
# 概述

benchscope 是测试工具，实现以下功能

**webclient 基本功能定义**

1）启动时，配置 vLLM 或 SGlang 等兼容opanai 接口的 API接口，进行配置；
2）测试支持配置 vLLM bench 和 sglang bench 相关参数，请搜索相关参数，并可选择指定相关配置项;
3) 测试数据集支持 random 和 sharegpt ，sharegpt 数据集支持自动下载（https://www.modelscope.cn/datasets/gliang1001/ShareGPT_V3_unfiltered_cleaned_split）；
4）测试模型，以API获取的 models为准，若有多个，提供可选项；
5) 启动后，若vLLM和sglang推理服务还未启动，等待其启动后变更状态，测试中若推理服务断开，变更状态；若webclent掉线，显示自身状态；
6）主导航分为2大类 vLLM 和 Sglang ，每大类按照random、sharegpt数据集和自定义数据集三小类，自定义数据集功能和sharegpt保持一致
7）打开网站有几个状态：网站服务状态 就绪/离线，推理服务状态 就绪/离线；
8）UI界面，
1，整个页面浏览器全宽；
2，顶部导航，分为左侧为  vLLM/Sglang/日志分析， 右侧为 推理服务状态和服务设置；
3，每个测试页面，从上往下3个面板，依次是测试配置、实时结果、日志分析；
4，测试配置，增加 TPOT阈值，测试记录表格高亮接近此阈值的行；
5，实时结果，表格 标题显示全 中英双语，曲线为6项，分别为 output 吞吐,total吞吐，TTFT mean 耗时、TPOT mean耗时 、 TTFT P99 耗时和 TPOT P99 耗时；
6，日志分析，右侧为日志管理全部列表，选择列表项，左侧显示日志项面板为：测试日志表格，Outpu吞吐,Total吞吐，TTFT mean 耗时、TPOT mean耗时 、 TTFT P99 耗时和 TPOT P99 耗时；


**webclient 测试功能定义**


1）测试脚本见 `asserts/test-non.py` 内容，脚本生成的是 ttft/itl/tpot是 平均的。再保存一份P99的；
2）若是 random 数据集，可添加多个输入/输出长度，默认支持 3K/1K，1K/1K，256/256 ，默认都选中，可取消某个，可自定义条件；
3）若是 sharegpt 数据集，无需指定输入/输出长度；
4）测试请求数分均可自定义，默认支持 1,4,8,16,32,40,64,128 ，可编辑，可添加，可删除；
5）模型部署使用的GPU数量看是否可以自动获取，不可以给选择和编辑框；
6）测试并发数默认 --max-concurrency 和 --num-prompts 均保持一致，给出 inf 选项，可选择 inf ；
7) vLLM 和  sglang 其他参数可自由度添加；

**webclient 日志功能定义**

1）日志保存见 'asserts/logs'文件夹下，日志保持到执行目录，提供预览和下载功能，提供日志记录为月日-时分秒为一次日志目录名；
2）日志汇总每一次日志记录提供日志汇总功能，生成如`asserts/benchmark-260821.xlsx` 文件内容，列项说明
  - 模型： 模型名称，自动填上
  - 精度： 测试的模型数据精度，可不填；
  - GPU： GPU型号和数量，可不填；
  - 推理框架：自动填上，vLLM或SGlang，
  - 输入长度，输出长度：根据测试日志整理
  - 并发数：根据测试日志整理；
  - output/peakoutput/total/ttft/itl/tpot，根据测试日志整理，但顺序依次不变；
  - 单用户： 1000/tpot 自动计算
3）日志汇总2个面板，一个基于 ttft/itl/tpot 平均的，一个基于ttft/itl/tpot P99的；

**webclient 分析功能定义**

1）实时更新：每个并发结果出来列到表格中，绘制output/peakoutput/total/ttft/itl/tpot曲线，横轴并发数，纵轴相应的数据；
2）分析面板分2大块，一个基于 ttft/itl/tpot 平均的，一个基于ttft/itl/tpot P99的；
3）表格可自定义最佳并发， 指定TPOT毫秒参数，如指定tpot=100ms，若测试记录表格中出现最接近 <100ms的记录则为最佳记录，此行颜色高亮；

 
**技术方案**

benchscope 是测试工具，是一个类似于tensorflow-dashborad的工具，pip安装后，连上 vLLM服务或sglang服务或 兼容 openai的API服务就可以进行性能测试；

整体web界面，希望使用vue前端技术+ant desgin UI设计组件实现，但要执行 vllm bench 和 sglang bench ，是否需要在其环境安装服务插件？

**规划**

1，是否有更好的技术方案，给出技术选项方案
2，目前规划性能测试： V1, 纯文本性能测试，V2 多模态模型测试,V3全模态模型性能测试；V4 世界模型性能测试；
3，另外规划精度测试： V5 常见数据集的精度测试 , V6 并且给出modelscope 官方模型链接，可分析出对比结论；
4, 本地调试测试 vLLM openai 服务为: http://192.168.1.67:8000 

**版本路线**

v1.0.0（已发布，纯文本性能测试：双框架、三数据集、实时结果、日志与 xlsx 汇总、分析、管理台 UI）。
版本规划与迭代记录见 [VERSION_README.md](VERSION_README.md)：v2.0 多模态 / v3.0 全模态 / v4.0 世界模型 / v5.0 精度测试 / v6.0 ModelScope 模型对比 / v7.0 内置 GPU 适配模型下载。