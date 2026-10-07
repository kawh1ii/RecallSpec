"""Diagnostic-only trace for vLLM 0.11 n-gram speculative decoding.

Run in a fresh process with SPEC_DIAG_DIR set. Optionally set SPEC_SHARED=1
to load the unmodified RecallSpec sitecustomize before instrumentation.
This logs every draft and every scheduled verification to JSONL; it adds I/O
and must not be used for performance timing.
"""

import importlib.util
import json
import os
from pathlib import Path
import time


trace_dir = os.environ.get("SPEC_DIAG_DIR")
if trace_dir:
    if os.environ.get("SPEC_SHARED") == "1":
        shared_path = Path(__file__).resolve().parents[1] / "src" / "sitecustomize.py"
        spec = importlib.util.spec_from_file_location("spec_shared_patch", shared_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        native_propose = module.original_propose

        def timed_native(self, *args, **kwargs):
            started = time.perf_counter_ns()
            result = native_propose(self, *args, **kwargs)
            self._diag_native_ns = time.perf_counter_ns() - started
            return result

        # The shared patch resolves this module global on each invocation.
        # Time the original proposer without changing its returned draft.
        module.original_propose = timed_native

    from vllm.v1.spec_decode.ngram_proposer import NgramProposer
    from vllm.v1.core.sched.scheduler import Scheduler

    Path(trace_dir).mkdir(parents=True, exist_ok=True)
    draft_file = Path(trace_dir) / f"drafts-{os.getpid()}.jsonl"
    verify_file = Path(trace_dir) / f"verify-{os.getpid()}.jsonl"
    original_propose = NgramProposer.propose
    original_update = Scheduler.update_from_output

    def trace_propose(self, sampled_token_ids, req_ids, num_tokens_no_spec,
                      token_ids_cpu, spec_decode_unsupported_reqs):
        start = time.perf_counter_ns()
        drafts = original_propose(self, sampled_token_ids, req_ids,
                                  num_tokens_no_spec, token_ids_cpu,
                                  spec_decode_unsupported_reqs)
        elapsed = time.perf_counter_ns() - start
        native_ns = getattr(self, "_diag_native_ns", None)
        rows = []
        for req_id, draft in zip(req_ids, drafts):
            source = ("shared" if draft and
                      req_id in getattr(self, "_shared_previous", {})
                      else "native" if draft else "none")
            rows.append({"req_id": req_id, "source": source,
                         "draft": list(map(int, draft))})
        with draft_file.open("a") as stream:
            stream.write(json.dumps({"type": "propose", "elapsed_ns": elapsed,
                                     "native_ns": native_ns,
                                     "shared_extra_ns": (elapsed - native_ns)
                                     if native_ns is not None else None,
                                     "rows": rows}) + "\n")
        return drafts

    def trace_update(self, scheduler_output, model_runner_output):
        scheduled = scheduler_output.scheduled_spec_decode_tokens
        samples = model_runner_output.sampled_token_ids
        rows = []
        for req_id, draft in scheduled.items():
            index = model_runner_output.req_id_to_index.get(req_id)
            if index is None:
                continue
            sampled = samples[index] if samples else []
            rows.append({"req_id": req_id, "draft": list(map(int, draft)),
                         "accepted": max(len(sampled) - 1, 0),
                         "sampled": list(map(int, sampled))})
        with verify_file.open("a") as stream:
            stream.write(json.dumps({"type": "step",
                                     "scheduled_req_ids": list(
                                         scheduler_output.num_scheduled_tokens),
                                     "rows": rows}) + "\n")
        return original_update(self, scheduler_output, model_runner_output)

    NgramProposer.propose = trace_propose
    Scheduler.update_from_output = trace_update
