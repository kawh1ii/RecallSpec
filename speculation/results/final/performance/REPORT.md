# Recomputed experiment summary

Times are medians of subsequent rounds within each process, then medians across seeds.
They describe an ordered engine-local cache history; first batch-8 call can inherit batch-1 cache entries.
Trace runs contain instrumentation overhead and must not supply production speedup claims.

| workload | mode | median s | per-seed medians s | ratio vs base |
|---|---|---:|---|---:|
| conflict/b1 | base | 1.092938 | 71:1.092938, 72:1.092716, 73:1.093735 | 1.000 |
| conflict/b1 | gated | 1.072877 | 71:1.066941, 72:1.076465, 73:1.072877 | 1.019 |
| conflict/b1 | native | 1.087302 | 71:1.087302, 72:1.095411, 73:1.078641 | 1.005 |
| conflict/b1 | ungated | 1.070639 | 71:1.070639, 72:1.067334, 73:1.073995 | 1.021 |
| conflict/b8 | base | 1.273948 | 71:1.276282, 72:1.273948, 73:1.265982 | 1.000 |
| conflict/b8 | gated | 0.259194 | 71:0.266981, 72:0.257642, 73:0.259194 | 4.915 |
| conflict/b8 | native | 1.192614 | 71:1.192614, 72:1.193344, 73:1.187090 | 1.068 |
| conflict/b8 | ungated | 0.261912 | 71:0.271346, 72:0.257959, 73:0.261912 | 4.864 |
| general/b1 | base | 1.091469 | 71:1.091598, 72:1.091469, 73:1.091360 | 1.000 |
| general/b1 | gated | 1.240529 | 71:1.238701, 72:1.240529, 73:1.286896 | 0.880 |
| general/b1 | native | 1.246552 | 71:1.230194, 72:1.246552, 73:1.247873 | 0.876 |
| general/b1 | ungated | 1.234269 | 71:1.234269, 72:1.231983, 73:1.261365 | 0.884 |
| general/b8 | base | 1.261601 | 71:1.267054, 72:1.261601, 73:1.261348 | 1.000 |
| general/b8 | gated | 1.230310 | 71:1.249829, 72:1.230310, 73:1.166503 | 1.025 |
| general/b8 | native | 1.346400 | 71:1.359494, 72:1.344570, 73:1.346400 | 0.937 |
| general/b8 | ungated | 1.225093 | 71:1.243555, 72:1.225093, 73:1.165987 | 1.030 |
| repeat/b1 | base | 1.088298 | 71:1.089098, 72:1.088298, 73:1.086215 | 1.000 |
| repeat/b1 | gated | 0.160450 | 71:0.161298, 72:0.160429, 73:0.160450 | 6.783 |
| repeat/b1 | native | 1.234533 | 71:1.234533, 72:1.234394, 73:1.239333 | 0.882 |
| repeat/b1 | ungated | 0.160583 | 71:0.160409, 72:0.160583, 73:0.160991 | 6.777 |
| repeat/b8 | base | 1.266996 | 71:1.266996, 72:1.276063, 73:1.258921 | 1.000 |
| repeat/b8 | gated | 0.210637 | 71:0.209805, 72:0.210637, 73:0.211065 | 6.015 |
| repeat/b8 | native | 1.356239 | 71:1.358037, 72:1.352435, 73:1.356239 | 0.934 |
| repeat/b8 | ungated | 0.209784 | 71:0.220815, 72:0.209432, 73:0.209784 | 6.040 |

## Full token comparisons

- gated-s71-vs-base: 81/108 identical; 27 differences (see summary.json).
- gated-s71-vs-native: 82/108 identical; 26 differences (see summary.json).
- gated-s72-vs-base: 76/108 identical; 32 differences (see summary.json).
- gated-s72-vs-native: 82/108 identical; 26 differences (see summary.json).
- gated-s73-vs-base: 84/108 identical; 24 differences (see summary.json).
- gated-s73-vs-native: 83/108 identical; 25 differences (see summary.json).
- native-s71-vs-base: 80/108 identical; 28 differences (see summary.json).
- native-s72-vs-base: 79/108 identical; 29 differences (see summary.json).
- native-s73-vs-base: 81/108 identical; 27 differences (see summary.json).
- ungated-s71-vs-base: 81/108 identical; 27 differences (see summary.json).
- ungated-s71-vs-native: 82/108 identical; 26 differences (see summary.json).
- ungated-s72-vs-base: 76/108 identical; 32 differences (see summary.json).
- ungated-s72-vs-native: 82/108 identical; 26 differences (see summary.json).
- ungated-s73-vs-base: 84/108 identical; 24 differences (see summary.json).
- ungated-s73-vs-native: 83/108 identical; 25 differences (see summary.json).

## Verification traces

```json
{}
```
