# Recomputed experiment summary

Times are medians of subsequent rounds within each process, then medians across seeds.
They describe an ordered engine-local cache history; first batch-8 call can inherit batch-1 cache entries.
Trace runs contain instrumentation overhead and must not supply production speedup claims.

| workload | mode | median s | per-seed medians s | ratio vs base |
|---|---|---:|---|---:|
| conflict/b1 | base | 1.599877 | 74:1.599877 | 1.000 |
| conflict/b1 | gated | 1.418700 | 74:1.418700 | 1.128 |
| conflict/b1 | native | 1.465665 | 74:1.465665 | 1.092 |
| conflict/b8 | base | 1.600998 | 74:1.600998 | 1.000 |
| conflict/b8 | gated | 0.889421 | 74:0.889421 | 1.800 |
| conflict/b8 | native | 1.471800 | 74:1.471800 | 1.088 |
| general/b1 | base | 1.598682 | 74:1.598682 | 1.000 |
| general/b1 | gated | 1.451711 | 74:1.451711 | 1.101 |
| general/b1 | native | 1.441088 | 74:1.441088 | 1.109 |
| general/b8 | base | 1.597016 | 74:1.597016 | 1.000 |
| general/b8 | gated | 1.458677 | 74:1.458677 | 1.095 |
| general/b8 | native | 1.601492 | 74:1.601492 | 0.997 |
| repeat/b1 | base | 1.591787 | 74:1.591787 | 1.000 |
| repeat/b1 | gated | 0.199155 | 74:0.199155 | 7.993 |
| repeat/b1 | native | 1.543083 | 74:1.543083 | 1.032 |
| repeat/b8 | base | 1.591995 | 74:1.591995 | 1.000 |
| repeat/b8 | gated | 0.222366 | 74:0.222366 | 7.159 |
| repeat/b8 | native | 1.537234 | 74:1.537234 | 1.036 |

## Full token comparisons

- gated-s74-vs-base: 81/81 identical; 0 differences (see summary.json).
- gated-s74-vs-native: 81/81 identical; 0 differences (see summary.json).
- native-s74-vs-base: 81/81 identical; 0 differences (see summary.json).

## Verification traces

```json
{
  "base-s74": {
    "repeat/b1": {
      "target_steps": 192,
      "native_cpu_ms_median": null,
      "extension_cpu_ms_median": null
    },
    "repeat/b8": {
      "target_steps": 195,
      "native_cpu_ms_median": null,
      "extension_cpu_ms_median": null
    },
    "general/b1": {
      "target_steps": 192,
      "native_cpu_ms_median": null,
      "extension_cpu_ms_median": null
    },
    "general/b8": {
      "target_steps": 195,
      "native_cpu_ms_median": null,
      "extension_cpu_ms_median": null
    },
    "conflict/b1": {
      "target_steps": 192,
      "native_cpu_ms_median": null,
      "extension_cpu_ms_median": null
    },
    "conflict/b8": {
      "target_steps": 195,
      "native_cpu_ms_median": null,
      "extension_cpu_ms_median": null
    },
    "final_stats": {},
    "max_keys": 0,
    "matched_requests": 81
  },
  "gated-s74": {
    "repeat/b1": {
      "target_steps": 79,
      "native_scheduled": 217,
      "native_accepted": 1,
      "shared_scheduled": 112,
      "shared_accepted": 112,
      "native_cpu_ms_median": 0.055762500000000007,
      "extension_cpu_ms_median": 0.043382000000000004
    },
    "repeat/b8": {
      "target_steps": 27,
      "shared_scheduled": 1344,
      "shared_accepted": 1344,
      "native_cpu_ms_median": 0.069748,
      "extension_cpu_ms_median": 0.8076765
    },
    "general/b1": {
      "target_steps": 178,
      "native_scheduled": 99,
      "native_accepted": 14,
      "native_cpu_ms_median": 0.055024,
      "extension_cpu_ms_median": 0.053662
    },
    "general/b8": {
      "target_steps": 182,
      "shared_scheduled": 656,
      "shared_accepted": 567,
      "native_scheduled": 404,
      "native_accepted": 32,
      "native_cpu_ms_median": 0.064258,
      "extension_cpu_ms_median": 0.153722
    },
    "conflict/b1": {
      "target_steps": 175,
      "native_scheduled": 509,
      "native_accepted": 12,
      "shared_scheduled": 16,
      "shared_accepted": 6,
      "native_cpu_ms_median": 0.055084,
      "extension_cpu_ms_median": 0.042338
    },
    "conflict/b8": {
      "target_steps": 131,
      "shared_scheduled": 1016,
      "shared_accepted": 840,
      "native_scheduled": 1582,
      "native_accepted": 51,
      "native_cpu_ms_median": 0.065084,
      "extension_cpu_ms_median": 0.1325875
    },
    "final_stats": {
      "lookups": 2717,
      "misses": 2324,
      "insertions": 10082,
      "expired_entries": 0,
      "retrieved_proposals": 393,
      "retrieved_tokens": 3144,
      "verified_proposals": 393,
      "verified_tokens": 3144,
      "accepted_tokens": 2869,
      "gate_blocks": 2
    },
    "max_keys": 2706,
    "matched_requests": 81
  },
  "native-s74": {
    "repeat/b1": {
      "target_steps": 189,
      "native_scheduled": 651,
      "native_accepted": 3,
      "native_cpu_ms_median": 0.051116499999999995,
      "extension_cpu_ms_median": 0.0059405
    },
    "repeat/b8": {
      "target_steps": 192,
      "native_scheduled": 5208,
      "native_accepted": 24,
      "native_cpu_ms_median": 0.066109,
      "extension_cpu_ms_median": 0.008423
    },
    "general/b1": {
      "target_steps": 178,
      "native_scheduled": 99,
      "native_accepted": 14,
      "native_cpu_ms_median": 0.050441,
      "extension_cpu_ms_median": 0.006268
    },
    "general/b8": {
      "target_steps": 194,
      "native_scheduled": 744,
      "native_accepted": 78,
      "native_cpu_ms_median": 0.06263250000000001,
      "extension_cpu_ms_median": 0.0070895
    },
    "conflict/b1": {
      "target_steps": 179,
      "native_scheduled": 525,
      "native_accepted": 14,
      "native_cpu_ms_median": 0.051513,
      "extension_cpu_ms_median": 0.006045
    },
    "conflict/b8": {
      "target_steps": 183,
      "native_scheduled": 4209,
      "native_accepted": 115,
      "native_cpu_ms_median": 0.065464,
      "extension_cpu_ms_median": 0.007837
    },
    "final_stats": {},
    "max_keys": 0,
    "matched_requests": 81
  }
}
```
