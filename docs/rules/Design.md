# 设计规范 — Design

> **文档状态**：benchscope UI / 字体 / 颜色等设计规范  
> **关联**：[Software.md](./Software.md)（技术选型）· [Development.md](./Development.md)（开发规范）

---

## 1. 布局规范

| 项 | 规范 |
| --- | --- |
| 页面 | 浏览器全宽；内容区内部滚动（`height:100%` + `overflow:auto/hidden`） |
| 顶部导航 | 5 栏固定：Dashboard / Performance / Accuracy / Sessions / Settings（AntDV Menu） |
| 面板 | 统一 `a-card size="small"`，圆角 8–12px，卡片间距 12–20px |
| 页面内布局 | 仪表盘类：`a-row/a-col`（gutter 16–24）；三面板：grid / flex 等高 |
| 弹层 | 详情用 `a-modal`（宽 1100px）；侧边详情用 `a-drawer`（right，440px） |
| 表单 | 设置类标签 + 控件同行两端对齐（`section-row` / `panel-row`） |

## 2. 字体规范

| 用途 | 字号 / 字重 | 说明 |
| --- | --- | --- |
| 页面标题 / 面板标题 | 14px / 600 | 卡片 head 默认 |
| 正文 / 标签 | 12px | **与 Dashboard 面板一致**（页面面板统一 12px 内容文字） |
| 统计数字 | 26px / 700 | Overview 统计值，主色 |
| 表格 | 12px | 表头/表体一致；状态/操作列着色，其余列默认色 |
| 终端 / 命令 | 11–13px 等宽 | `SFMono / Consolas / Menlo` |
| 提示 / 次级 | 11–12px | `--ant-color-text-tertiary` |

## 3. 颜色规范

统一使用 antd 设计变量（`var(--ant-color-*)`），支持亮/暗/跟随系统主题：

| 用途 | 变量 / 值 |
| --- | --- |
| 主色（链接/激活/强调） | `--ant-color-primary`（默认 #1677ff） |
| 成功 / 在线 / Best 绿 | `--ant-color-success`（#52c41a） |
| 错误 / 离线 / 删除红 | `--ant-color-error`（#f5222d） |
| 警告 / 橙（stopped / 阈值） | #fa8c16 / #faad14 |
| 紫色（SGLang / bestModel） | #722ed1 |
| 文本 | `--ant-color-text`（#333）· `--ant-color-text-secondary`（#666）· `--ant-color-text-tertiary`（#999） |
| 边框 / 分隔 | `--ant-color-border`（#f0f0f0）· `--ant-color-border-secondary`（#d9d9d9） |
| 背景 | `--ant-color-bg-container`（#fff）· `--ant-color-bg-layout`（#fafafa）· `--ant-color-fill-secondary`（#f5f5f5） |
| 状态色 | running=蓝 processing、done=绿 success、stopped=橙 warning、error=红 error、pending=灰 default |

## 4. 表格规范（纯文本风格）

- 单元格**不使用按钮/边框/tag 包裹**；Run ID 不加粗。
- 仅**状态列与操作列**着色（详情蓝 / 删除红 / 状态按状态色），其余列统一默认文字色。
- 分组表格：每组前插入组标题行（`label#g{case_id}`）；Excel 导出组标题行加粗 + 浅蓝底色。
- Successful 百分比显示为整数（`98%`）。

## 5. 统计图规范（Statistics）

- 4 列 × 3 行 = 12 图：吞吐（Output/Peak/Total）、TTFT、TPOT、ITL（各 Mean/Median/P99）。
- 每列 8 色调色板；同一列同一 case 颜色一致，不同列颜色不同。
- x 轴：并发数（Requests 文字位于**轴末端、轴线上方**）；y 轴单位（tok/s / ms）。
- 图例：多于 1 个序列时显示（可滚动）；tooltip axis 触发、虚线 axisPointer。
- 多组相同条件：序列键 `label#g{case_id}` 独立成线。

## 6. 主题与国际化

- 亮 / 暗 / 跟随系统：`App.vue` 依据配置 `theme` 切换 antd 主题变量。
- 国际化：`web/src/i18n/{zh,en}.js`，全量双语键；`check-i18n` 保证 en/zh 键集合一致、无重复键。
- 英文默认；语言切换立即生效并持久化（`config.locale`）。
