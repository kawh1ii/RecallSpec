"""Sequential single-GPU runs; preserve failed evidence and native source baselines."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser()
p.add_argument("--model", required=True)
p.add_argument("--output", required=True)
p.add_argument("--modes", default="base,native,ungated,gated")
p.add_argument("--seeds", default="71,72,73")
p.add_argument("--rounds", type=int, default=4)
p.add_argument("--batches", default="1,8")
p.add_argument("--kinds", default="repeat,general,conflict")
p.add_argument("--tokens", type=int, default=128)
p.add_argument("--trace", action="store_true")
p.add_argument("--eager", action="store_true")
p.add_argument("--batch-invariant", action="store_true")
p.add_argument("--prefix-cache", action="store_true")
p.add_argument("--runner", choices=["v1", "v2"], default="v1")
p.add_argument("--config")
a = p.parse_args()
os.environ["PATH"] = str(Path(sys.executable).parent) + os.pathsep + os.environ.get("PATH", "")
os.environ["OMP_NUM_THREADS"] = "4"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
out = Path(a.output).resolve()
out.mkdir(parents=True, exist_ok=True)
protocol = out / "protocol.json"
if protocol.exists() and json.loads(protocol.read_text()) != vars(a):
    raise SystemExit("Existing protocol differs")
protocol.write_text(json.dumps(vars(a), indent=2))
try:
    for seed_index, seed in enumerate(a.seeds.split(",")):
        modes = a.modes.split(",")
        # Predetermined rotation reduces fixed ordering bias; no best-run selection.
        modes = modes[seed_index % len(modes):] + modes[:seed_index % len(modes)]
        for mode in modes:
            dest = out / f"{mode}-s{seed}.json"
            if dest.exists() and json.loads(dest.read_text()).get("completed"):
                print("SKIP complete", dest, flush=True)
                continue
            if dest.exists():
                raise SystemExit(f"Incomplete prior run: preserve {dest} and use a new output path")
            patch = [sys.executable, str(ROOT / "tools/patch_vllm.py")]
            if mode in ("base", "native") and not a.trace:
                patch.append("--restore")
            subprocess.run(patch, check=True)
            cmd = [sys.executable, str(ROOT / "tools/benchmark.py"), "--model", a.model,
                   "--mode", mode, "--output", str(dest), "--seed", seed,
                   "--rounds", str(a.rounds), "--batches", a.batches,
                   "--kinds", a.kinds, "--tokens", str(a.tokens)]
            cmd += ["--runner", a.runner]
            for flag in ("eager", "batch_invariant", "prefix_cache"):
                if getattr(a, flag): cmd.append("--" + flag.replace("_", "-"))
            if a.config: cmd += ["--config", a.config]
            if a.trace: cmd += ["--trace", str(out / f"{mode}-s{seed}-trace")]
            print("RUN", mode, seed, flush=True)
            with dest.with_suffix(".log").open("w") as log:
                subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, check=True,
                               env={k: v for k, v in os.environ.items()
                                    if not k.startswith("RECALLSPEC_")})
finally:
    subprocess.run([sys.executable, str(ROOT / "tools/patch_vllm.py"), "--restore"], check=True)
