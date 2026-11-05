"""Frozen validation stages, sequential on one GPU. No implicit resume of failures."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser()
p.add_argument("--model", required=True)
p.add_argument("--output", required=True)
p.add_argument("--model7b")
a = p.parse_args()
out = Path(a.output).resolve()
out.mkdir(parents=True, exist_ok=True)
fingerprint = {str(f.relative_to(ROOT)): hashlib.sha256(f.read_bytes()).hexdigest()
               for folder in ("src", "tools", "patches") for f in sorted((ROOT / folder).rglob("*"))
               if f.is_file() and "__pycache__" not in str(f) and not f.name.startswith("._")}
selection = out / "source-fingerprint.json"
if selection.exists() and json.loads(selection.read_text()) != fingerprint:
    raise SystemExit("Code changed; use a fresh validation directory")
selection.write_text(json.dumps(fingerprint, indent=2))
fallback = out / "fallback.json"
fallback.write_text(json.dumps({"shared_first": False}))
stages = [
    ("strict", ["--seeds", "74", "--rounds", "3", "--tokens", "64",
                "--modes", "base,native,gated", "--batch-invariant", "--trace"]),
    ("performance", ["--seeds", "71,72,73", "--rounds", "4"]),
    ("diagnostics", ["--seeds", "75", "--rounds", "3", "--trace",
                     "--modes", "base,native,gated"]),
    ("fallback", ["--seeds", "71", "--rounds", "4", "--modes", "gated",
                  "--config", str(fallback)]),
    ("prefix", ["--seeds", "71", "--rounds", "3", "--modes", "base,gated", "--prefix-cache"]),
    ("default-runner", ["--seeds", "71", "--rounds", "4", "--modes", "base,native",
                        "--runner", "v2"]),
]
if a.model7b:
    stages.append(("7b", ["--seeds", "76", "--rounds", "3", "--modes", "base,gated",
                          "--kinds", "repeat,general"]))
for stage, extra in stages:
    print("STAGE", stage, flush=True)
    model = a.model7b if stage == "7b" else a.model
    subprocess.run([sys.executable, str(ROOT / "tools/run_matrix.py"),
                    "--model", model, "--output", str(out / stage)] + extra, check=True)
    subprocess.run([sys.executable, str(ROOT / "tools/analyze.py"), str(out / stage)], check=True)
    (out / (stage + ".done")).write_text(json.dumps({"source_fingerprint": fingerprint}))
print("ALL_STAGES_COMPLETED", flush=True)
