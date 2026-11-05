# Recomputed experiment summary

Times are medians of subsequent rounds within each process, then medians across seeds.
They describe an ordered engine-local cache history; first batch-8 call can inherit batch-1 cache entries.
Trace runs contain instrumentation overhead and must not supply production speedup claims.

| workload | mode | median s | per-seed medians s | ratio vs base |
|---|---|---:|---|---:|
| conflict/b1 | base | 1.696371 | 74:1.696371 | 1.000 |
| conflict/b1 | gated | 1.404171 | 74:1.404171 | 1.208 |
| conflict/b1 | native | 1.414157 | 74:1.414157 | 1.200 |
| conflict/b8 | base | 1.800728 | 74:1.800728 | 1.000 |
| conflict/b8 | gated | 1.426064 | 74:1.426064 | 1.263 |
| conflict/b8 | native | 1.395543 | 74:1.395543 | 1.290 |
| general/b1 | base | 1.690059 | 74:1.690059 | 1.000 |
| general/b1 | gated | 1.540341 | 74:1.540341 | 1.097 |
| general/b1 | native | 1.540578 | 74:1.540578 | 1.097 |
| general/b8 | base | 1.764500 | 74:1.764500 | 1.000 |
| general/b8 | gated | 1.604050 | 74:1.604050 | 1.100 |
| general/b8 | native | 1.610101 | 74:1.610101 | 1.096 |
| repeat/b1 | base | 1.694661 | 74:1.694661 | 1.000 |
| repeat/b1 | gated | 1.693149 | 74:1.693149 | 1.001 |
| repeat/b1 | native | 1.681906 | 74:1.681906 | 1.008 |
| repeat/b8 | base | 1.754453 | 74:1.754453 | 1.000 |
| repeat/b8 | gated | 1.610089 | 74:1.610089 | 1.090 |
| repeat/b8 | native | 1.604705 | 74:1.604705 | 1.093 |

## Full token comparisons

- gated-s74-vs-base: 81/81 identical; 0 differences (see summary.json).
- gated-s74-vs-native: 81/81 identical; 0 differences (see summary.json).
- native-s74-vs-base: 81/81 identical; 0 differences (see summary.json).

## Verification traces

```json
{}
```
