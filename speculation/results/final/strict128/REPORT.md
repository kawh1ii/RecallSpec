# Recomputed experiment summary

Times are medians of subsequent rounds within each process, then medians across seeds.
They describe an ordered engine-local cache history; first batch-8 call can inherit batch-1 cache entries.
Trace runs contain instrumentation overhead and must not supply production speedup claims.

| workload | mode | median s | per-seed medians s | ratio vs base |
|---|---|---:|---|---:|
| conflict/b1 | base | 3.211343 | 77:3.211343 | 1.000 |
| conflict/b1 | gated | 2.654032 | 77:2.654032 | 1.210 |
| conflict/b1 | native | 2.711273 | 77:2.711273 | 1.184 |
| conflict/b8 | base | 3.176669 | 77:3.176669 | 1.000 |
| conflict/b8 | gated | 1.545419 | 77:1.545419 | 2.056 |
| conflict/b8 | native | 2.677264 | 77:2.677264 | 1.187 |
| general/b1 | base | 3.206495 | 77:3.206495 | 1.000 |
| general/b1 | gated | 3.038313 | 77:3.038313 | 1.055 |
| general/b1 | native | 3.041092 | 77:3.041092 | 1.054 |
| general/b8 | base | 3.169671 | 77:3.169671 | 1.000 |
| general/b8 | gated | 2.926783 | 77:2.926783 | 1.083 |
| general/b8 | native | 3.183775 | 77:3.183775 | 0.996 |
| repeat/b1 | base | 3.196255 | 77:3.196255 | 1.000 |
| repeat/b1 | gated | 0.396485 | 77:0.396485 | 8.061 |
| repeat/b1 | native | 3.083380 | 77:3.083380 | 1.037 |
| repeat/b8 | base | 3.161428 | 77:3.161428 | 1.000 |
| repeat/b8 | gated | 0.412047 | 77:0.412047 | 7.672 |
| repeat/b8 | native | 2.997352 | 77:2.997352 | 1.055 |

## Full token comparisons

- gated-s77-vs-base: 81/81 identical; 0 differences (see summary.json).
- gated-s77-vs-native: 81/81 identical; 0 differences (see summary.json).
- native-s77-vs-base: 81/81 identical; 0 differences (see summary.json).

## Verification traces

```json
{
  "base-s77": {
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
  "gated-s77": {
    "repeat/b1": {
      "target_steps": 157,
      "native_scheduled": 561,
      "native_accepted": 3,
      "shared_scheduled": 224,
      "shared_accepted": 224,
      "native_cpu_ms_median": 0.054153,
      "extension_cpu_ms_median": 0.043428
    },
    "repeat/b8": {
      "target_steps": 51,
      "shared_scheduled": 2688,
      "shared_accepted": 2688,
      "native_scheduled": 192,
      "native_accepted": 0,
      "native_cpu_ms_median": 0.068578,
      "extension_cpu_ms_median": 0.8120689999999999
    },
    "general/b1": {
      "target_steps": 356,
      "native_scheduled": 196,
      "native_accepted": 28,
      "native_cpu_ms_median": 0.053454,
      "extension_cpu_ms_median": 0.0498425
    },
    "general/b8": {
      "target_steps": 363,
      "shared_scheduled": 1128,
      "shared_accepted": 971,
      "native_scheduled": 1400,
      "native_accepted": 86,
      "native_cpu_ms_median": 0.064003,
      "extension_cpu_ms_median": 0.159404
    },
    "conflict/b1": {
      "target_steps": 321,
      "native_scheduled": 1136,
      "native_accepted": 58,
      "shared_scheduled": 40,
      "shared_accepted": 7,
      "native_cpu_ms_median": 0.054136,
      "extension_cpu_ms_median": 0.043766
    },
    "conflict/b8": {
      "target_steps": 235,
      "shared_scheduled": 2320,
      "shared_accepted": 2078,
      "native_scheduled": 2203,
      "native_accepted": 118,
      "native_cpu_ms_median": 0.059673,
      "extension_cpu_ms_median": 0.093252
    },
    "final_stats": {
      "lookups": 5139,
      "misses": 4338,
      "insertions": 21506,
      "expired_entries": 0,
      "retrieved_proposals": 801,
      "retrieved_tokens": 6408,
      "verified_proposals": 800,
      "verified_tokens": 6400,
      "accepted_tokens": 5968,
      "self_excluded": 1,
      "gate_blocks": 5
    },
    "max_keys": 6267,
    "matched_requests": 81
  },
  "native-s77": {
    "repeat/b1": {
      "target_steps": 375,
      "native_scheduled": 1635,
      "native_accepted": 9,
      "native_cpu_ms_median": 0.054421,
      "extension_cpu_ms_median": 0.006316
    },
    "repeat/b8": {
      "target_steps": 378,
      "native_scheduled": 13080,
      "native_accepted": 72,
      "native_cpu_ms_median": 0.0685775,
      "extension_cpu_ms_median": 0.0088205
    },
    "general/b1": {
      "target_steps": 356,
      "native_scheduled": 196,
      "native_accepted": 28,
      "native_cpu_ms_median": 0.054299,
      "extension_cpu_ms_median": 0.006533499999999999
    },
    "general/b8": {
      "target_steps": 384,
      "native_scheduled": 2099,
      "native_accepted": 158,
      "native_cpu_ms_median": 0.066325,
      "extension_cpu_ms_median": 0.0075274999999999995
    },
    "conflict/b1": {
      "target_steps": 326,
      "native_scheduled": 1165,
      "native_accepted": 60,
      "native_cpu_ms_median": 0.0542075,
      "extension_cpu_ms_median": 0.006328500000000001
    },
    "conflict/b8": {
      "target_steps": 334,
      "native_scheduled": 9346,
      "native_accepted": 482,
      "native_cpu_ms_median": 0.06848099999999999,
      "extension_cpu_ms_median": 0.0083175
    },
    "final_stats": {},
    "max_keys": 0,
    "matched_requests": 81
  }
}
```
