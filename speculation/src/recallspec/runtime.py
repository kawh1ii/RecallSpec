"""Audited synchronous vLLM 0.32.0 worker hooks (single GPU, text only)."""
import dataclasses
import json
import os
from pathlib import Path
import time

from recallspec.core import Config, RetrievalIndex


def _trace(event):
    directory = os.environ.get("RECALLSPEC_TRACE")
    if directory:
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)
        with (path / f"worker-{os.getpid()}.jsonl").open("a") as f:
            f.write(json.dumps(event, separators=(",", ":")) + "\n")


def _index(runner):
    if not hasattr(runner, "_recallspec_index"):
        cfg = json.loads(os.environ.get("RECALLSPEC_CONFIG", "{}"))
        if "key_lengths" in cfg:
            cfg["key_lengths"] = tuple(cfg["key_lengths"])
        cfg["gate"] = os.environ.get("RECALLSPEC_MODE") == "gated"
        runner._recallspec_index = RetrievalIndex(Config(**cfg))
        _trace({"event": "init", "config": dataclasses.asdict(runner._recallspec_index.config)})
    return runner._recallspec_index


def before_update(runner, scheduler_output):
    index = getattr(runner, "_recallspec_index", None)
    if index is not None:
        for req_id in scheduler_output.finished_req_ids:
            index.finish(req_id)
    _trace({"event": "schedule", "requests": dict(scheduler_output.num_scheduled_tokens),
            "drafts": {rid: len(v) for rid, v in
                       scheduler_output.scheduled_spec_decode_tokens.items()},
            "finished": list(scheduler_output.finished_req_ids),
            "live_cursors": len(index.cursors) if index is not None else 0,
            "pending": len(index.pending) if index is not None else 0,
            "keys": len(index.entries) if index is not None else 0})


def propose(runner, scheduler_output, sampled, k, slot_mappings):
    start = time.perf_counter_ns()
    original_start = start
    drafts = runner.drafter.propose(k, sampled, runner.input_batch.num_tokens_no_spec,
                                  runner.input_batch.token_ids_cpu,
                                  slot_mappings=slot_mappings)
    native_ns = time.perf_counter_ns() - original_start
    mode = os.environ.get("RECALLSPEC_MODE", "native")
    index = _index(runner) if mode in ("gated", "ungated") else None
    if index is not None:
        if runner.use_async_scheduling or runner.parallel_config.tensor_parallel_size != 1:
            raise RuntimeError("RecallSpec supports synchronous single-GPU execution only")
        index.tick()
    events = []
    # Query the previous-step index for the whole batch before publishing any
    # current-step tokens. Batch ordering cannot manufacture same-step hits.
    to_commit = []
    for i, request_id in enumerate(runner.input_batch.req_ids):
        scheduled = scheduler_output.scheduled_spec_decode_tokens.get(request_id, [])
        verified = None
        if index is not None:
            verified = index.feedback(request_id, scheduled, sampled[i])
        if scheduled and sampled[i]:
            accepted = len(sampled[i]) - 1
            if not 0 <= accepted <= len(scheduled):
                raise RuntimeError("unsupported verifier output")
            events.append({"request_id": request_id, "scheduled": len(scheduled),
                           "accepted": accepted,
                           "source": "shared" if verified is not None else "native"})
        if index is None or not sampled[i]:
            continue
        request = runner.requests[request_id]
        if request.lora_request or request.mm_features or request.prompt_embeds is not None:
            raise RuntimeError("RecallSpec index is restricted to text without adapters")
        length = int(runner.input_batch.num_tokens_no_spec[i])
        tokens = runner.input_batch.token_ids_cpu[i, :length]
        if index.config.shared_first or not drafts[i]:
            cap = min(k, runner.max_model_len - length)
            shared = index.lookup(request_id, tokens, cap)
            if shared:
                drafts[i] = shared
        to_commit.append((request_id, tokens, request.num_prompt_tokens))
    for request_id, tokens, prompt_length in to_commit:
        index.commit(request_id, tokens, prompt_length)
    _trace({"event": "propose", "feedback": events,
            "native_ns": native_ns, "total_ns": time.perf_counter_ns() - start,
            "stats": dict(index.stats) if index is not None else {},
            "keys": len(index.entries) if index is not None else 0,
            "live_cursors": len(index.cursors) if index is not None else 0,
            "pending": len(index.pending) if index is not None else 0})
    return drafts
