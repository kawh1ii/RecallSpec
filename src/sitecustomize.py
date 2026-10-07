"""Opt-in cross-request N-gram proposer for vLLM 0.11.0 experiments.

The index is bounded to 50,000 keys and scoped to one isolated engine.
It stores token continuations from other requests and lets vLLM's target
model verify every proposed token. This prototype has no tenant isolation;
do not enable it on a shared service.
"""

import atexit
from collections import OrderedDict
import json
import os


if os.environ.get("SPEC_SHARED") == "1":
    from vllm.v1.spec_decode.ngram_proposer import NgramProposer

    original_propose = NgramProposer.propose
    stats = {"shared_proposals": 0, "shared_tokens": 0,
             "shared_accepted": 0, "indexed_keys": 0}

    def propose_shared(self, sampled_token_ids, req_ids,
                       num_tokens_no_spec, token_ids_cpu,
                       spec_decode_unsupported_reqs):
        if not hasattr(self, "_shared_index"):
            self._shared_index = OrderedDict()
            self._shared_end = {}
            self._shared_previous = {}
        index = self._shared_index
        active = set(req_ids)
        for req_id in list(self._shared_end):
            if req_id not in active:
                del self._shared_end[req_id]
                self._shared_previous.pop(req_id, None)

        for req_id, sampled in zip(req_ids, sampled_token_ids):
            prior = self._shared_previous.pop(req_id, 0)
            if prior:
                stats["shared_accepted"] += min(max(len(sampled) - 1, 0), prior)

        drafts = original_propose(self, sampled_token_ids, req_ids,
                                  num_tokens_no_spec, token_ids_cpu,
                                  spec_decode_unsupported_reqs)

        # Query before updating the index so a request cannot propose from
        # tokens it just contributed itself.
        for i, req_id in enumerate(req_ids):
            if drafts[i] or req_id in spec_decode_unsupported_reqs:
                continue
            length = int(num_tokens_no_spec[i])
            for n in (12, 8):
                if length < n:
                    continue
                key = tuple(int(v) for v in token_ids_cpu[i, length-n:length])
                entries = index.get(key)
                if entries is None:
                    continue
                candidate = next((tokens for source, tokens in reversed(entries)
                                  if source != req_id), None)
                if candidate:
                    drafts[i] = candidate.copy()
                    self._shared_previous[req_id] = len(candidate)
                    stats["shared_proposals"] += 1
                    stats["shared_tokens"] += len(candidate)
                    index.move_to_end(key)
                    break

        k = self.k
        for i, req_id in enumerate(req_ids):
            length = int(num_tokens_no_spec[i])
            if req_id not in self._shared_end:
                if not sampled_token_ids[i]:
                    continue
                # The first proposal follows the first sampled token. The
                # boundary just before it is the end of the prompt, so the
                # index contains only prompt-tail -> generated continuation
                # and subsequent generated-token continuations.
                self._shared_end[req_id] = max(12, length - 1)
            start = self._shared_end[req_id]
            stop = length - k + 1
            for end in range(start, stop):
                continuation = [int(v) for v in token_ids_cpu[i, end:end+k]]
                for n in (8, 12):
                    if end < n:
                        continue
                    key = tuple(int(v) for v in token_ids_cpu[i, end-n:end])
                    entries = index.get(key)
                    if entries is None:
                        entries = []
                        index[key] = entries
                    entries[:] = [(source, tokens) for source, tokens in entries
                                  if source != req_id]
                    entries.append((req_id, continuation))
                    if len(entries) > 2:
                        del entries[0]
                    index.move_to_end(key)
            self._shared_end[req_id] = max(start, stop)
        while len(index) > 50000:
            index.popitem(last=False)
        stats["indexed_keys"] = len(index)

        stats_file = os.environ.get("SPEC_STATS_FILE")
        if stats_file and stats["shared_proposals"] and \
                stats["shared_proposals"] % 16 == 0:
            with open(stats_file, "w") as stream:
                json.dump(stats, stream)
        return drafts

    NgramProposer.propose = propose_shared

    def emit_stats():
        if stats["indexed_keys"]:
            print("SPEC_SHARED_STATS", json.dumps(stats), flush=True)

    atexit.register(emit_stats)
