"""Locate the first divergent token and local top-logprob margin."""

import argparse
import json
from pathlib import Path


def load(path):
    data = json.loads(Path(path).read_text())
    return {(item["repetition"], item["variant"]): item
            for item in data["records"]}


def first_diff(a, b):
    return next((i for i, (x, y) in enumerate(zip(a, b)) if x != y),
                None if len(a) == len(b) else min(len(a), len(b)))


def context(item, pos):
    if pos is None:
        return None
    probs = item["top_logprobs"][pos] if pos < len(item["top_logprobs"]) else {}
    ranks = sorted(probs.items(), key=lambda kv: kv[1], reverse=True)
    margin = ranks[0][1] - ranks[1][1] if len(ranks) > 1 else None
    return {"token": item["token_ids"][pos], "top": ranks[:5],
            "top1_top2_margin": margin}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("base")
    parser.add_argument("native")
    parser.add_argument("shared")
    args = parser.parse_args()
    modes = {name: load(getattr(args, name))
             for name in ("base", "native", "shared")}
    for key in sorted(modes["base"]):
        b, n, s = (modes[name][key] for name in modes)
        differences = {"base_native": first_diff(b["token_ids"], n["token_ids"]),
                       "base_shared": first_diff(b["token_ids"], s["token_ids"]),
                       "native_shared": first_diff(n["token_ids"], s["token_ids"])}
        pos = min((v for v in differences.values() if v is not None), default=None)
        print(json.dumps({"repetition_variant": key, "differences": differences,
                          "first_position": pos,
                          "logprobs": {name: context(modes[name][key], pos)
                                       for name in modes}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
