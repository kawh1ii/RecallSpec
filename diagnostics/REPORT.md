# RecallSpec 补充诊断（2026-10-07）

## 范围与设置

在原实验环境的克隆机上运行：RTX 4090（24,564 MiB）、PyTorch 2.8.0+cu128、vLLM 0.11.0、Qwen2.5-3B-Instruct BF16。无推测、原生 n-gram k=8、RecallSpec 使用相同模型与生成参数；除专门标出的 logprobs 消融外，普通请求比较沿用原基准的 variant 0 预热、variant 1--8 计时顺序及默认 SamplingParams。

诊断脚本在 vLLM 0.11.0 的 `NgramProposer.propose` 记录草稿来源与 CPU 调用时间，并在 `Scheduler.update_from_output` 记录**实际被调度验证**的草稿、接受 token 数及目标模型执行步数。按请求 ID 对齐两处记录；以下表格只统计计时请求，排除初始化和预热。所有诊断文件均为 JSONL，`analyze_spec_diag.py` 可复算。诊断写盘影响端到端耗时，故加速比采用单独无诊断运行。

## 高重复续写负载：机制计数

| batch | 模式 | 跨请求已调度草稿 | 跨请求接受 token | 原生草稿接受 token | 目标模型执行步数 | proposer CPU 调用中位数 |
|---:|---|---:|---:|---:|---:|---:|
| 1 | 原生 n-gram | — | — | 32 / 4416（0.72%） | 992 | 0.082 ms |
| 1 | RecallSpec | 112 次、896 token | **896 / 896（100%）** | 0 / 128 | **136** | 0.178 ms |
| 8 | 原生 n-gram | — | — | 160 / 22360（0.72%） | 625 | 0.122 ms |
| 8 | RecallSpec | 549 次、4392 token | **4392 / 4392（100%）** | 1 / 1160 | **124** | 0.601 ms |

batch 1 每种模式统计 8 个计时请求，batch 8 统计 5 批、共 40 个计时请求。跨请求草稿的平均每次验证接受数在这组刻意构造的重复负载中均为 **8.0**。目标模型执行步数 batch 1 减少 7.29 倍，batch 8 减少 5.04 倍；这与端到端加速方向一致。proposer 数字是诊断中**整个 Python proposer 方法的 CPU 调用时间**，包含原生查找与 RecallSpec 逻辑，不是额外开销或端到端延迟的可加项；不同模式执行步数、请求数和缓存状态也不同，不能简单相减得出净开销。

进一步在 RecallSpec 内部单独计时原生 n-gram 调用，以整个 proposer 时间减去它，得到本补丁的**增量 Python CPU 时间**：batch 1 每次调用中位数 **0.103 ms**、8 个计时请求累计 **12.23 ms**；batch 8 每次调用中位数 **0.493 ms**、40 个计时请求累计 **45.86 ms**。这个数包含索引查找和维护，是诊断运行中的计时；它不是独立的 GPU kernel 时间，也不能直接从端到端延迟里相减。

### 无诊断复测

| 机器/运行 | batch 1 基线 → RecallSpec | batch 8 基线 → RecallSpec | 逐 token 一致 |
|---|---:|---:|---:|
| 原机先前实验 | 1.0479 → 0.1664 s（6.30×） | 1.2291 → 0.2883 s（4.26×） | 48/48 |
| 克隆机本次复测 | 1.0471 → 0.1734 s（6.04×） | 1.2259 → 0.3463 s（3.54×） | 48/48 |

这些数字只对应固定的整数序列输出任务；两台同型号 GPU 的批量结果也有幅度差异，不能外推到一般对话。

## 普通请求与正确性排查

- 在 8 个不同内容的普通请求中，原生 n-gram 已调度草稿 767 token、接受 157（20.5%）；RecallSpec 的跨请求草稿仅出现 **1 次、8 token、接受 0**。该次请求属于 variant 8。跨请求续写在这组请求中没有提供可观测的加速机制。
- 按原基准条件复跑，无推测与原生 n-gram、RecallSpec 的逐 token 一致数仍各为 **5/8**。原生与 RecallSpec 在 variant 3、7 的首次分歧位置同为 31、70；variant 8 分别从位置 70、71 起与基线不同。与最初实验记录相同。
- 单独请求 `logprobs=0` 后，原生和 RecallSpec 均变为 **8/8 一致**；固定 seed 或去掉预热并未单独消除原生 n-gram 的 3 个分歧。请求 top-5 logprobs 的两轮对照中，三种模式 **16/16 一致**。variant 3 和 7 的原首次分歧位置，在 logprobs 路径的 top-2 候选概率恰好打平；variant 8 的机制仍未定位。

**结论边界：** 当前数据定位到“是否请求 logprobs”会改变这些普通请求的输出对照结果，但不能证明具体是哪个 kernel、浮点舍入还是请求调度造成。原生 n-gram 在相同位置也分歧，不能把 5/8 直接归因于跨请求缓存；variant 8 的跨请求草稿虽被拒绝，仍需继续调查。不要把 `logprobs=0` 当作修复方案。vLLM 的[推测解码文档](https://docs.vllm.ai/en/v0.11.0/features/spec_decode.html)也明确区分算法层面的 lossless 保证与实际数值路径的输出稳定性。

## 复核入口

- `results/clean_replica/`：克隆机无诊断计时和完整输出 token。
- `results/legacy_repro/`：按旧基准条件的普通请求三模式复测。
- `results/correct_*.json`、`results/correct_nolog_*.json`、`results/ablate_*.json`：固定 seed、logprobs、预热条件消融的完整 token 输出；top-5 文件含候选 logprobs。
- `results/traces/diag_steps_*`：高重复负载最终分来源草稿与目标模型执行步数 JSONL。
- `results/traces/diag_extra_*`：RecallSpec 增量 Python CPU 时间分解 JSONL。
- `results/traces/diag_*general1`：普通请求分来源草稿 JSONL。
- `analyze_spec_diag.py`：从 JSONL 复算接受率、目标执行步数及 proposer CPU 时间；batch 1 传 `--min-request-id 1`，batch 8 传 `--min-request-id 8` 以排除预热。

原始诊断文件按请求 ID 保存 token 序列，不包含 SSH 凭据。该缓存仍没有租户隔离，不能直接用于多租户服务。

在相同 vLLM 0.11.0 环境中复跑一次 batch 1 分来源诊断（诊断写盘会影响耗时）：

```bash
PROJECT=/path/to/RecallSpec
MODEL=/path/to/Qwen2.5-3B-Instruct
mkdir -p "$PROJECT/diagnostics/results/new_shared_b1"
cd "$PROJECT/diagnostics/results"
SPEC_SHARED=1 SPEC_DIAG_DIR="$PROJECT/diagnostics/results/new_shared_b1" \
  PYTHONPATH="$PROJECT/diagnostics" python "$PROJECT/src/benchmark.py" \
  --mode shared8 --workload shared_tail --batch 1 --rounds 8 --model "$MODEL"
python "$PROJECT/diagnostics/analyze_spec_diag.py" \
  "$PROJECT/diagnostics/results/new_shared_b1" --min-request-id 1
```
