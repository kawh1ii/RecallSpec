"""Measure how many real vLLM n-gram rows can be skipped on controlled inputs."""
import argparse
from importlib.util import module_from_spec, spec_from_file_location
import hashlib
from importlib.metadata import version
import inspect
import json
import platform
import os
from pathlib import Path
import statistics
from time import perf_counter_ns
from types import SimpleNamespace as NS

import numpy as np
from vllm.v1.spec_decode.ngram_proposer import NgramProposer
from recallspec.core import Config, RetrievalIndex


def load(name, path):
    spec = spec_from_file_location(name, path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Counted:
    def __init__(self, drafter):
        self.drafter = drafter
        self.calls = 0
        self.rows = 0
        self.native_ns = 0

    def propose(self, k, sampled, *args, **kwargs):
        self.calls += 1
        self.rows += sum(bool(x) for x in sampled)
        t0 = perf_counter_ns()
        result = self.drafter.propose(k, sampled, *args, **kwargs)
        self.native_ns += perf_counter_ns() - t0
        return result


def fixture(rows, hits, native):
    b, length = rows.shape
    ids = [f"r{i}" for i in range(b)]
    index = RetrievalIndex(Config())
    for i in range(hits):
        row = rows[i, -12:].tolist()
        index.commit(f"source{i}", row + [100 + i] * 8, 12)
    return NS(
        drafter=Counted(native), input_batch=NS(req_ids=ids, num_tokens_no_spec=np.full(b, length, np.int32),
                                                token_ids_cpu=rows),
        requests={rid: NS(lora_request=None, mm_features=[], prompt_embeds=None,
                          num_prompt_tokens=length - 32) for rid in ids},
        max_model_len=4096, parallel_config=NS(tensor_parallel_size=1),
        use_async_scheduling=False, _recallspec_index=index,
    )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("original", type=Path)
    p.add_argument("candidate", type=Path)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--seed", type=int, default=231)
    a = p.parse_args()
    if a.output.exists():
        raise FileExistsError(a.output)
    os.environ["RECALLSPEC_MODE"] = "gated"
    modules = (load("original", a.original), load("candidate", a.candidate))
    config = NS(speculative_config=NS(prompt_lookup_min=2, prompt_lookup_max=5, num_speculative_tokens=8),
                model_config=NS(max_model_len=4096), scheduler_config=NS(max_num_seqs=8),
                parallel_config=NS(tensor_parallel_size=1))
    native = NgramProposer(config)
    scheduler = NS(scheduled_spec_decode_tokens={})
    rng = np.random.default_rng(a.seed)
    groups = []
    for batch in (1, 8):
        for length in (128, 1024):
            for hits in sorted({0, batch // 2, batch}):
                stats = [[], []]
                for i in range(68):
                    # Earlier copy of the tail gives native lookup real work
                    # and a valid alternative continuation on uncovered rows.
                    rows = rng.integers(200, 28000, (batch, length), dtype=np.int32)
                    rows[:, :5] = rows[:, -5:]
                    sampled = [[int(row[-1])] for row in rows]
                    outputs, states = [None, None], [None, None]
                    order = (0, 1) if i % 2 == 0 else (1, 0)
                    for j in order:
                        runner = fixture(rows, hits, native)
                        t0 = perf_counter_ns()
                        outputs[j] = modules[j].propose(runner, scheduler, sampled, 8, None)
                        elapsed = perf_counter_ns() - t0
                        states[j] = vars(runner._recallspec_index)
                        if runner.drafter.rows != (batch if j == 0 else batch - hits):
                            raise AssertionError("Unexpected fallback mask")
                        if i >= 4:
                            stats[j].append({"ns": elapsed, "calls": runner.drafter.calls,
                                             "rows": runner.drafter.rows, "native_ns": runner.drafter.native_ns})
                    if outputs[0] != outputs[1] or states[0] != states[1]:
                        raise AssertionError((batch, length, hits, i))
                groups.append({"batch": batch, "context_tokens": length, "shared_hits": hits,
                               "original_median_us": statistics.median(x["ns"] for x in stats[0]) / 1000,
                               "candidate_median_us": statistics.median(x["ns"] for x in stats[1]) / 1000,
                               "original": stats[0], "candidate": stats[1], "exact_cases": 68})
                print("PASS", batch, length, hits, flush=True)
    source = Path(inspect.getfile(NgramProposer))
    meta = {
        "seed": a.seed, "groups": groups, "vllm": version("vllm"),
        "numba": version("numba"), "python": platform.python_version(),
        "original_sha256": hashlib.sha256(a.original.read_bytes()).hexdigest(),
        "candidate_sha256": hashlib.sha256(a.candidate.read_bytes()).hexdigest(),
        "native_source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    }
    a.output.write_text(json.dumps(meta, indent=2) + "\n")


if __name__ == "__main__":
    main()
