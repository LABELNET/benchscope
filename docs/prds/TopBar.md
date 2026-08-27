# TopBar 主导航 — 全局参数与变更记录

> **版本**：v1.0.6（开发中）
> **最后更新**：2026-08-28 00:24:23（文档创建）
> **文档状态**：全局顶部导航栏（`web/src/components/TopBar.vue` + `web/src/components/StatusBadge.vue`）的结构、全局参数与**全部变更记录**（含精确时间 年-月-日 时:分:秒）
> **关联文档**：[Design.md](../rules/Design.md)（设计规范）· [Dashboard.md](./Dashboard.md)（记录入口联动）· [Datas.md](./Datas.md)（Datas 副导航）· [VERSION_1_0_6.md](../versions/VERSION_1_0_6.md)（版本迭代记录）

---

## 0. 总览

TopBar 为**全局主导航**，出现在所有页面上方（`App.vue` 布局内），由三部分构成（从左到右）：

1. **品牌区（brand）**：Logo 图片 + 品牌名 BenchScope + 版本标签，点击回到 `/dashboard`
2. **导航菜单（nav-menu）**：AntDV `a-menu` 水平菜单，6 栏固定项，随当前路由高亮，点击跳转对应路由
3. **右侧状态区（topbar-right）**：Service 服务状态徽标——**仅状态颜色图标（无文字）**，hover tooltip 显示详情

---

## 1. 品牌区（brand）

| 参数 | 当前值 | 说明 |
| --- | --- | --- |
| Logo 图片 | `/blue_logo.png` | 后端 `app.py` 静态路由提供（避免被 SPA fallback 吞掉） |
| Logo 尺寸 | **48 × 48px**，`border-radius: 12px`，`object-fit: contain` | 1.0.6 放大（40→48px） |
| 品牌名 | **BenchScope** | 17px / 700 字重，主文字色 |
| 版本标签 | 动态 `v1.0.6-dev` | `a-tag color="blue"`，`v-if="versionTag"`；来源 `GET /api/version` 的 `display` 字段（后端 `_version_display()` 生成，开发版带 `-dev`，正式版只显示版本号）；接口失败时隐藏 |
| 点击行为 | `$router.push('/dashboard')` | 回到仪表盘 |

## 2. 导航菜单（nav-menu）

- 组件：AntDV `a-menu`，`mode="horizontal"`，`:selectedKeys="[activeKey]"`，`:items="menuItems"`，`@click="onMenuClick"`（`router.push('/'+key)`）。
- `menuItems` 为 `computed`（依赖 `i18nState` 语言状态），**切换界面语言时菜单文案即时更新**。
- `activeKey` 为 `computed`，按 `route.path` 前缀匹配（`startsWith`），无匹配时回退 `dashboard`。

| 顺序 | key | 图标 | i18n 文案（zh / en） | 路由前缀 | 页面 |
| --- | --- | --- | --- | --- | --- |
| 1 | dashboard | `DashboardOutlined` | 仪表盘 / Dashboard | `/dashboard` | 仪表盘 |
| 2 | performance | `ExperimentOutlined` | 性能测试 / Performance | `/performance` | 性能测试（任务化） |
| 3 | accuracy | `FundOutlined` | 精度测试 / Accuracy | `/accuracy` | 精度测试 |
| 4 | sessions | `MessageOutlined` | 会话 / Sessions | `/sessions` | 会话（SSE 对话） |
| 5 | datas | `DatabaseOutlined` | Datas / Datas | `/datas` | **记录管理**（1.0.6 新增，含 Perfs/Evals/Analysis 副导航子路由） |
| 6 | settings | `SettingOutlined` | 设置 / Settings | `/settings` | 设置 |

## 3. 右侧状态区（topbar-right）

| 参数 | 当前值 | 说明 |
| --- | --- | --- |
| 组件 | `<StatusBadge :label="t('service')" :ready="serviceReady" :extra="serviceExtra" no-label />` | `no-label`：**仅显示状态颜色图标，不显示文字** |
| 图标 | `CheckCircleFilled`（就绪）/ `CloseCircleFilled`（异常） | 16px；在线绿 `#52c41a` / 离线红 `#ff4d4f` |
| `serviceReady` | 恒为 `true` | 当前为占位实现（1.0.6 暂不接入真实探测） |
| `serviceExtra` | `'benchscope'` | tooltip 附加信息（与 label 合并显示于 hover） |
| 交互 | 无点击行为，hover 显示 tooltip（label + extra） | 状态详情以 tooltip 承载，界面保持极简 |

### StatusBadge 组件全局参数（`web/src/components/StatusBadge.vue`）

| prop | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `label` | String | 必填 | 状态名称；`no-label` 时不渲染 `.status-label` 文本，仅用于 tooltip |
| `ready` | Boolean | `false` | 就绪态 → 绿 `CheckCircleFilled`；否则红 `CloseCircleFilled` |
| `extra` | String | `''` | tooltip 附加信息 |
| `noLabel` | Boolean | `false` | **1.0.6 新增**：为 `true` 时隐藏文字、仅显示状态颜色图标 |

## 4. 样式全局参数（`.topbar`）

| 参数 | 值 |
| --- | --- |
| 高度 | `56px`（`line-height` 同步） |
| 背景 | `--ant-color-bg-container`（#fff，亮/暗主题自适应） |
| 底部边框 | 1px `--ant-color-border` |
| 阴影 | `0 1px 4px rgba(0,21,41,0.06)` |
| 内边距 | `0 20px` |
| 品牌区 | flex 居中，gap 6px，`margin-right: 24px` |
| 菜单 | `flex: 1` + `min-width: 0`，`border-bottom: none`（去掉 antd 默认下划线） |

