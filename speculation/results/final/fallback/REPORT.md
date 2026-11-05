# Recomputed experiment summary

Times are medians of subsequent rounds within each process, then medians across seeds.
They describe an ordered engine-local cache history; first batch-8 call can inherit batch-1 cache entries.
Trace runs contain instrumentation overhead and must not supply production speedup claims.

| workload | mode | median s | per-seed medians s | ratio vs base |
|---|---|---:|---|---:|
| conflict/b1 | gated | 1.067991 | 71:1.067991 | — |
| conflict/b8 | gated | 0.383239 | 71:0.383239 | — |
| general/b1 | gated | 1.245351 | 71:1.245351 | — |
| general/b8 | gated | 1.159403 | 71:1.159403 | — |
| repeat/b1 | gated | 0.161286 | 71:0.161286 | — |
| repeat/b8 | gated | 0.295996 | 71:0.295996 | — |

## Full token comparisons


## Verification traces

```json
{}
```
