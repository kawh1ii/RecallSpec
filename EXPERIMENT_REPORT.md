# RecallSpec 项目实验报告

**实验日期：**2026-10-07（原机实验与克隆机补充诊断）  
**项目：**基于 vLLM 0.11.0 的跨请求续写缓存与推测解码验证

## 1. 实验目标与方法

vLLM 原生 n-gram proposer 从当前请求的历史 token 中查找草稿。当不同请求具有相同的输出后缀、但单个请求自身没有足够的可复用历史时，原生 proposer 可能找不到有效草稿。RecallSpec 在原生 proposer 未提供草稿时，按当前请求末尾 12 或 8 个 token 检索其他请求此前**已生成**的续写，最多提出 8 个 token，随后仍由 vLLM 原有目标模型验证路径决定是否接受。

本项目要检验四个问题：跨请求草稿能否在目标负载中降低端到端延迟；加速是否伴随草稿接受与目标模型执行步数下降；新增 proposer 的 CPU 时间是多少；在普通请求中是否仍有收益与一致性问题。实现入口为 [`src/sitecustomize.py`](src/sitecustomize.py)，没有修改安装好的 vLLM 包。缓存最多包含 50,000 个键，每个键保留不超过两个来源请求的续写，并排除当前请求自身。

## 2. 实验环境与计量口径

| 项目 | 配置 |
|---|---|
| GPU / 系统 | NVIDIA RTX 4090（报告显存 24,564 MiB）；Ubuntu 22.04；CUDA 12.8；驱动 580.105.08 |
| 框架 | Python 3.12.3；PyTorch 2.8.0+cu128；vLLM 0.11.0；Transformers 4.57.1 |
| 模型 | Qwen2.5-3B-Instruct，BF16；`max_model_len=2048`；`gpu_memory_utilization=0.75`；`max_num_seqs=8` |
| 生成 | `temperature=0`；每请求固定生成 128 token（`min_tokens=max_tokens=128`，忽略 EOS） |
| 对照 | 无推测；原生 n-gram k=8；无推测加 Automatic Prefix Caching（APC）；RecallSpec |
| n-gram 参数 | `prompt_lookup_min=2`，`prompt_lookup_max=5`；原生与 RecallSpec 相同 |

每种模式在**独立进程**中运行。每组先预热一次，再记录各轮 `llm.generate` 的端到端 wall time，以测量轮次的**中位数**报告延迟。batch 1 测量 8 轮，batch 8 测量 5 轮；batch 8 的每轮是 8 个请求同时生成。加速比定义为“无推测中位延迟 / RecallSpec 中位延迟”。输出一致性按每个请求完整的生成 token ID 序列比较。诊断脚本会写 JSONL，影响计时，因此接受率、执行步数和 CPU 时间取自独立诊断运行，端到端加速比取自**无诊断运行**；两组数据不能合并视作同一次运行。

## 3. 高重复后缀负载：端到端结果

提示词前部的请求 ID 每轮变化，后部要求模型输出从 1 到 100 的逗号分隔整数。这是刻意构造的高重复、确定性负载，用于验证跨请求续写复用机制。

| batch | 无推测 | 原生 n-gram k=8 | 无推测 + APC | RecallSpec | 相对无推测加速 | 逐 token 一致 |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 1.0479 s | 1.1383 s | 1.0769 s | **0.1664 s** | **6.30×** | 8/8 |
| 8 | 1.2291 s | 1.3449 s | 1.2248 s | **0.2883 s** | **4.26×** | 40/40 |

这两组共 **48/48 个请求**与无推测基线逐 token 一致。APC 复用前缀；该负载的请求 ID 位于提示词前部，因此 APC 对这个重复**后缀**场景没有观察到明显收益。原生 n-gram k=8 也没有获得端到端加速。原机计时文件位于 [`results/`](results/)；运行 [`verify_results.py`](verify_results.py) 可重新计算中位数、加速比和逐 token 比对。

在克隆机上另做无诊断复测：batch 1 为 1.0471 → 0.1734 s（6.04×），batch 8 为 1.2259 → 0.3463 s（3.54×），两组仍为 48/48 逐 token 一致。不同机器的加速幅度有差异，尤其 batch 8；这里只把它作为同方向复测，不把原机的 6.30× / 4.26× 当作跨机器稳定值。复测原始文件位于 [`diagnostics/results/clean_replica/`](diagnostics/results/clean_replica/)。

## 4. 加速机制：草稿、验证步数与 CPU 时间

