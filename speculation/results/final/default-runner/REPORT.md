# Recomputed experiment summary

Times are medians of subsequent rounds within each process, then medians across seeds.
They describe an ordered engine-local cache history; first batch-8 call can inherit batch-1 cache entries.
Trace runs contain instrumentation overhead and must not supply production speedup claims.

| workload | mode | median s | per-seed medians s | ratio vs base |
|---|---|---:|---|---:|
| conflict/b1 | base | 1.319480 | 71:1.319480 | 1.000 |
| conflict/b1 | native | 1.196579 | 71:1.196579 | 1.103 |
| conflict/b8 | base | 1.512727 | 71:1.512727 | 1.000 |
| conflict/b8 | native | 1.352731 | 71:1.352731 | 1.118 |
| general/b1 | base | 1.306143 | 71:1.306143 | 1.000 |
| general/b1 | native | 1.406232 | 71:1.406232 | 0.929 |
| general/b8 | base | 1.534807 | 71:1.534807 | 1.000 |
| general/b8 | native | 1.589167 | 71:1.589167 | 0.966 |
| repeat/b1 | base | 1.313982 | 71:1.313982 | 1.000 |
| repeat/b1 | native | 1.445081 | 71:1.445081 | 0.909 |
| repeat/b8 | base | 1.521080 | 71:1.521080 | 1.000 |
| repeat/b8 | native | 1.605522 | 71:1.605522 | 0.947 |

## Full token comparisons

- native-s71-vs-base: 77/108 identical; 31 differences (see summary.json).

## Verification traces

```json
{}
```
