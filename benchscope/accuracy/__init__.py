"""精度测试模块（Accuracy）：与性能模块彻底解耦的独立评测闭环。

子模块：
  - engines.py      精度引擎适配（bench 引擎注册表 eval 能力过滤 + 环境校验）
  - datasets.py     评测数据集（datasets.yaml 注册表 + 下载/标准化/抽样/统计）
  - executor.py     推理执行器（Serving/Native/Mock 统一接口；benchscope eval 实现体）
  - metrics.py      指标汇总（accuracy/pass_rate/分学科/Token 统计/结论）
  - estimator.py    Token 预估（常量表 > 实测统计 > 字符估算）
  - baselines.py    开源基线库与对标计算
  - task_manager.py EvalTaskManager（独立调度 + 三件套落库 + WS 推送）
  - compare.py      多任务对比 / Native vs Serving 一致性差值
  - scorers/        判分器（choice / math / code / judge）

设计文档：docs/rules/AccuracyEngine.md
"""
