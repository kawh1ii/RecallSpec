# Recomputed experiment summary

Times are medians of subsequent rounds within each process, then medians across seeds.
They describe an ordered engine-local cache history; first batch-8 call can inherit batch-1 cache entries.
Trace runs contain instrumentation overhead and must not supply production speedup claims.

| workload | mode | median s | per-seed medians s | ratio vs base |
|---|---|---:|---|---:|
| general/b1 | base | 2.119359 | 76:2.119359 | 1.000 |
| general/b1 | gated | 2.187283 | 76:2.187283 | 0.969 |
| general/b8 | base | 2.234596 | 76:2.234596 | 1.000 |
| general/b8 | gated | 1.955586 | 76:1.955586 | 1.143 |
| repeat/b1 | base | 2.121510 | 76:2.121510 | 1.000 |
| repeat/b1 | gated | 0.283819 | 76:0.283819 | 7.475 |
| repeat/b8 | base | 2.241796 | 76:2.241796 | 1.000 |
| repeat/b8 | gated | 0.387900 | 76:0.387900 | 5.779 |

## Full token comparisons

- gated-s76-vs-base: 33/54 identical; 21 differences (see summary.json).

## Verification traces

```json
{}
```
