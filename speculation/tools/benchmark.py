"""Offline paired workloads. Every output ID and cold/warm phase is retained."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import random
import statistics
import time


TOPICS = [
    "Explain MVCC using a bank transfer example.",
    "Describe packet loss and congestion control.",
    "Compare row and column storage for analytic queries.",
    "Explain write-ahead logging with an example.",
    "Describe the tradeoffs of synchronous replication.",
    "Explain how a Bloom filter reduces disk reads.",
    "Compare checkpointing strategies for data pipelines.",
    "Explain deadlocks among three processes.",
    "Explain consistent hashing and remapping.",
    "Compare eager and lazy GPU memory allocation.",
    "Describe a way to measure p99 latency accurately.",
    "Explain when an LRU cache performs poorly.",
]


def prompts(kind, batch, variant, seed):
    rng = random.Random(seed * 1000 + variant)
    if kind == "repeat":
        return [f"Request identifier {seed}-{variant}-{i}. Ignore this identifier. "
                "Output integers 1 through 100 in increasing order separated by a comma "
                "and one space. No introduction or explanation. Begin immediately."
                for i in range(batch)]
    if kind == "conflict":
        # Repeated ending and opening answer tokens; continuation depends on
        # earlier instruction. A shared suffix is not evidence of same answer.
        return [f"Task {seed}-{variant}-{i}: Output the multiples of "
                f"{rng.choice([3, 7, 11, 13, 17, 19])} below 500. "
                "Start with the exact text 'Result: ' and then the numbers. "
                "Separate numbers with a comma and one space. No explanation. Begin now."
                for i in range(batch)]
    return [f"Case {seed}-{variant}-{i}: {TOPICS[(variant * batch + i) % len(TOPICS)]} "
            "Give a concrete example and explain the tradeoff."
            for i in range(batch)]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True)
    p.add_argument("--mode", choices=["base", "native", "ungated", "gated"], required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--seed", type=int, default=71)
    p.add_argument("--rounds", type=int, default=4)
    p.add_argument("--batches", default="1,8")
    p.add_argument("--kinds", default="repeat,general,conflict")
    p.add_argument("--tokens", type=int, default=128)
    p.add_argument("--trace")
    p.add_argument("--eager", action="store_true")
    p.add_argument("--batch-invariant", action="store_true")
    p.add_argument("--prefix-cache", action="store_true")
    p.add_argument("--runner", choices=["v1", "v2"], default="v1")
    p.add_argument("--config")
    a = p.parse_args()
    output = Path(a.output)
    if output.exists():
        raise FileExistsError(output)
    os.environ["RECALLSPEC_MODE"] = a.mode
    # 0.32 defaults may select a different runner that bypasses the audited
    # integration point. Fix the SAME supported runner for every control.
    if a.runner == "v2" and (a.mode in ("gated", "ungated") or a.trace):
        raise ValueError("v2 is a native-only external control, without RecallSpec traces")
    os.environ["VLLM_USE_V2_MODEL_RUNNER"] = "0" if a.runner == "v1" else "1"
    if a.config:
        os.environ["RECALLSPEC_CONFIG"] = Path(a.config).read_text()
    if a.trace:
        os.environ["RECALLSPEC_TRACE"] = str(Path(a.trace).resolve())
    if a.batch_invariant:
        os.environ["VLLM_BATCH_INVARIANT"] = "1"
    from vllm import LLM, SamplingParams
    import torch
    import vllm
    root = Path(__file__).resolve().parents[1]
    package = Path(vllm.__file__).parent
    files = {str(f.relative_to(root)): hashlib.sha256(f.read_bytes()).hexdigest()
             for f in sorted((root / "src").rglob("*.py")) if not f.name.startswith("._")}
    for f in ("v1/worker/gpu_model_runner.py", "v1/spec_decode/ngram_proposer.py",
              "v1/core/sched/scheduler.py"):
        files["vllm/" + f] = hashlib.sha256((package / f).read_bytes()).hexdigest()
    result = {"args": vars(a), "utc": datetime.now(timezone.utc).isoformat(),
              "environment": {"vllm": vllm.__version__, "torch": torch.__version__,
                              "python": platform.python_version(),
                              "gpu": torch.cuda.get_device_name(0)},
              "source_hashes": files, "model_runner": "GPUModelRunner" + a.runner.upper(),
              "records": []}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2))
    spec = None if a.mode == "base" else {
        "method": "ngram", "num_speculative_tokens": 8,
        "prompt_lookup_min": 2, "prompt_lookup_max": 5}
    llm = LLM(model=a.model, dtype="bfloat16", max_model_len=4096,
              attention_backend="FLASH_ATTN",
              gpu_memory_utilization=0.75, max_num_seqs=8,
              enable_prefix_caching=a.prefix_cache, speculative_config=spec,
              async_scheduling=False, enforce_eager=a.eager, seed=0)
    sampling = SamplingParams(temperature=0, seed=0, max_tokens=a.tokens,
                              min_tokens=a.tokens, ignore_eos=True)
    # Compile and initialize with unrelated prompts. No repeat-task cache seed.
    llm.generate(["Explain memory alignment."] * 8, sampling, use_tqdm=False)
    tokenizer = llm.get_tokenizer()
    variants = [(kind, batch, round_) for kind in a.kinds.split(",")
                for batch in map(int, a.batches.split(","))
                for round_ in range(a.rounds)]
    for kind, batch, round_ in variants:
        raw_texts = prompts(kind, batch, round_, a.seed)
        texts = [tokenizer.apply_chat_template(
                    [{"role": "user", "content": t}], tokenize=False,
                    add_generation_prompt=True) for t in raw_texts]
        torch.cuda.synchronize()
        start = time.perf_counter()
        outputs = llm.generate(texts, sampling, use_tqdm=False)
        torch.cuda.synchronize()
        duration = time.perf_counter() - start
        record = {"kind": kind, "batch": batch, "round": round_,
                  "phase": "first" if round_ == 0 else "subsequent",
                  "duration_s": duration, "outputs": []}
        for raw_prompt, prompt, item in zip(raw_texts, texts, outputs):
            record["outputs"].append({"request_id": item.request_id, "prompt": prompt,
                    "raw_prompt": raw_prompt,
                    "prompt_token_ids": tokenizer.encode(prompt),
                    "token_ids": list(item.outputs[0].token_ids),
                    "finish_reason": item.outputs[0].finish_reason})
        result["records"].append(record)
        output.write_text(json.dumps(result, indent=2))
        print(json.dumps({"kind": kind, "batch": batch, "round": round_,
                          "duration_s": duration}), flush=True)
    result["completed"] = True
    if a.trace:
        traces = list(Path(a.trace).glob("*.jsonl"))
        if not traces:
            raise RuntimeError("No worker trace: audited integration did not execute")
        if a.mode in ("gated", "ungated") and not any(
                '"event":"init"' in t.read_text() for t in traces):
            raise RuntimeError("Retrieval index never initialized")
    result["packages"] = {d.metadata["Name"]: d.version for d in importlib.metadata.distributions()}
    output.write_text(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
