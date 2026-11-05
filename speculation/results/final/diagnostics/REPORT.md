# Recomputed experiment summary

Times are medians of subsequent rounds within each process, then medians across seeds.
They describe an ordered engine-local cache history; first batch-8 call can inherit batch-1 cache entries.
Trace runs contain instrumentation overhead and must not supply production speedup claims.

| workload | mode | median s | per-seed medians s | ratio vs base |
|---|---|---:|---|---:|
| conflict/b1 | base | 1.119144 | 75:1.119144 | 1.000 |
| conflict/b1 | gated | 1.102099 | 75:1.102099 | 1.015 |
| conflict/b1 | native | 1.108534 | 75:1.108534 | 1.010 |
| conflict/b8 | base | 1.287951 | 75:1.287951 | 1.000 |
| conflict/b8 | gated | 0.719740 | 75:0.719740 | 1.789 |
| conflict/b8 | native | 1.209690 | 75:1.209690 | 1.065 |
| general/b1 | base | 1.109709 | 75:1.109709 | 1.000 |
| general/b1 | gated | 1.250028 | 75:1.250028 | 0.888 |
| general/b1 | native | 1.237670 | 75:1.237670 | 0.897 |
| general/b8 | base | 1.280143 | 75:1.280143 | 1.000 |
| general/b8 | gated | 1.309365 | 75:1.309365 | 0.978 |
| general/b8 | native | 1.376544 | 75:1.376544 | 0.930 |
| repeat/b1 | base | 1.108318 | 75:1.108318 | 1.000 |
| repeat/b1 | gated | 0.164667 | 75:0.164667 | 6.731 |
| repeat/b1 | native | 1.266646 | 75:1.266646 | 0.875 |
| repeat/b8 | base | 1.279092 | 75:1.279092 | 1.000 |
| repeat/b8 | gated | 0.781048 | 75:0.781048 | 1.638 |
| repeat/b8 | native | 1.384985 | 75:1.384985 | 0.924 |

## Full token comparisons

- gated-s75-vs-base: 58/81 identical; 23 differences (see summary.json).
- gated-s75-vs-native: 61/81 identical; 20 differences (see summary.json).
- native-s75-vs-base: 58/81 identical; 23 differences (see summary.json).

## Verification traces

```json
{
  "base-s75": {
    "repeat/b1": {
      "target_steps": 384,
      "native_cpu_ms_median": null,
      "extension_cpu_ms_median": null
    },
    "repeat/b8": {
      "target_steps": 387,
      "native_cpu_ms_median": null,
      "extension_cpu_ms_median": null
    },
    "general/b1": {
      "target_steps": 384,
      "native_cpu_ms_median": null,
      "extension_cpu_ms_median": null
    },
    "general/b8": {
      "target_steps": 387,
      "native_cpu_ms_median": null,
      "extension_cpu_ms_median": null
    },
    "conflict/b1": {
      "target_steps": 384,
      "native_cpu_ms_median": null,
      "extension_cpu_ms_median": null
    },
    "conflict/b8": {
      "target_steps": 387,
      "native_cpu_ms_median": null,
      "extension_cpu_ms_median": null
    },
    "final_stats": {},
    "max_keys": 0,
    "matched_requests": 81
  },
  "gated-s75": {
    "repeat/b1": {
      "target_steps": 157,
      "native_scheduled": 561,
      "native_accepted": 3,
      "shared_scheduled": 224,
      "shared_accepted": 224,
      "native_cpu_ms_median": 0.051951,
      "extension_cpu_ms_median": 0.042936
    },
    "repeat/b8": {
      "target_steps": 160,
      "shared_scheduled": 2512,
      "shared_accepted": 2464,
      "native_scheduled": 1280,
      "native_accepted": 6,
      "native_cpu_ms_median": 0.0557335,
      "extension_cpu_ms_median": 0.064891
    },
    "general/b1": {
      "target_steps": 362,
      "native_scheduled": 259,
      "native_accepted": 22,
      "native_cpu_ms_median": 0.051514,
      "extension_cpu_ms_median": 0.047344
    },
    "general/b8": {
      "target_steps": 368,
      "shared_scheduled": 960,
      "shared_accepted": 762,
      "native_scheduled": 1441,
      "native_accepted": 101,
      "native_cpu_ms_median": 0.062392,
      "extension_cpu_ms_median": 0.177993
    },
    "conflict/b1": {
      "target_steps": 326,
      "native_scheduled": 1167,
      "native_accepted": 55,
      "shared_scheduled": 40,
      "shared_accepted": 6,
      "native_cpu_ms_median": 0.052169,
      "extension_cpu_ms_median": 0.043025
    },
    "conflict/b8": {
      "target_steps": 234,
      "shared_scheduled": 2280,
      "shared_accepted": 2026,
      "native_scheduled": 2394,
      "native_accepted": 134,
      "native_cpu_ms_median": 0.0592995,
      "extension_cpu_ms_median": 0.10773250000000001
    },
    "final_stats": {
      "lookups": 5448,
      "misses": 4696,
      "insertions": 21544,
      "expired_entries": 0,
      "self_excluded": 2,
      "retrieved_proposals": 752,
      "retrieved_tokens": 6016,
      "verified_proposals": 752,
      "verified_tokens": 6016,
      "accepted_tokens": 5482,
      "gate_blocks": 10
    },
    "max_keys": 7137,
    "matched_requests": 81
  },
  "native-s75": {
    "repeat/b1": {
      "target_steps": 375,
      "native_scheduled": 1635,
      "native_accepted": 9,
      "native_cpu_ms_median": 0.050401,
      "extension_cpu_ms_median": 0.005877
    },
    "repeat/b8": {
      "target_steps": 378,
      "native_scheduled": 13241,
      "native_accepted": 72,
      "native_cpu_ms_median": 0.065194,
      "extension_cpu_ms_median": 0.008449
    },
    "general/b1": {
      "target_steps": 362,
      "native_scheduled": 259,
      "native_accepted": 22,
      "native_cpu_ms_median": 0.049944,
      "extension_cpu_ms_median": 0.005938
    },
    "general/b8": {
      "target_steps": 384,
      "native_scheduled": 2090,
      "native_accepted": 161,
      "native_cpu_ms_median": 0.0632625,
      "extension_cpu_ms_median": 0.0070845000000000005
    },
    "conflict/b1": {
      "target_steps": 329,
      "native_scheduled": 1199,
      "native_accepted": 58,
      "native_cpu_ms_median": 0.050819,
      "extension_cpu_ms_median": 0.005883
    },
    "conflict/b8": {
      "target_steps": 335,
      "native_scheduled": 9650,
      "native_accepted": 493,
      "native_cpu_ms_median": 0.065796,
      "extension_cpu_ms_median": 0.007998
    },
    "final_stats": {},
    "max_keys": 0,
    "matched_requests": 81
  }
}
```
