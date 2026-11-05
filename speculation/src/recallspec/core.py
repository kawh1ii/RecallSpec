"""Engine-local, bounded index of committed generated continuations.

This module has no GPU dependency. All boundaries are half-open token offsets.
Only actual scheduled drafts can update acceptance feedback. A retrieved draft
never becomes committed data until the caller supplies verified output tokens.
"""
from collections import Counter, OrderedDict
from dataclasses import dataclass, field
from typing import Sequence


@dataclass(frozen=True)
class Config:
    key_lengths: tuple[int, ...] = (12, 8)
    draft_tokens: int = 8
    max_keys: int = 50000
    sources_per_key: int = 2
    ttl_steps: int = 4096
    gate: bool = True
    shared_first: bool = True
    min_observations: int = 2
    min_accepted: float = 2.0
    cooldown_steps: int = 32
    max_updates_per_request: int = 32

    def __post_init__(self):
        if not self.key_lengths or any(n <= 0 for n in self.key_lengths):
            raise ValueError("key lengths must be positive")
        if len(set(self.key_lengths)) != len(self.key_lengths):
            raise ValueError("duplicate key lengths")
        for name in ("draft_tokens", "max_keys", "sources_per_key", "ttl_steps",
                     "min_observations", "cooldown_steps", "max_updates_per_request"):
            if getattr(self, name) <= 0:
                raise ValueError(name + " must be positive")
        if not 0 <= self.min_accepted <= self.draft_tokens:
            raise ValueError("min_accepted out of range")


@dataclass
class Entry:
    source: str
    tokens: tuple[int, ...]
    written: int
    observations: int = 0
    mean_accepted: float = 0.0
    blocked_until: int = 0


@dataclass(frozen=True)
class Proposal:
    key: tuple[int, ...]
    source: str
    tokens: tuple[int, ...]
    entry: Entry = field(compare=False, repr=False)


@dataclass
class Cursor:
    prompt_length: int
    next_end: int
    committed_length: int


