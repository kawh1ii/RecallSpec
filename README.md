# RecallSpec：跨请求续写缓存与目标模型验证

## 项目定位

vLLM 0.11.0 自带的 n-gram speculative decoding 只在**当前请求**的历史 token 中寻找续写。本项目为它增加一个容量受限的跨请求索引：若本地没有草稿，则用当前请求末尾的 12 或 8 个 token 查找先前请求中已经生成过的后续 8 个 token，交给原有 speculative decoding 路径，由目标模型验证。这是一个**单租户离线原型**，不能直接部署到多租户服务。

缓存上限为 50,000 个键；每个键最多保留两个来源请求的续写，并排除当前请求自身。索引只记录提示词末尾到**已生成 token**的续写以及后续生成片段，不记录纯提示词到提示词的片段。启用方式为进程启动时设置 `SPEC_SHARED=1` 并加载 `src/sitecustomize.py`。实现没有改动安装好的 vLLM 文件。

## 为什么选择它

我先在同一台 GPU 上评估了融合 Gate/Up+SwiGLU 的 Triton kernel、静态 n-gram speculative decoding，以及基于接受率调节草稿长度。融合 kernel 在一个微基准上有 1.32×，但 24 层 MLP 只有约 1.03×，完整模型生成约 1% 且更大模型的目标形状反而变慢。自适应草稿在递增日志上比静态 8-token 草稿慢（0.742 秒对 0.568 秒）。因此选了能显示**系统级效果**、又有明确边界的跨请求续写复用方向。

## 实验配置

- 硬件：NVIDIA RTX 4090，实际报告显存 24,564 MiB；Ubuntu 22.04；CUDA 12.8，驱动 580.105.08。
- 软件：Python 3.12.3；PyTorch 2.8.0+cu128；vLLM 0.11.0；Transformers 4.57.1。
- 模型：Qwen2.5-3B-Instruct，BF16；`max_model_len=2048`，`gpu_memory_utilization=0.75`，`max_num_seqs=8`。
- 解码：temperature 0，强制生成 128 token；一次预热不计时；之后按表中轮数测量 `llm.generate` 端到端耗时中位数。每轮使用不同请求 ID。batch 8 的 128 token × 8 请求为一次批量调用。
- 基线：无推测解码；vLLM 自带 n-gram 静态 k=8；无推测解码加 Automatic Prefix Caching（APC）。静态与共享模式的 n-gram 配置均为 `prompt_lookup_min=2`、`prompt_lookup_max=5`。

### 结果：可复用后缀的目标工作负载

提示词前部的请求 ID 变化，后部指令都要求输出 1 到 100 的逗号分隔整数。这个任务是**刻意构造的高重复、确定性场景**。

| batch | 测量轮数 | 无推测 | 自带 n-gram k=8 | 无推测 + APC | RecallSpec | 相对无推测 | RecallSpec 与无推测逐 token 一致 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 8；APC 5 | 1.0479 s | 1.1383 s | 1.0769 s | **0.1664 s** | **6.30×** | 8/8 |
| 8 | 5 | 1.2291 s | 1.3449 s | 1.2248 s | **0.2883 s** | **4.26×** | 40/40 |

APC 复用的是前缀；本工作负载变更了前部 ID，后缀与输出相同，所以 APC 在这些实测中未显著改变耗时。共享缓存的 8-token 草稿经目标模型验证。独立诊断对计时请求累计统计，跨请求草稿 accepted / proposed token 数为 **896/896（batch 1）** 和 **4392/4392（batch 8）**；相对于原生 n-gram，目标模型执行步数分别由 **992 降至 136**、**625 降至 124**。诊断数据、CPU 开销和独立无诊断复测见 [diagnostics/REPORT.md](diagnostics/REPORT.md)。

### 负对照：不同内容的普通请求

8 个相互不同的问题、每轮不同 case ID，batch 1：无推测 1.0484 s；自带 n-gram k=8 为 1.0024 s；RecallSpec 为 0.9924 s。这里没有可靠的系统级加速证据。RecallSpec 与无推测逐 token 一致 **5/8**；自带 n-gram 也是 **5/8**。另有一个共享模式与静态模式的差异，原因尚未定位。虽然目标模型验证了草稿，**不能把验证机制等同于整个推理栈逐 token 必然一致**。该原型需要进一步调查批处理数值路径及输出差异后才能考虑生产环境。

## 复现

在有 NVIDIA GPU 的 Linux 环境中安装与上述版本相同的软件及 Qwen2.5-3B-Instruct 模型。将下方 `MODEL` 改为实际模型目录，`PROJECT` 改为本项目目录。`SPEC_SHARED` 与 `PYTHONPATH` 必须在启动 Python 前设置，以便 vLLM worker 也加载补丁。

```bash
PROJECT=/path/to/RecallSpec
MODEL=/path/to/Qwen2.5-3B-Instruct
cd "$PROJECT/results"
python "$PROJECT/src/benchmark.py" --mode base --workload shared_tail --batch 1 --rounds 8 --model "$MODEL"
python "$PROJECT/src/benchmark.py" --mode static8 --workload shared_tail --batch 1 --rounds 8 --model "$MODEL"
SPEC_SHARED=1 PYTHONPATH="$PROJECT/src" python "$PROJECT/src/benchmark.py" --mode shared8 --workload shared_tail --batch 1 --rounds 8 --model "$MODEL"
python "$PROJECT/src/benchmark.py" --mode base --workload shared_tail --batch 1 --rounds 5 --model "$MODEL" --prefix-cache
python "$PROJECT/verify_results.py"
```

将 `--batch` 改为 8、`--rounds` 改为 5 可以跑批量对照；`--workload unique_general --batch 1 --rounds 8` 可以跑负对照。每个模式启动独立进程，以免跨模式共享状态；默认 vLLM 多进程引擎配置。原始 JSON 保存了每轮时间和完整输出 token ID；`verify_results.py` 重新计算中位数、加速比与逐 token 比对。文件名中的模型目录名应为 `model3b` 才能直接运行附带的验证脚本；其他目录名需相应调整该脚本的文件名模板。

## 局限与下一步

1. 这些加速数字只适用于实测的高重复任务；不能外推为一般对话的平均收益。更真实的多请求轨迹、不同负载和并发数仍需测量。
2. 当前索引仅按 token 序列查找，没有租户隔离、敏感内容策略、持久化、TTL 或命中收益控制。不得在共享用户服务中直接开启。
3. 普通请求的输出一致性尚未完全通过；应先定位差异、再增加回归测试，之后才能谈部署。
4. Nsight Systems 可运行；云端对 Nsight Compute GPU 硬件计数器返回 `ERR_NVGPUCTRPERM`，所以没有可靠的硬件计数器数据。若需深入 kernel 分析，需机器提供计数器访问权限。

## 补充诊断

已在克隆机上完成分来源的已调度草稿、实际接受 token、目标模型执行步数及 proposer 增量 CPU 时间测量，并复查普通请求输出差异。高重复场景下跨请求草稿接受率为 100%，普通请求仅有一次跨请求草稿验证且被拒绝；旧基准的 5/8 差异可复现，但请求 logprobs 后变为一致，具体数值机制尚未定位。原始数据、两机无诊断复测与限制见 [diagnostics/REPORT.md](diagnostics/REPORT.md)。

相关上游资料：[vLLM 0.11.0 NgramProposer](https://docs.vllm.ai/en/v0.11.0/api/vllm/v1/spec_decode/ngram_proposer.html)、[vLLM 0.11.0 benchmark 说明](https://docs.vllm.ai/en/v0.11.0/contributing/benchmarks.html)。