诊断在 `NgramProposer.propose` 记录草稿来源和 proposer CPU 调用时间，在 `Scheduler.update_from_output` 统计**实际被调度验证**的草稿、接受 token 与目标模型执行步数。按请求 ID 对齐，并排除初始化与预热。

| batch | 模式 | 跨请求已调度草稿 | 跨请求接受 / 提议 token | 原生草稿接受 / 提议 token | 目标模型执行步数 |
|---:|---|---:|---:|---:|---:|
| 1 | 原生 n-gram | — | — | 32/4416 | 992 |
| 1 | RecallSpec | 112 次、896 token | **896/896** | 0/128 | **136** |
| 8 | 原生 n-gram | — | — | 160/22360 | 625 |
| 8 | RecallSpec | 549 次、4392 token | **4392/4392** | 1/1160 | **124** |

在这个确定性高重复负载中，已调度的跨请求草稿全部被接受，平均每次验证接受 8 个 token。相较原生 n-gram，目标模型执行步数在 batch 1 从 992 降至 136，在 batch 8 从 625 降至 124。该机制数据与端到端加速方向一致；它本身不是严格的因果分解，也不表示所有场景都有 100% 接受率。

单独计时 RecallSpec 逻辑后，增量 Python CPU 时间中位数为 **0.103 ms/调用（batch 1）**、**0.493 ms/调用（batch 8）**；对应计时请求累计 12.23 ms 和 45.86 ms。它包含索引查找与维护，来自诊断运行，不是 GPU kernel 时间，也不能直接从无诊断端到端延迟中相减。原始 JSONL 与复算脚本见 [`diagnostics/REPORT.md`](diagnostics/REPORT.md) 和 [`diagnostics/analyze_spec_diag.py`](diagnostics/analyze_spec_diag.py)。

## 5. 普通请求负对照与正确性排查

在 8 个内容各异的普通请求中，batch 1 中位延迟为：无推测 1.0484 s，原生 n-gram 1.0024 s，RecallSpec 0.9924 s。这组样本没有可靠的通用端到端收益证据。诊断中跨请求草稿仅被调度 **1 次、8 token、接受 0**；因此不能将这个普通请求结果解读为跨请求缓存带来的加速。

沿用原基准条件时，原生 n-gram 和 RecallSpec 各有 **5/8** 个请求与无推测基线逐 token 一致。两种推测模式在部分请求的首次分歧位置相同，不能将差异直接归因于本项目的跨请求 proposer。单独请求 `logprobs=0` 后两者均为 8/8 一致；固定 seed 或移除预热并未单独消除原生 n-gram 的分歧。请求 top-5 logprobs 的两轮对照中三种模式为 16/16 一致，但具体数值机制仍未定位。**`logprobs=0` 只是诊断现象，不是修复方案。**相关结果和首次分歧分析见 [`diagnostics/REPORT.md`](diagnostics/REPORT.md)。

## 6. 结论与适用边界

RecallSpec 在实测的高重复后缀负载下实现了 6.30×（batch 1）和 4.26×（batch 8）的原机端到端加速，并观察到跨请求草稿被接受、目标模型执行步数下降和亚毫秒级的增量 proposer CPU 调用时间。独立克隆机复测仍有同方向收益，但幅度不同。普通请求没有可靠的通用收益，且输出对照中存在未完全解释的一致性差异。

当前实现只适用于单租户离线实验；没有租户隔离、敏感内容策略、TTL、持久化或收益控制。不能将本报告的高重复场景结果外推为一般对话平均收益，也不能在完成正确性调查前部署到多租户服务。

## 7. 复核入口

1. [`src/benchmark.py`](src/benchmark.py)：负载、模型配置、预热和端到端计时。
2. [`src/sitecustomize.py`](src/sitecustomize.py)：跨请求续写索引与 proposer 扩展。
3. [`verify_results.py`](verify_results.py)：从原始 JSON 复算中位数、加速比和输出一致性；在仓库根目录运行 `python3 verify_results.py`。
4. [`results/`](results/)：原机四类对照的原始计时与生成 token ID。
5. [`diagnostics/REPORT.md`](diagnostics/REPORT.md)：分来源接受率、执行步数、CPU 时间、克隆机复测和正确性消融的详细方法与数据位置。

完整 GPU 环境复现命令见 [`README.md`](README.md#复现)。原始计时和诊断文件均已随仓库提交；模型权重不包含在仓库中。
