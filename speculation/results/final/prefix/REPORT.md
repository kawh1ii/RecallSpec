# Recomputed experiment summary

Times are medians of subsequent rounds within each process, then medians across seeds.
They describe an ordered engine-local cache history; first batch-8 call can inherit batch-1 cache entries.
Trace runs contain instrumentation overhead and must not supply production speedup claims.

| workload | mode | median s | per-seed medians s | ratio vs base |
|---|---|---:|---|---:|
| conflict/b1 | base | 1.092301 | 71:1.092301 | 1.000 |
| conflict/b1 | gated | 0.642980 | 71:0.642980 | 1.699 |
| conflict/b8 | base | 1.258053 | 71:1.258053 | 1.000 |
| conflict/b8 | gated | 0.708433 | 71:0.708433 | 1.776 |
| general/b1 | base | 1.095014 | 71:1.095014 | 1.000 |
| general/b1 | gated | 1.248209 | 71:1.248209 | 0.877 |
| general/b8 | base | 1.262455 | 71:1.262455 | 1.000 |
| general/b8 | gated | 1.269891 | 71:1.269891 | 0.994 |
| repeat/b1 | base | 1.092873 | 71:1.092873 | 1.000 |
| repeat/b1 | gated | 0.162290 | 71:0.162290 | 6.734 |
| repeat/b8 | base | 1.252533 | 71:1.252533 | 1.000 |
| repeat/b8 | gated | 0.749437 | 71:0.749437 | 1.671 |

## Full token comparisons

- gated-s71-vs-base: 59/81 identical; 22 differences (see summary.json).

## Verification traces

```json
{}
```
