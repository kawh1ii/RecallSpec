"""Reproducible offline vLLM speculative-decoding comparison."""

import argparse
import json
import os
from pathlib import Path
import statistics
import time

from vllm import LLM, SamplingParams


ADAPTIVE_STATS = {"proposed": 0, "accepted": 0, "steps": 0,
                  "caps": {"2": 0, "4": 0, "8": 0}}
DEBUG_STATS = {"update_calls": 0, "updated_drafts": 0,
               "scheduled_drafts": 0, "steps": 0}


def install_debug_metrics() -> None:
    from vllm.v1.core.sched.scheduler import Scheduler

    original_update = Scheduler.update_draft_token_ids
    original_schedule = Scheduler.schedule

    def update(self, drafts):
        DEBUG_STATS["update_calls"] += 1
        DEBUG_STATS["updated_drafts"] += sum(map(len, drafts.draft_token_ids))
        return original_update(self, drafts)

    def schedule(self):
        output = original_schedule(self)
        DEBUG_STATS["steps"] += 1
        DEBUG_STATS["scheduled_drafts"] += sum(
            map(len, output.scheduled_spec_decode_tokens.values()))
        return output

    Scheduler.update_draft_token_ids = update
    Scheduler.schedule = schedule


def install_adaptive_policy() -> None:
    """Cap each request's draft length using recent verified acceptance."""
    from vllm.v1.spec_decode.ngram_proposer import NgramProposer

    original = NgramProposer.propose

    def adaptive_propose(self, sampled_token_ids, req_ids,
                         num_tokens_no_spec, token_ids_cpu,
                         spec_decode_unsupported_reqs):
        if not hasattr(self, "_adaptive_history"):
            self._adaptive_history = {}
        history = self._adaptive_history
        active = set(req_ids)
        for old_id in list(history):
            if old_id not in active:
                del history[old_id]

        for req_id, sampled in zip(req_ids, sampled_token_ids):
            previous = history.get(req_id)
            if previous is None or not previous["draft_len"]:
                continue
            accepted = min(max(len(sampled) - 1, 0), previous["draft_len"])
            ratio = accepted / previous["draft_len"]
            previous["ema"] = 0.65 * previous["ema"] + 0.35 * ratio
            previous["observations"] += 1
            ADAPTIVE_STATS["accepted"] += accepted

        drafts = original(self, sampled_token_ids, req_ids,
                          num_tokens_no_spec, token_ids_cpu,
                          spec_decode_unsupported_reqs)
        for req_id, draft in zip(req_ids, drafts):
            if not draft:
                continue
            item = history.setdefault(req_id, {"ema": 0.5,
                                               "observations": 0,
                                               "draft_len": 0})
            if item["observations"] < 2:
                cap = 4
            elif item["ema"] >= 0.7:
                cap = 8
            elif item["ema"] >= 0.35:
                cap = 4
            else:
                cap = 2
            cap = min(cap, len(draft))
            del draft[cap:]
            item["draft_len"] = len(draft)
            ADAPTIVE_STATS["proposed"] += len(draft)
            ADAPTIVE_STATS["steps"] += 1
            ADAPTIVE_STATS["caps"][str(cap)] = (
                ADAPTIVE_STATS["caps"].get(str(cap), 0) + 1)
        return drafts

    NgramProposer.propose = adaptive_propose


