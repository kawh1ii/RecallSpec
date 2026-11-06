"""Pair the two RecallSpec fallback implementations in one vLLM environment."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def fingerprint(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (root / "src").rglob("*.py")}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--baseline", type=Path, required=True)
    p.add_argument("--candidate", type=Path, required=True)
    p.add_argument("--model", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--seeds", type=int, nargs="+", default=[244, 245, 246])
    p.add_argument("--strict", action="store_true")
    args = p.parse_args()
    roots = {"original": args.baseline.resolve(), "lazy": args.candidate.resolve()}
    hashes = {k: fingerprint(v) for k, v in roots.items()}
    old, new = hashes.values()
    if {k for k in old.keys() | new.keys() if old.get(k) != new.get(k)} != {"src/recallspec/runtime.py"}:
        raise RuntimeError("Unexpected runtime source differences")
    sys.path.insert(0, str(roots["original"] / "tools"))
    from analyze import compare, trace_summary
    args.output.mkdir(parents=True, exist_ok=False)
    report = {"seeds": args.seeds, "strict": args.strict, "source_hashes": hashes, "pairs": []}
    for i, seed in enumerate(args.seeds):
        order = list(roots) if i % 2 == 0 else list(reversed(roots))
        raw, traces = {}, {}
        for variant in order:
            root = roots[variant]
            target = args.output / f"{variant}-s{seed}"
            command = [sys.executable, str(root / "tools/run_matrix.py"), "--model", str(args.model),
                       "--output", str(target), "--modes", "gated", "--seeds", str(seed),
                       "--rounds", "3", "--tokens", "128", "--batches", "1,8", "--runner", "v1"]
            if args.strict:
                command += ["--eager", "--batch-invariant", "--trace"]
            env = {k: v for k, v in os.environ.items()
                   if not k.startswith("RECALLSPEC_") and k != "VLLM_BATCH_INVARIANT"}
            env["PYTHONPATH"] = str(root / "src")
            with target.with_suffix(".log").open("w") as log:
                subprocess.run(command, env=env, check=True, stdout=log, stderr=subprocess.STDOUT)
            data = json.loads((target / f"gated-s{seed}.json").read_text())
            if not data["completed"]:
                raise RuntimeError(f"Incomplete run: {target}")
            if any(data["source_hashes"].get(k) != v for k, v in hashes[variant].items()):
                raise RuntimeError("Worker run did not fingerprint expected code")
            raw[variant] = data
            if args.strict:
                trace = target / f"gated-s{seed}-trace"
                traces[variant] = trace_summary(trace, data["records"])
                native_calls = 0
                for file in trace.glob("*.jsonl"):
                    events = [json.loads(line) for line in file.read_text().splitlines()]
                    schedule = [e for e in events if e["event"] == "schedule"]
                    if not schedule or schedule[-1]["live_cursors"] or schedule[-1]["pending"]:
                        raise RuntimeError("Recall state did not drain")
                    if any(e.get("keys", 0) > 50000 for e in events):
                        raise RuntimeError("Index exceeded key capacity")
                    if variant == "lazy":
                        native_calls += sum(e["native_calls"] for e in events if e["event"] == "propose")
                if variant == "lazy":
                    traces[variant]["native_calls"] = native_calls
        comparison = compare(raw["original"], raw["lazy"])
        if comparison["total"] != 81:
            raise RuntimeError("Incomplete paired comparison")
        report["pairs"].append({"seed": seed, "token_comparison": comparison, "traces": traces})
        (args.output / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
        print(seed, comparison["identical"], comparison["total"], flush=True)
        if args.strict and comparison["identical"] != 81:
            raise RuntimeError("Strict paired outputs differ")
    report["completed"] = True
    (args.output / "summary.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
