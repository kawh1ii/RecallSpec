"""Join per-request proposal traces to vLLM's scheduled verifications."""

import argparse
from collections import defaultdict
import json
from pathlib import Path
import statistics


def read_rows(folder: Path, pattern: str):
    for file in sorted(folder.glob(pattern)):
        for line in file.read_text().splitlines():
            yield json.loads(line)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("folder", type=Path)
    parser.add_argument("--min-request-id", type=int, default=0,
                        help="Exclude init/warmup request IDs below this value")
    args = parser.parse_args()

    def measured(req_id):
        return req_id.isdecimal() and int(req_id) >= args.min_request_id

    proposals = defaultdict(list)
    times_ms = []
    shared_extra_ms = []
    source_proposals = defaultdict(int)
    for event in read_rows(args.folder, "drafts-*.jsonl"):
        rows = [row for row in event["rows"] if measured(row["req_id"])]
        if rows:
            times_ms.append(event["elapsed_ns"] / 1e6)
            if event.get("shared_extra_ns") is not None:
                shared_extra_ms.append(event["shared_extra_ns"] / 1e6)
        for row in rows:
            if row["draft"]:
                proposals[row["req_id"]].append(row)
                source_proposals[row["source"]] += 1

    counts = defaultdict(lambda: {"steps": 0, "proposed": 0, "accepted": 0})
    unmatched = []
    skipped = 0
    offsets = defaultdict(int)
    target_steps = 0
    target_request_steps = 0
    for event in read_rows(args.folder, "verify-*.jsonl"):
        scheduled_ids = [req_id for req_id in event.get("scheduled_req_ids", [])
                         if measured(req_id)]
        if scheduled_ids:
            target_steps += 1
            target_request_steps += len(scheduled_ids)
        for row in event["rows"]:
            req_id = row["req_id"]
            if not measured(req_id):
                continue
            queue = proposals[req_id]
            cursor = offsets[req_id]
            match = None
            for j in range(cursor, len(queue)):
                draft = queue[j]["draft"]
                if draft[:len(row["draft"])] == row["draft"]:
                    match = j
                    break
            if match is None:
                unmatched.append(req_id)
                continue
            skipped += match - cursor
            offsets[req_id] = match + 1
            source = queue[match]["source"]
            accepted = row["accepted"]
            assert 0 <= accepted <= len(row["draft"])
            counts[source]["steps"] += 1
            counts[source]["proposed"] += len(row["draft"])
            counts[source]["accepted"] += accepted

    unscheduled = skipped + sum(len(rows) - offsets[req_id]
                                for req_id, rows in proposals.items())
    result = {"scheduled_by_source": dict(counts),
              "target_execute_steps": target_steps,
              "target_request_steps": target_request_steps,
              "raw_proposals_by_source": dict(source_proposals),
              "unscheduled_proposals": unscheduled,
              "unmatched_scheduled": len(unmatched),
              "proposer_calls": len(times_ms),
              "proposer_ms_median": statistics.median(times_ms) if times_ms else None,
              "proposer_ms_mean": statistics.mean(times_ms) if times_ms else None,
              "proposer_ms_total": sum(times_ms),
              "shared_extra_ms_median": (statistics.median(shared_extra_ms)
                                         if shared_extra_ms else None),
              "shared_extra_ms_total": sum(shared_extra_ms)}
    for source, values in counts.items():
        values["acceptance_rate"] = (values["accepted"] / values["proposed"]
                                     if values["proposed"] else None)
        values["accepted_per_verification"] = (
            values["accepted"] / values["steps"] if values["steps"] else None)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