def prompts(workload: str, batch: int, variant: int = 0) -> list[str]:
    if workload == "copy":
        examples = []
        for i in range(batch):
            tag = chr(ord("A") + i)
            line = f"{tag} record: orange | status: ready | unit: 17 | checksum: 3491"
            body = "\n".join([line] * 30)
            examples.append(
                "Continue this exact repeated log for 30 more lines. "
                "Output only log lines.\n" + body + "\n" + f"{tag} record: orange | status:"
            )
        return examples
    if workload == "incremental":
        examples = []
        for i in range(batch):
            tag = chr(ord("A") + i)
            lines = [f"{tag} item {j:03d}: value={j * 7 + i}; status=ready"
                     for j in range(40)]
            examples.append(
                "Continue this log in exactly the same format for 30 more "
                "lines. Output only the continued log.\n" +
                "\n".join(lines) + "\n" + f"{tag} item 040:"
            )
        return examples
    if workload == "shared_tail":
        return [
            f"Request identifier: {10000 + variant * batch + i}. "
            "The identifier is unrelated to the answer. "
            "Output the integers 1 through 100 in increasing order, "
            "separated by a comma and one space. No introduction and "
            "no explanation. Begin immediately."
            for i in range(batch)
        ]
    if workload == "unique_general":
        topics = [
            "Explain MVCC using a bank transfer example.",
            "Describe how packet loss affects congestion control.",
            "Compare row and column storage for analytic queries.",
            "Explain the purpose of a write-ahead log in a database.",
            "Describe the tradeoffs of synchronous replication.",
            "Explain how a Bloom filter can reduce disk reads.",
            "Compare checkpointing strategies for data pipelines.",
            "Describe how deadlocks can form among three processes.",
            "Explain how consistent hashing reduces remapping.",
            "Compare eager and lazy memory allocation on a GPU.",
            "Describe a way to measure p99 latency accurately.",
            "Explain when an LRU cache can perform poorly.",
        ]
        return [
            f"{topics[(variant * batch + i) % len(topics)]} "
            f"Use the distinct case identifier {20000 + variant * batch + i} "
            "in your explanation."
            for i in range(batch)
        ]
    topics = [
        "Explain how a database index changes query latency for different selectivity levels.",
        "Compare optimistic and pessimistic concurrency control with an example.",
        "Describe the tradeoffs between tensor and pipeline parallelism in LLM training.",
        "Explain why a cache can increase tail latency under some workloads.",
        "How does backpressure affect a streaming data pipeline?",
        "Describe a way to test whether a distributed lock implementation is correct.",
        "Explain the difference between throughput and latency in online inference.",
        "What happens when a GPU kernel uses more registers than the available budget?",
    ]
    return [topics[i % len(topics)] for i in range(batch)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("base", "static4", "static8", "adaptive8", "shared8"), required=True)
    parser.add_argument("--workload", choices=("copy", "incremental", "general", "shared_tail", "unique_general"), required=True)
    parser.add_argument("--batch", type=int, default=1)
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument("--model", required=True,
                        help="Local path or Hugging Face model ID")
    parser.add_argument("--prefix-cache", action="store_true")
    args = parser.parse_args()

    spec = None
    if args.mode != "base":
        spec = {
            "method": "ngram",
            "num_speculative_tokens": 4 if args.mode == "static4" else 8,
            "prompt_lookup_min": 2,
            "prompt_lookup_max": 5,
        }
    if args.mode == "adaptive8" and os.environ.get("SPEC_ADAPTIVE") != "1":
        install_adaptive_policy()
    if os.environ.get("SPEC_DEBUG") == "1":
        install_debug_metrics()

    llm = LLM(
        model=args.model,
        dtype="bfloat16",
        max_model_len=2048,
        gpu_memory_utilization=0.75,
        max_num_seqs=max(8, args.batch),
        enable_prefix_caching=args.prefix_cache,
        speculative_config=spec,
    )
    sampling = SamplingParams(temperature=0, max_tokens=128,
                              min_tokens=128, ignore_eos=True)
    timings = []
    ttft_samples = []
    tpot_samples = []
    token_ids = None
    round_token_ids = []
    for run in range(args.rounds + 1):
        inputs = prompts(args.workload, args.batch,
                         variant=run if args.workload in ("shared_tail", "unique_general") else 0)
        start = time.perf_counter()
        outputs = llm.generate(inputs, sampling, use_tqdm=False)
        elapsed = time.perf_counter() - start
        ids = [item.outputs[0].token_ids for item in outputs]
        if run > 0:
            timings.append(elapsed)
            token_ids = ids
            round_token_ids.append(ids)
            for item in outputs:
                metrics = getattr(item, "metrics", None)
                first = getattr(metrics, "first_token_time", None)
                arrival = getattr(metrics, "arrival_time", None)
                finished = getattr(metrics, "finished_time", None)
                if first is not None and arrival is not None:
                    ttft_samples.append(first - arrival)
                if first is not None and finished is not None:
                    tpot_samples.append((finished - first) / 127)
        print("ROUND", run, elapsed, flush=True)
    result = {
        "mode": args.mode, "workload": args.workload, "batch": args.batch,
        "prefix_cache": args.prefix_cache,
        "model": args.model, "output_tokens": args.batch * 128,
        "elapsed_seconds": timings,
        "median_seconds": statistics.median(timings),
        "output_tokens_per_second": args.batch * 128 / statistics.median(timings),
        "ttft_seconds": ttft_samples,
        "tpot_seconds": tpot_samples,
        "token_ids": token_ids,
        "round_token_ids": round_token_ids,
        "adaptive_stats": ADAPTIVE_STATS if args.mode == "adaptive8" else None,
        "debug_stats": DEBUG_STATS if os.environ.get("SPEC_DEBUG") == "1" else None,
    }
    print("SUMMARY", json.dumps({k: v for k, v in result.items()
                                 if k not in ("token_ids", "round_token_ids")}), flush=True)
    suffix = "_apc" if args.prefix_cache else ""
    result_path = (f"spec_{Path(args.model).name}_{args.mode}_"
                   f"{args.workload}_b{args.batch}{suffix}.json")
    with open(result_path, "w") as f:
        json.dump(result, f, indent=2)


if __name__ == "__main__":
    main()
