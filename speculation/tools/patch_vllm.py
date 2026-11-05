"""Version/hash locked, idempotent and reversible worker integration."""
import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser()
p.add_argument("--restore", action="store_true")
p.add_argument("--check", action="store_true")
a = p.parse_args()
m = json.loads((root / "patches/manifest.json").read_text())
if sys.prefix == sys.base_prefix:
    raise SystemExit("Use an isolated virtual environment")
if importlib.metadata.version("vllm") != m["version"]:
    raise SystemExit("Unsupported vLLM version")
package = Path(importlib.util.find_spec("vllm").origin).parent
target = package / m["target"]
ngram = package / "v1/spec_decode/ngram_proposer.py"
if hashlib.sha256(ngram.read_bytes()).hexdigest() != m["ngram_sha256"]:
    raise SystemExit("Unknown ngram source")
source = target.read_text()
digest = hashlib.sha256(source.encode()).hexdigest()
if digest not in (m["original_sha256"], m["patched_sha256"]):
    raise SystemExit("Unknown worker source: " + digest)
if a.check:
    print(json.dumps({"sha256": digest, "patched": digest == m["patched_sha256"]}))
    raise SystemExit(0)
desired = m["original_sha256"] if a.restore else m["patched_sha256"]
if digest != desired:
    for before, after in reversed(m["changes"]) if a.restore else m["changes"]:
        if a.restore:
            before, after = after, before
        if source.count(before) != 1:
            raise SystemExit("Patch anchor mismatch")
        source = source.replace(before, after, 1)
    assert hashlib.sha256(source.encode()).hexdigest() == desired
    compile(source, str(target), "exec")
    target.write_text(source)
print("Restored worker" if a.restore else "Installed RecallSpec hooks")
