# 设计规范 — Design

> **文档状态**：benchscope UI / 字体 / 颜色等设计规范；**对齐 Ant Design 设计语言**（ant.design）
> **关联**：[Software.md](./Software.md)（技术选型）· [Development.md](./Development.md)（开发规范）· [TopBar.md](../prds/TopBar.md)（主导航全局参数与变更记录）

---

## 0. Ant Design 设计规范基准（ant.design/design.md）

> 本项目 UI 以 **Ant Design 设计语言**为基准（antd 5.x，`https://ant.design/` 设计规范，Vue 实现 `ant-design-vue`）。
> 所有页面 / 组件遵循 antd 的**设计价值观、设计令牌（Design Token）与设计基础**，保证视觉一致性与可维护性。

### 0.1 设计价值观（四大）

| 价值观 | 含义 | 本项目落地 |
| --- | --- | --- |
| **自然（Natural）** | 交互符合人类直觉与习惯，界面秩序、克制 | 布局遵循 8px 网格与栅格；减少装饰，内容优先 |
| **确定性（Certainty）** | 明确、一致、可预期的行为与反馈 | 统一使用 antd 组件语义；状态/操作有明确视觉反馈；按钮、标签、Tag 语义一致 |
| **意义感（Meaningful）** | 界面服务内容，而非装饰；信息层次清晰 | 主次信息用字号/字重/颜色区分；关键操作醒目、次要弱化 |
| **生长性（Growth）** | 模块化、可复用、可演进 | 抽取通用组件（StatusBadge/MetricsTable/Panel 等）；设计令牌驱动主题 |

### 0.2 设计令牌（Design Token）

- 统一使用 **antd 设计令牌**（`var(--ant-color-*)` / `--ant-color-*`），**禁止硬编码色值/字号/间距**。
- 主题：亮 / 暗 / 跟随系统由 `App.vue` 依据配置切换，令牌自动跟随。
- 需新增令牌值时，用 antd 语义色系派生，避免引入游离值。

### 0.3 设计基础（Design Basics）

| 基础 | 规范（antd） |
| --- | --- |
| **色彩** | 功能色：primary / success / warning / error / info；中性色：text / border / bg 分层；状态色与语义强绑定 |
| **字体** | 默认字体栈；数字/统计用等宽增强可读性；标题/正文/次级三层字重 |
| **间距（8px 网格）** | 页面/卡片内间距取 8px 倍数（8 / 12 / 16 / 24）；卡片间距 12–24px |
| **栅格（24 列）** | 仪表盘/表单用 `a-row/a-col`，`span` 基于 24 栅格；`gutter` 16–24 |
| **圆角** | 面板/卡片 8px（小）· 弹窗 8px · 按钮/输入框按组件默认 |
| **阴影** | 面板/弹层用 antd 阴影令牌（hover 上浮、drawer/modal 默认阴影） |
| **图标** | 统一 `@ant-design/icons-vue`；图标语义明确、尺寸规范（16/24/48 层级） |
| **动效** | 交互反馈用 antd 默认动效（过渡 0.2s 左右）；不引入无意义动画 |
| **无障碍** | 文本对比度达标（antd 色板）；可点击元素有 hover/焦点态；`aria`/`title` 补充 |

---

## 1. 布局规范

| 项 | 规范 |
| --- | --- |
| 页面 | 浏览器全宽；内容区内部滚动（`height:100%` + `overflow:auto/hidden`） |
| 顶部导航 | 6 栏固定：Dashboard / Performance / Accuracy / Sessions / Datas / Settings（AntDV Menu）；左侧品牌区 Logo（`blue_logo.png`，48×48 圆角）+ BenchScope + 版本标签；右侧 Service 状态仅显示状态颜色图标（`StatusBadge no-label`，在线绿 / 离线红，无文字，hover tooltip 显示详情） |
| 面板 | 统一 `a-card size="small"`，圆角 8–12px，卡片间距 12–20px |
| 页面内布局 | 仪表盘类：`a-row/a-col`（gutter 16–24）；三面板：grid / flex 等高 |
| 弹层 | 详情用 `a-modal`（宽 1100px）；侧边详情用 `a-drawer`（right，440px） |
| 表单 | 设置类标签 + 控件同行两端对齐（`section-row` / `panel-row`） |
| **间距（对齐 antd 8px 网格）** | 卡片内边距 / 元素间距取 8px 倍数（8/12/16/24）；紧凑面板用 8–12px，宽松用 16–24px |
| **栅格（对齐 antd 24 栅格）** | `a-row` 默认 `gutter=16/24`；`a-col` 按 24 分割（如 24/12/8/6/4） |

---

## 2. 字体规范（对齐 antd 字体系统）

