# RecallSpec：跨请求草稿检索与验证反馈

在 vLLM worker 中提交已确认的 token 续写、检索跨请求草稿，并按实际调度量收集验证反馈。单卡高重复续写、热缓存、batch 1 的限定场景延迟由 1.088 s 降至 0.160 s；普通问答的回退与数值差异另列。

- [实现与复现步骤](speculation/README.md)
- [实验结果和适用边界](speculation/RESULTS.md)
- [设计与实现细节](speculation/docs/DESIGN.md)
- [源码](speculation/src) · [测试](speculation/tests) · [原始实验记录](speculation/results)

当前实现及其测量证据在 `speculation/`。旧实现与实验仍可从[此前的项目说明](README.previous.md)查看。
