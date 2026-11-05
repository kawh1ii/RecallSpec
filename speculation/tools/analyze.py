"""Recompute paired comparisons and source-attributed verification from raw data."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import statistics


def compare(reference, candidate):
    a = reference["records"]; b = candidate["records"]
    if len(a) != len(b): raise ValueError("record count mismatch")
    stats = Counter(); diffs = []
    for ra, rb in zip(a, b):
        key = (ra["kind"], ra["batch"], ra["round"])
        if key != (rb["kind"], rb["batch"], rb["round"]):
            raise ValueError("workload mismatch")
        if len(ra["outputs"]) != len(rb["outputs"]): raise ValueError("batch mismatch")
        for i, (oa, ob) in enumerate(zip(ra["outputs"], rb["outputs"])):
            if oa["prompt_token_ids"] != ob["prompt_token_ids"]:
                raise ValueError("input token mismatch")
            ta, tb = oa["token_ids"], ob["token_ids"]
            stats["total"] += 1
            if ta == tb:
                stats["identical"] += 1
            else:
                pos = next((j for j, (x, y) in enumerate(zip(ta, tb)) if x != y), min(len(ta), len(tb)))
                diffs.append({"kind": key[0], "batch": key[1], "round": key[2],
                              "item": i, "first_difference": pos,
                              "reference": ta[pos:pos+4], "candidate": tb[pos:pos+4]})
    return {**stats, "differences": diffs}


def trace_summary(directory, records):
    events = []
    for path in sorted(directory.glob("*.jsonl")):
        events.extend(json.loads(line) for line in path.read_text().splitlines())
    if not events:
        raise ValueError("Missing trace: cannot establish integration execution")
    # 0.32 input_processor.py appends '-'+8 hex characters to external IDs.
    # Resolve the actual worker IDs from schedule events; require a unique
    # mapping rather than silently dropping requests when matching metrics.
    internal_ids = set()
    for event in events:
        if event["event"] == "schedule":
            internal_ids.update(event["requests"])
    external_to_internal = defaultdict(set)
    for rid in internal_ids:
        external = re.sub(r"-[0-9a-f]{8}$", "", rid)
        external_to_internal[external].add(rid)
    groups = defaultdict(set)
    for r in records:
        for output in r["outputs"]:
            external = output["request_id"]
            candidates = external_to_internal[external]
            if len(candidates) != 1:
                raise ValueError(f"Missing or ambiguous worker ID for {external}: {candidates}")
            groups[f'{r["kind"]}/b{r["batch"]}'].update(candidates)
    out = {}
    for group, ids in groups.items():
        counts = Counter(); native_times = []; extra_times = []
        for event in events:
            if event["event"] == "schedule":
                if ids.intersection(event["requests"]): counts["target_steps"] += 1
            if event["event"] == "propose":
                relevant = [e for e in event["feedback"] if e["request_id"] in ids]
                for e in relevant:
                    counts[e["source"] + "_scheduled"] += e["scheduled"]
                    counts[e["source"] + "_accepted"] += e["accepted"]
                if relevant:
                    native_times.append(event["native_ns"] / 1e6)
                    extra_times.append((event["total_ns"] - event["native_ns"]) / 1e6)
        out[group] = {**counts,
                      "native_cpu_ms_median": statistics.median(native_times) if native_times else None,
                      "extension_cpu_ms_median": statistics.median(extra_times) if extra_times else None}
    proposals = [e for e in events if e["event"] == "propose"]
    out["final_stats"] = proposals[-1]["stats"] if proposals else {}
    out["max_keys"] = max((e.get("keys", 0) for e in events), default=0)
    out["matched_requests"] = sum(len(ids) for ids in groups.values())
    return out


def analyze(directory):
    files = {}
    for path in sorted(directory.glob("*-s*.json")):
        d = json.loads(path.read_text())
        if not d.get("completed"):
            raise ValueError("Incomplete run: " + str(path))
        files[(d["args"]["mode"], d["args"]["seed"])] = d
    if not files: raise ValueError("No completed runs")
    tables = defaultdict(dict)
    for (mode, seed), data in files.items():
        groups = defaultdict(list)
        for r in data["records"]:
            if r["round"] > 0:
                groups[f'{r["kind"]}/b{r["batch"]}'].append(r["duration_s"])
        for group, values in groups.items():
            tables[group].setdefault(mode, {})[str(seed)] = statistics.median(values)
    comparisons = {}
    for (mode, seed), data in files.items():
        if mode != "base" and ("base", seed) in files:
            comparisons[f"{mode}-s{seed}-vs-base"] = compare(files[("base", seed)], data)
        if mode in ("gated", "ungated") and ("native", seed) in files:
            comparisons[f"{mode}-s{seed}-vs-native"] = compare(files[("native", seed)], data)
    traces = {}
    for (mode, seed), data in files.items():
        directory_trace = directory / f"{mode}-s{seed}-trace"
        if directory_trace.exists():
            traces[f"{mode}-s{seed}"] = trace_summary(directory_trace, data["records"])
    summary = {"timings_by_seed": dict(tables), "comparisons": comparisons, "traces": traces,
               "runs": len(files), "requests": sum(len(r["outputs"]) for d in files.values() for r in d["records"])}
    (directory / "summary.json").write_text(json.dumps(summary, indent=2))
    lines = ["# Recomputed experiment summary", "", "Times are medians of subsequent rounds within each process, then medians across seeds.",
             "They describe an ordered engine-local cache history; first batch-8 call can inherit batch-1 cache entries.",
             "Trace runs contain instrumentation overhead and must not supply production speedup claims.", "",
             "| workload | mode | median s | per-seed medians s | ratio vs base |", "|---|---|---:|---|---:|"]
    for group, modes in sorted(tables.items()):
        base = statistics.median(modes["base"].values()) if "base" in modes else None
        for mode, values in sorted(modes.items()):
            med = statistics.median(values.values())
            ratio = f"{base/med:.3f}" if base is not None else "—"
            lines.append(f"| {group} | {mode} | {med:.6f} | {', '.join(f'{k}:{v:.6f}' for k,v in values.items())} | {ratio} |")
    lines += ["", "## Full token comparisons", ""]
    for name, item in comparisons.items():
        lines.append(f"- {name}: {item.get('identical',0)}/{item['total']} identical; {len(item['differences'])} differences (see summary.json).")
    lines += ["", "## Verification traces", "", "```json", json.dumps(traces, indent=2), "```"]
    (directory / "REPORT.md").write_text("\n".join(lines) + "\n")
    return summary


if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("directory")
    a = p.parse_args(); d = analyze(Path(a.directory))
    print(json.dumps({k: d[k] for k in ("runs", "requests")}, indent=2))