| 用途 | 字号 / 字重 | 说明 |
| --- | --- | --- |
| 页面标题 / 面板标题 | 14px / 600 | 卡片 head 默认 |
| 正文 / 标签 | 12px | **与 Dashboard 面板一致**（页面面板统一 12px 内容文字） |
| 统计数字 | 26px / 700 | Overview 统计值，主色；数字用等宽增强可读性 |
| 表格 | 12px | 表头/表体一致；状态/操作列着色，其余列默认色 |
| 终端 / 命令 | 11–13px 等宽 | `SFMono / Consolas / Menlo` |
| 提示 / 次级 | 11–12px | `--ant-color-text-tertiary` |
| **字体栈（antd）** | 默认 | 遵循 antd 默认字体栈（系统字体 + 中文字体回退）；代码/数字用等宽（`font-variant-numeric: tabular-nums`） |

---

## 3. 颜色规范（对齐 antd 色彩系统）

统一使用 antd 设计令牌（`var(--ant-color-*)`），支持亮/暗/跟随系统主题：

| 用途 | 变量 / 值 |
| --- | --- |
| 主色（链接/激活/强调） | `--ant-color-primary`（默认 #1677ff） |
| 成功 / 在线 / Best 绿 | `--ant-color-success`（#52c41a） |
| 错误 / 离线 / 删除红 | `--ant-color-error`（#f5222d） |
| 警告 / 橙（stopped / 阈值） | #fa8c16 / #faad14 |
| 紫色（SGLang / bestModel） | #722ed1 |
| 信息蓝（Serving / info） | `--ant-color-info` |
| 文本 | `--ant-color-text`（#333）· `--ant-color-text-secondary`（#666）· `--ant-color-text-tertiary`（#999） |
| 边框 / 分隔 | `--ant-color-border`（#f0f0f0）· `--ant-color-border-secondary`（#d9d9d9） |
| 背景 | `--ant-color-bg-container`（#fff）· `--ant-color-bg-layout`（#fafafa）· `--ant-color-fill-secondary`（#f5f5f5） |
| 状态色 | running=蓝 processing、done=绿 success、stopped=橙 warning、error=红 error、pending=灰 default |
| **色阶派生** | 需深浅变体时用 antd 色板（`-1/-2/-3` 或 `hover/active` 派生），避免硬编码 |

---

## 4. 表格规范（纯文本风格）

- 单元格**不使用按钮/边框/tag 包裹**；Run ID 不加粗。
- 仅**状态列与操作列**着色（详情蓝 / 删除红 / 状态按状态色），其余列统一默认文字色。
- 分组表格：每组前插入组标题行（`label#g{case_id}`）；Excel 导出组标题行加粗 + 浅蓝底色。
- Successful 百分比显示为整数（`98%`）。

---

## 5. 统计图规范（Statistics）

- 4 列 × 3 行 = 12 图：吞吐（Output/Peak/Total）、TTFT、TPOT、ITL（各 Mean/Median/P99）。
- 每列 8 色调色板；同一列同一 case 颜色一致，不同列颜色不同。
- x 轴：并发数（Requests 文字位于**轴末端、轴线上方**）；y 轴单位（tok/s / ms）。
- **图例（位于 Y 轴右侧、曲线图内，竖排对齐）**：多于 1 个序列时显示——
  - `orient: vertical` **竖排**，`left: 48, top: 12`（紧贴 Y 轴刻度右侧、曲线图内）；`type: scroll`、`align: left`
  - 颜色标记缩小：`itemWidth/Height: 8`、`itemGap: 5`、`icon: circle`
  - 文字缩小：`textStyle.fontSize: 9`
  - **透明度 60%**：`itemStyle.opacity: 0.6` + `textStyle.opacity: 0.6`
- tooltip axis 触发、虚线 axisPointer。
- 多组相同条件：序列键 `label#g{case_id}` 独立成线。

## 5.5 表格列控制（MetricsTable）

- 列定义集中在 `ALL_COLUMNS`（key + title + 组 + 默认可见 + fixed）。
- **`defaultHidden` prop**：指定默认隐藏的列键（仍可在列控制下拉中开启）；隐藏后自动将首个可见任务列固定左侧（如 Datas Perf Datas 隐藏 Case 后 Requests 固定）。
- 预设 `preset`（default / mean / median / p99）重置列选择，同样受 `defaultHidden` 过滤。
- 列控制下拉按组展示（task / throughput / ttft / tpot / itl），勾选切换可见。

---

## 6. 主题与国际化

- 亮 / 暗 / 跟随系统：`App.vue` 依据配置 `theme` 切换 antd 主题令牌（`var(--ant-color-*)`）。
- 国际化：`web/src/i18n/{zh,en}.js`，全量双语键；`check-i18n` 保证 en/zh 键集合一致、无重复键。
- 英文默认；语言切换立即生效并持久化（`config.locale`）。

---

## 7. 遵循检查清单（对齐 antd）

- [ ] 未硬编码颜色 / 字号 / 间距（一律用 `var(--ant-*)` 令牌）
- [ ] 间距符合 8px 网格；栅格按 24 列布局
- [ ] 组件用 antd 语义（按钮 primary/danger、Tag 状态色、Badge status）
- [ ] 图标来自 `@ant-design/icons-vue`，语义明确
- [ ] 弹窗/抽屉/阴影/动效用 antd 默认令牌
- [ ] 中英文案同步（i18n 双语）