---

## 5. 导航变更记录（按时间顺序，含精确时间）

> **约定**：以下时间取自代码提交（git commit）时间，格式 `年-月-日 时:分:秒`；此后每次导航/全局参数变更，均需在本文档**追加**一条记录（含精确到秒的时间），并同步 `docs/versions/` 与 `docs/rules/Design.md`。

### 2026-08-24 11:13:52 — v1.0.3 初始导航（commit `fc9fafb`）
- 导航 3 栏：**vLLM / SGLang / 日志管理**（`ThunderboltOutlined` / `RocketOutlined` / `FileSearchOutlined`）
- 品牌区：`ThunderboltFilled` 图标 + 小写 `benchscope` + 固定标签 `v1.0.3`；点击回 `/vllm`
- 右侧：`服务` 徽标 + `环境` 徽标（StatusBadge）+ 「设置」按钮（`primary ghost`）
- 菜单文案硬编码中文，未接入 i18n

### 2026-08-24 16:19:29 — v2.0 UI 大改（commit `895c905`）
- 导航改为 **5 栏**：dashboard / performance / accuracy / sessions / settings（图标 `Dashboard/Experiment/Fund/Message/Setting` Outlined）
- 品牌区点击改为回 `/dashboard`；版本标签 `v1.0.4` → `v2.0`
- 徽标文案接入 i18n（`t('service')` / `t('environment')`），「设置」按钮文案 `t('settings')`
- `activeKey` 改为按新 5 路由前缀匹配

### 2026-08-24 18:25:05 — 品牌 Logo 化（commit `8f99cad`）
- 品牌图标 `ThunderboltFilled` → **Logo 图片** `/bs-logo.png`（28×28px，圆角 6px）
- 品牌名 `benchscope` → **BenchScope**；版本标签 `v1.0.5`
- 移除右侧「设置」按钮（设置已入导航菜单）；删除 `ThunderboltFilled` 导入

### 2026-08-25 18:52:53 — 菜单 i18n 响应化（commit `c01fcaa`）
- `menuItems` 由静态数组改为 **`computed`**（依赖 `i18nState`），切换语言菜单即时更新

### 2026-08-26 00:54:05 — 右侧区精简（commit `890c7a2`）
- 移除 `环境` 徽标与竖向分隔线（`a-divider`），右侧仅保留 **Service 服务** 徽标
- 移除 TopBar 对 `useConfigStore` 的依赖（推理状态探测不再由导航承担）

### 2026-08-26 23:56:12 — v1.0.5 发布（commit `00a09f8`，tag `v1.0.5`）
- 5 栏导航 + Service 徽标形态定型并随 v1.0.5 发布

### 2026-08-27 00:55:23 — 新增 Datas 导航（commit `bbcf4cd`）
- 导航 5 栏 → **6 栏**：Sessions 之后插入 **datas**（`DatabaseOutlined`，i18n `datas`：Datas / Datas）
- `activeKey` 增加 `/datas` 前缀匹配；`/datas` 路由注册（1.0.6 记录管理入口）

### 2026-08-27 13:20:02 — Logo 换新 + 版本标签动态化（commit `6f3a83d`）
- Logo `/bs-logo.png` → **`/blue_logo.png`**（蓝色海豚，与 Sessions 头像 / favicon 统一）
- 版本标签由硬编码改为**动态拉取** `GET /api/version` 的 `display`（开发中 `v1.0.6-dev`，正式版 `v1.0.6`）；接口失败隐藏
- Logo 尺寸 28×28 → **40×40px**，圆角 6 → 10px，补 `object-fit: contain`

### 2026-08-27 19:02:20 — Datas 副导航子路由（commit `02b2a8a`）
- 路由 `/datas` 改为容器页 + 子路由：默认重定向 `/datas/perfs`，子页 `perfs / evals / analysis`（DatasView 渲染副导航 + router-view）；主导航 `datas` 项高亮规则不变（前缀 `/datas` 匹配全部子页）

### 2026-08-28 00:16:53 — Logo 放大 + Service 状态去文字（commit `cd2cac3`）
- **Logo 40×40 → 48×48px**，圆角 10 → **12px**（放大强调品牌）
- **Service 状态仅保留状态颜色图标，无文字**：`StatusBadge` 新增 `noLabel` prop（`v-if="!noLabel"` 控制 `.status-label` 渲染）；TopBar 传 `no-label`，界面只显示在线绿 / 离线红图标，hover tooltip 仍显示完整状态详情
- 同步更新：[Dashboard.md](./Dashboard.md)（记录入口联动）、[Datas.md](./Datas.md)、[Design.md](../rules/Design.md)（顶部导航规范）、[VERSION_1_0_6.md](../versions/VERSION_1_0_6.md) 迭代 15

---

## 6. 维护约定

- **任何**对主导航/品牌区/右侧状态/全局参数的修改（含文案、图标、路由、样式、组件 prop），必须在本节**追加变更记录**，记录**精确到秒**的时间（`年-月-日 时:分:秒`，以提交/落地时刻为准）。
- 同步更新：[Design.md](../rules/Design.md) §1 顶部导航规范、[VERSION_1_0_6.md](../versions/VERSION_1_0_6.md) 当前版本迭代记录、本页相关 i18n 键说明。
- 菜单项数量变更时同步更新本文档 §2 路由映射表与 [Design.md](../rules/Design.md) 顶部导航栏数。
