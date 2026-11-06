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

全命中消除了重复原生工作。零命中还有掩码构造成本，其他组的总耗时方向不一致。上表只量 CPU proposer，目标模型验证见独立 GPU 对照。

## 复现

使用 RecallSpec 仓库提交 8b8f7c10ff8b2616f72aedc5b8845647afe25335 中的 speculation 目录。把该目录复制为候选副本后应用 [lazy-native.patch](lazy-native.patch)。将原版 src 加到 PYTHONPATH 并在已装 vLLM 0.32.0 的环境运行下列命令。

```sh
python benchmark_native_rows.py /path/to/original/src/recallspec/runtime.py /path/to/candidate/src/recallspec/runtime.py --output cpu-result.json --seed 232
```

[补丁](lazy-native.patch) · [初测证据](cpu-evidence.json) · [复测 232](cpu-s232.json) · [复测 233](cpu-s233.json) · [复测 234](cpu-s234.json)

## RTX 4090 严格对照

在 RTX 4090、vLLM 0.32.0、PyTorch 2.13.0+cu130、Qwen2.5-3B-Instruct BF16 上运行。三种子各比较 81 条输出，两版的 243 条完整 token ID 序列逐条相同。每组结束后 live cursor 和 pending 均归零，索引峰值未超过 50,000 个键。原版和按需版均执行同样次数的 proposer 路径，其中按需版全批短路累计 292 次。该计数覆盖完整 trace，包含每轮启动时的独立预热。

| 种子 | 完整输出 ID 一致数 | 原版原生调用 | 按需版原生调用 |
| ---: | ---: | ---: | ---: |
| 244 | 81/81 | 1737 | 1650 |
| 245 | 81/81 | 1658 | 1560 |
| 246 | 81/81 | 1569 | 1462 |
| 合计 | 243/243 | 4964 | 4672 |

- [环境与模型散列](gpu-cu130-environment.json)
- [逐请求输出、草稿反馈与索引 trace](recall-gpu-strict/)
- [独立复算](gpu-strict-audit.json)

## 常规生成耗时

相同种子和输入在常规配置下的完整 token ID 也逐条一致，共 243/243。以下为后两轮生成耗时的种子内中位数，再取三种子中位数。

| 负载 | 批大小 | 原版，ms | 按需版，ms |
| --- | ---: | ---: | ---: |
| 重复 | 1 | 168.1 | 165.9 |
| 重复 | 8 | 222.1 | 224.9 |
| 通用 | 1 | 1296.9 | 1295.2 |
| 通用 | 8 | 1389.0 | 1400.9 |
| 冲突 | 1 | 633.1 | 627.9 |
| 冲突 | 8 | 718.6 | 707.3 |

生成耗时变化为约 −1.6% 至 +1.3%，方向随负载而变。重复批 8 和通用批 8 出现小幅回退。这次改动的直接收益是省掉被覆盖的原生提议，并保持已验证负载的输出一致。

- [逐请求输出和分轮耗时](recall-gpu-timing/)
- [独立复算](gpu-timing-audit.json)

## GPU 复现

沿用上述原版和候选副本，使用独立 venv 与同一份 Qwen2.5-3B-Instruct 权重。严格组启用 eager、batch-invariant 和 trace，常规计时组关闭这三项。两组固定 vLLM V1 GPUModelRunner、贪心解码与 128 个输出 token。每个种子覆盖重复、通用和冲突三类提示，批大小为 1、8，每个组合执行三轮。常规计时仅统计第 2、3 轮的 CUDA 同步生成耗时，分别取种子内与种子间中位数。

```sh
model=/path/to/Qwen2.5-3B-Instruct
python gpu_compare.py --baseline baseline --candidate candidate --model "$model" --output strict --seeds 244 245 246 --strict
python gpu_compare.py --baseline baseline --candidate candidate --model "$model" --output timing --seeds 244 245 246
```
