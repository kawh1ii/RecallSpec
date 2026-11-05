# RecallSpec 按需调用原生草稿

共享优先策略原本先给整批请求调用原生 n-gram proposer，再覆盖检索命中的位置。命中位置的原生草稿被直接丢弃。改为先检索、再把命中行的 sampled IDs 置空，利用 vLLM 0.32.0 原生 proposer 的空行跳过逻辑，仅对未覆盖的行生成候选。全命中时跳过整个调用。保留原行号、目标模型验证、反馈口径和批内先查后写顺序。

## 原生组件对照

在源机器的 CPU 上调用真实 vLLM 0.32.0 NgramProposer，原生源码散列与项目锁定的 b7c0a807… 完全一致。用批量 1/8、128/1024 token 上下文和可控共享命中数，逐样本对照返回草稿和完整索引状态。初测 680 组，独立三种子复测 2,040 组，均完全一致。31 项原有回归和两项针对混合批回退与全命中短路的测试通过。

以下是 8 请求、1,024 token 的复测结果。耗时为三种子运行中位数的中位数。CPU proposer 总耗时包括索引提交和查找。

| 共享命中数 | 送入原生的行数，原版 → 新版 | 原生部分 μs，原版 → 新版 | proposer 总耗时 μs，原版 → 新版 |
| ---: | ---: | ---: | ---: |
| 0 | 8 → 8 | 146.7 → 131.7 | 4054.9 → 4364.9 |
| 4 | 8 → 4 | 116.8 → 98.8 | 3885.8 → 3736.1 |
| 8 | 8 → 0 | 178.1 → 0 | 4297.1 → 3886.8 |

全命中确实消除了重复原生工作。零命中还有掩码构造成本，其他组的总耗时方向不一致。现有数字只量 CPU proposer。目标模型验证和端到端效果由独立 GPU 对照评估。

## 复现

使用 RecallSpec 仓库提交 8b8f7c10ff8b2616f72aedc5b8845647afe25335 中的 speculation 目录。把该目录复制为候选副本后应用 [lazy-native.patch](lazy-native.patch)。将原版 src 加到 PYTHONPATH 并在已装 vLLM 0.32.0 的环境运行下列命令。

```sh
python benchmark_native_rows.py /path/to/original/src/recallspec/runtime.py /path/to/candidate/src/recallspec/runtime.py --output cpu-result.json --seed 232
```

[补丁](lazy-native.patch) · [初测证据](cpu-evidence.json) · [复测 232](cpu-s232.json) · [复测 233](cpu-s233.json) · [复测 234](cpu-s234.json)
