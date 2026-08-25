# 1.0.5 验收检查清单

## P0 阻断性缺陷
- [x] 跑一次任务(可用 `BENCHSCOPE_FAKE_BENCH=1`),`logs/<run_id>/run.json` 存在且字段完整(framework_name/model/status/started_at/finished_at/rows/metrics)
- [x] Dashboard 表格中该任务行的 meta(model/framework/status/started_at)非空
- [x] Dashboard 统计卡片 `avg_tpot` / `best_model` 计入该任务 rows
- [x] Logs 视图(`/dashboard` 详情 Modal)能正确加载该 run 的指标与文件
- [x] zh.js / en.js 中 18 个重复键各仅出现一次
- [x] i18n 切换 zh/en,涉及的控件文案(模型选择/并发/框架/精度等)显示正确无回退到 key 名

## P1 未完成功能
- [x] TaskDetailView 任务 running 时,当前执行的 case/并发标签显示 processing 色;已完成 green、未开始 default
- [x] SessionsView 装饰控件(上传/搜索/质量)已接线或已移除(默认移除)
- [x] SessionsView 会话列表有「清空全部」按钮,点击带确认,调用 `DELETE /api/sessions` 后列表清空
- [x] SettingsView 无硬编码英文(列标题、提示语均走 i18n)
- [x] 模型管理库方案已确认:要么 `models.json` CRUD 可用,要么计划文档已更新注明推迟

## P2 清理与文档
- [x] `web/src/views/TestView.vue` 与 `LogView.vue` 已删除或归档,grep 无 import 残留
- [x] legacy 组件(EnvPanel/TestConfigPanel/TestProgressPanel/SubTabBar/RunRecordList/RunSummaryBlock)无引用残留
- [x] README.md / README.zh-CN.md 反映五栏导航与任务化流程
- [x] ROADMAP.md 含 1.0.4 / 1.0.5 行,注明 Accuracy 占位(v5.0)与 Plugins 占位
- [x] docs/PRD.md 版本号 = v1.0.5,导航与 API 清单已同步
- [x] `npm run build` 成功;`python -m build` + `twine check` 通过
