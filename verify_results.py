"""Recompute median, speedups, and exact token checks from saved raw runs."""

import json
from pathlib import Path


ROOT = Path(__file__).parent / "results"


def load(mode, workload, batch, apc=False):
    suffix = "_apc" if apc else ""
    name = f"spec_model3b_{mode}_{workload}_b{batch}{suffix}.json"
    return json.loads((ROOT / name).read_text())


def exact(reference, candidate):
    a = reference["round_token_ids"]
    b = candidate["round_token_ids"]
    assert len(a) >= len(b)
    return sum(x == y for row_a, row_b in zip(a, b)
               for x, y in zip(row_a, row_b)), sum(map(len, b))


for workload, batch in (("shared_tail", 1), ("shared_tail", 8),
                        ("unique_general", 1)):
    base = load("base", workload, batch)
    static = load("static8", workload, batch)
    shared = load("shared8", workload, batch)
    print(f"{workload} batch={batch}")
    for name, result in (("base", base), ("static8", static),
                         ("shared8", shared)):
        print(f"  {name}: median={result['median_seconds']:.6f}s, "
              f"speedup={base['median_seconds']/result['median_seconds']:.2f}x, "
              f"exact={exact(base, result)}")
    if workload == "shared_tail":
        apc = load("base", workload, batch, apc=True)
        print(f"  base+APC: median={apc['median_seconds']:.6f}s, "
              f"exact={exact(base, apc)}")