class RetrievalIndex:
    def __init__(self, config: Config = Config()):
        self.config = config
        self.entries: OrderedDict[tuple[int, ...], list[Entry]] = OrderedDict()
        self.cursors: dict[str, Cursor] = {}
        self.pending: dict[str, Proposal] = {}
        self.step = 0
        self.stats = Counter()

    def tick(self):
        self.step += 1

    def finish(self, request_id: str):
        """Drop live state; committed cache entries survive until TTL/LRU."""
        self.cursors.pop(request_id, None)
        self.pending.pop(request_id, None)

    def clear(self):
        self.entries.clear()
        self.cursors.clear()
        self.pending.clear()
        self.stats.clear()
        self.step = 0

    def commit(self, request_id: str, tokens: Sequence[int], prompt_length: int):
        """Index only continuations entirely after the actual prompt boundary.

        Cursor tracks committed tokens, never speculative slots. Work is capped
        per request per invocation; if catching up would exceed that cap, skip
        old windows and retain the newest windows. This is intentional sampling.
        """
        length = len(tokens)
        if not 0 <= prompt_length <= length:
            raise ValueError("invalid prompt boundary")
        cursor = self.cursors.get(request_id)
        if cursor is None:
            cursor = Cursor(prompt_length, prompt_length, length)
            self.cursors[request_id] = cursor
        elif cursor.prompt_length != prompt_length or length < cursor.committed_length:
            # A preempted request must supply its retained committed history.
            # Refuse silent cursor rollback or ID reuse without finish().
            raise ValueError("committed history rolled back or request ID reused")
        cursor.committed_length = length
        stop = length - self.config.draft_tokens + 1
        start = max(cursor.next_end, prompt_length)
        if stop - start > self.config.max_updates_per_request:
            self.stats["skipped_windows"] += stop - start - self.config.max_updates_per_request
            start = stop - self.config.max_updates_per_request
        for end in range(start, stop):
            continuation = tuple(int(t) for t in tokens[end:end + self.config.draft_tokens])
            for n in self.config.key_lengths:
                if end < n:
                    continue
                key = tuple(int(t) for t in tokens[end-n:end])
                entries = self.entries.setdefault(key, [])
                old = next((e for e in entries if e.source == request_id), None)
                if old is not None:
                    # Preserve feedback for the same continuation; changed
                    # continuations are new candidates and must be re-probed.
                    entries.remove(old)
                entry = old if old is not None and old.tokens == continuation else Entry(
                    request_id, continuation, self.step)
                entry.written = self.step
                entries.append(entry)
                del entries[:-self.config.sources_per_key]
                self.entries.move_to_end(key)
                self.stats["insertions"] += 1
                # Enforce capacity at each insertion, not only after a batch.
                if len(self.entries) > self.config.max_keys:
                    self.entries.popitem(last=False)
                    self.stats["evictions"] += 1
        cursor.next_end = max(cursor.next_end, stop)

    def lookup(self, request_id: str, tokens: Sequence[int], cap: int) -> list[int]:
        self.stats["lookups"] += 1
        self.pending.pop(request_id, None)
        cap = min(cap, self.config.draft_tokens)
        if cap <= 0:
            return []
        for n in self.config.key_lengths:
            if len(tokens) < n:
                continue
            key = tuple(int(t) for t in tokens[-n:])
            entries = self.entries.get(key)
            if not entries:
                continue
            live = [e for e in entries if self.step - e.written < self.config.ttl_steps]
            self.stats["expired_entries"] += len(entries) - len(live)
            if not live:
                del self.entries[key]
                continue
            self.entries[key] = live
            for entry in reversed(live):
                if entry.source == request_id:
                    self.stats["self_excluded"] += 1
                    continue
                if self.config.gate and self.step < entry.blocked_until:
                    self.stats["gate_skips"] += 1
                    continue
                draft = entry.tokens[:cap]
                self.pending[request_id] = Proposal(key, entry.source, draft, entry)
                self.entries.move_to_end(key)
                self.stats["retrieved_proposals"] += 1
                self.stats["retrieved_tokens"] += len(draft)
                return list(draft)
        self.stats["misses"] += 1
        return []

    def feedback(self, request_id: str, scheduled: Sequence[int], sampled: Sequence[int]):
        """Reconcile *scheduled* prefix and count target-accepted draft tokens.

        Standard synchronous ngram verifier returns accepted prefix + one
        target/bonus token. Empty output is not an observed rejection. Truncated
        scheduling is counted against the truncated length, never proposal len.
        """
        proposal = self.pending.pop(request_id, None)
        if proposal is None:
            return None
        scheduled = tuple(int(t) for t in scheduled)
        if not scheduled or not sampled:
            self.stats["unobserved_proposals"] += 1
            return None
        if len(scheduled) > len(proposal.tokens) or scheduled != proposal.tokens[:len(scheduled)]:
            self.stats["unmatched_feedback"] += 1
            raise ValueError("scheduled draft does not match pending retrieval")
        accepted = len(sampled) - 1
        if not 0 <= accepted <= len(scheduled):
            raise ValueError("invalid target acceptance count")
        if tuple(sampled[:accepted]) != scheduled[:accepted]:
            raise ValueError("accepted tokens differ from scheduled prefix")
        self.stats["verified_proposals"] += 1
        self.stats["verified_tokens"] += len(scheduled)
        self.stats["accepted_tokens"] += accepted
        entry = proposal.entry
        entry.observations += 1
        entry.mean_accepted += (accepted - entry.mean_accepted) / entry.observations
        # Freeze calibration until cooldown expires, then allow a fresh probe.
        if self.config.gate and entry.observations >= self.config.min_observations:
            if entry.mean_accepted < self.config.min_accepted:
                entry.blocked_until = self.step + self.config.cooldown_steps
                self.stats["gate_blocks"] += 1
            entry.observations = 0
            entry.mean_accepted = 0.0
        return {"source": "shared", "scheduled": len(scheduled), "accepted": accepted}
