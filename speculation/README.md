# RecallSpec v2：带验证反馈的跨请求草稿检索

将单租户引擎中先前请求已生成的续写作为 speculative decoding 草稿，通过 vLLM 目标模型验证后接受。项目重点是缓存提交边界、请求生命周期、真实接受反馈、候选选择与开销归因，不是重新实现模型或算子。

阅读顺序：[实测结论](RESULTS.md) → [设计与不变量](docs/DESIGN.md) → `src/recallspec/core.py` → `src/recallspec/runtime.py` → 原始实验记录。

## 与旧版的实质区别

| 旧版 | v2 |
|---|---|
| sitecustomize 在进程启动时覆盖 proposer | 版本与源码 SHA-256 锁定的显式 worker 扩展点，可恢复原文件 |
| 用第一次 sampled 长度推断提示词边界 | 读取 worker 的真实 prompt boundary，只发布完整的已提交生成片段 |
| 本地有草稿便跳过共享索引 | 默认长上下文共享候选优先，未命中/暂停时回退原生；保留旧优先级消融 |
| 活跃批次缺席就清理游标 | 区分暂未调度与请求结束，由 finished 事件清理状态 |
| 以提出长度近似统计接受量 | 对齐本步实际调度的草稿前缀及验证输出，截短/未调度分别记账 |
| 固定容量原型 | LRU、按写入步 TTL、每键来源上限、单请求维护工作上限 |
| 主要强调高重复输出加速 | 单列冷/热历史、普通与冲突负载、门控与优先级消融、完整输出对照 |

接受反馈门控是预设启发式：每个候选两次验证的平均接受 token 数低于 2，暂停 32 个 proposer 步，之后重新探测。它不等价于已学习的净收益预测器，实际作用见报告。

## 代码入口

- `src/recallspec/core.py`：无 GPU 依赖的索引、提交游标与待验证反馈状态。
- `src/recallspec/runtime.py`：同 worker 的请求 ID、实际已调度草稿和 token buffer 关联。
- `patches/manifest.json`：原始/补丁源码散列、明确替换片段。
- `tools/patch_vllm.py`：检查、应用、恢复补丁。
- `tools/benchmark.py`：chat template、完整输入输出 token、首轮与后续轮、源码及环境记录。
- `tools/run_matrix.py`：顺序管理实验；无诊断基线恢复原始源码，失败不冒充完成。
- `tools/full_validation.py`：冻结源码后运行严格一致性、性能、机制、优先级消融、APC 和 7B 对照。
- `tools/analyze.py`：从原始输出与 JSONL 重新计算结果。

## 安装和复现

需要 NVIDIA GPU 的 Linux 环境；本项目验证范围为单卡 RTX 4090、Qwen2.5-3B/7B-Instruct BF16、vLLM 0.32.0。不要在其他实验使用同一环境时切换源码补丁。

```bash
python3 -m venv .venv
.venv/bin/python -m pip install '.[engine]'
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
.venv/bin/python tools/patch_vllm.py --check
.venv/bin/python tools/full_validation.py \
  --model /path/to/Qwen2.5-3B-Instruct \
  --model7b /path/to/Qwen2.5-7B-Instruct \
  --output results/reproduction
```

运行器为共享组自动安装补丁，为无诊断原生组恢复补丁，并在结束/异常时恢复 worker。若进程被强制终止，可显式恢复：

```bash
.venv/bin/python tools/patch_vllm.py --restore
```

已有结果可用任意 Python 3.11+ 重新分析，无需加载模型：

```bash
python tools/analyze.py results/final/performance
python tools/analyze.py results/final/strict
python tools/analyze.py results/final/diagnostics
```

## 边界

缓存是一个引擎内的 token 续写索引；不是 KV Cache、前缀缓存或草稿模型。目标模型验证是上游能力。这里只处理同步、单 GPU、无适配器的文本请求，不提供多租户服务能力；也不声称一般对话加速、在线 SLO 保证或 CUDA 算子开发成果。

离线批量生成耗时、严格输出对照和带诊断的机制测量分别报告。普通 BF16 的微小数值差异可能影响贪心输出；具体一致性结论以完整 token 对照为准，不能用“lossless”代替实测。

上游依据：[vLLM speculative decoding](https://docs.vllm.ai/en/latest/features/speculative_decoding/)、[0.32.0 CPU n-gram proposer](https://github.com/vllm-project/vllm/blob/v0.32.0/vllm/v1/spec_decode/ngram_proposer.py)、[0.32.0 GPUModelRunner](https://github.com/vllm-project/vllm/blob/v0.32.0/vllm/v1/worker/gpu_model_runner.py)。旧仓库与重写来源见 [ORIGIN.json](docs/ORIGIN.json)。本地交付不代表公开仓库已经更新。

补充与性能相同生成长度的严格验证（最终另行执行的第八阶段）：

```bash
.venv/bin/python tools/run_matrix.py \
  --model /path/to/Qwen2.5-3B-Instruct \
  --output results/reproduction/strict128 --seeds 77 --rounds 3 \
  --tokens 128 --modes base,native,gated --batch-invariant --trace
.venv/bin/python tools/analyze.py results/reproduction/strict128
```

`requirements.lock` 是测量时的安装环境快照，不是跨平台可直接求解的依赖锁；模型文件清单沿用同一实例上一项目已核验的 SHA-256 清单，见 `results/models/`，本包不包含模型权重。

完整交付检查（无需 GPU）：

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
python docs/verify_release.py
```

检查器核对八阶段、28次引擎运行、2619个请求的完整记录，校验运行时源码与测量指纹、真实输出长度、两组严格对照、缓存容量与排空状态；分析器的后处理修正单独列出散列，不篡改冻结时记录。
