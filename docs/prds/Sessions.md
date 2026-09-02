# benchscope Sessions 页面 — 功能与约束说明

> **版本**：v1.0.9
> **最后更新**：2026-09-02
> **文档状态**：Sessions（SSE 流式对话）页面的功能逻辑与约束条件说明  
> **关联文档**：[Performance.md](./Performance.md) · [Dashboard.md](./Dashboard.md)

---

## 0. 总览

Sessions 页面提供与 OpenAI 兼容推理服务的 **SSE 流式对话**：

- 左侧：会话列表（新建 / 删除 / 重命名 / 清空），会话持久化于 `~/.benchscope/sessions/*.json`，并附带 `logs_dir/sessions/*.log` 对话日志（受 `data_dir` 配置影响，见 [Settings.md](./Settings.md)）
- 右侧：会话标题栏（实时推理性能数据，**header 颜色标记所选模型状态**）+ **对话采样参数（top_k / temperature / top_p）** + 消息区（思考块 / Markdown 回复）+ 底部输入栏（**Provider** / 模型 / 质量 / 思考开关 / 发送）

---

## 1. 会话管理

| 功能 | 行为 |
| --- | --- |
| 新建会话 | 左侧「+ 新建」按钮（**1.0.9 图标改为加号 `PlusOutlined`**）→ `POST /api/sessions`（携带当前模型）→ 自动选中 |
| 会话列表 | 每项显示**标题 + 修改时间**（`updated_at`，格式 `MM-DD HH:mm`，跨年显示年份）；点击切换；hover/active 显示**三点菜单**（`MoreOutlined`） |
| 三点菜单（1.0.9） | 点击弹 `a-dropdown`：**重命名**（弹框输入新标题，`PATCH /api/sessions/{id}/title`）与**删除**（`DELETE /api/sessions/{id}`） |
| 预览状态（1.0.9） | 会话项前置小图标：该会话**正在通讯（流式）时切换为「三个点滚动」动画**（`.session-typing`，`@keyframes sessionDotRoll`，标识 `streamingId`）；其它状态显示静态消息图标 |
| 删除会话 | `DELETE /api/sessions/{id}`，删除持久化文件与对应会话日志 |
| 清空会话 | header「清空」按钮（**1.0.9 改为居中确认弹窗** `a-modal`，非 popconfirm）→ 确认后 `DELETE /api/sessions`，清空全部（含会话日志目录） |
| 持久化 | 每条消息与性能数据（`perf`）写入会话 JSON；刷新页面后恢复 |
| 会话日志（1.0.9） | 对话记录以**可读日志落盘**到 `logs_dir/sessions/<id>.log`（区别于 `sessions/*.json` 缓存）：会话创建/消息变更/重命名/性能更新时刷新；删除/清空同步删除。内容为时间戳 + role + 正文 + thinking 的可读 transcript |

## 2. 对话与流式（SSE）

- 发送：`POST /api/sessions/{id}/chat`（`fetch` 流式读取，非 axios）。
  - 请求体：`{ message, model, quality, enable_thinking, provider_id, top_k, temperature, top_p }`（**provider_id 1.0.7 新增**，来自输入栏 Provider 下拉，缺省沿用会话已绑定的 provider_id；**top_k / temperature / top_p 为 1.0.9 新增**，来自顶部性能栏采样参数，缺省不传）
- 后端 `session_manager.stream_chat`：按 `provider_id` 从 `config.list_providers()` 解析该 Provider 的 API 配置（`_provider_api_config`），
  调用其 OpenAI 兼容端点（`base_url` + `endpoint`，默认 `/v1/chat/completions`），`stream: true`；无 provider_id 时回退全局 `config.api`。
- 流式解析：
  - `delta.reasoning_content` → 思考增量（`thinking` 事件）
  - `delta.content` → 正文增量（`token` 事件），实时渲染
  - `data: [DONE]` → 结束
- **思考/正文分离**：后端按已知推理标签对（`<think>` / `<reasoning>` / `<thinking>` / `<reflection>` / `<analysis>` 及其全角变体）解析 `parse_think_tags`，未闭合标签剩余内容归为思考；消息落库为 `content` + `thinking` 两段。
- **采样参数（1.0.9）**：后端 `stream_chat` 显式 `temperature` 优先级高于 quality 映射（high 0.9 / medium 0.5 / low 0.2）；`top_k>0` / `top_p` 非空时透传进 payload（`top_k` / `top_p` 为部分 OpenAI 兼容服务扩展字段，缺失/不支持时忽略）。
- 前端 Markdown 渲染（`renderMarkdown`，**1.0.9 起用 `marked` + `DOMPurify` 取代自实现解析**，支持 GFM 表格 / 标题 / 引用 / 图片等）：代码块经 `wrapCodeBlocks` 包装为带语言标签 + Copy 按钮；Copy 用**事件委托**（`onDocClick`，v-html 动态插入，避免内联 onclick 被 DOMPurify 清理）；`DOMPurify.sanitize` 防 XSS（`ADD_ATTR:['target']`）。
- **代码样式（1.0.9）**：代码块**纯黑底（`#0a0a0a`）+ 浅色正文（`#e6edf3`）**——`.code-block` 背景 `#0a0a0a`、极简 header `#0e0e0e`；**无行号**，直接 `<pre><code>` 展示；**比正文更小更紧凑**的等宽字体：`font-size 12.5px`（正文 14px）、`line-height 1.4`（正文 1.75）、`tab-size 4`，代码区 `padding 8px 14px`；`.copy-btn` 弱化默认隐藏、代码块悬停时显示；`.code-lang` 置灰小字。字体栈 `JetBrains Mono / Fira Code / SF Mono / Cascadia Code / Consolas / monospace`（无则回退）；行内代码 `.inline-code` 黑底绿字同字体；用户气泡内行内代码沿用蓝底白字以保证对比度。
- **代码语法高亮（1.0.9）**：代码块经 **highlight.js**（`lib/core` 按需注册 javascript/typescript/python/json/bash/xml/css/sql/java/c/cpp/go/rust/yaml/markdown/plaintext 语言 + `atom-one-dark` 暗色主题）做**语法着色**——通过自定义 `marked.Renderer().code`（marked v18 单 token 参数 `{text,lang}`）在 renderer 内一次性生成完整 `.code-block`（header + `<pre><code>`，无行号）；未识别语言自动 `highlightAuto` 降级转义。高亮 `span class="hljs-*"` 经 DOMPurify 保留（默认允许 span/class）；Copy 由事件委托 `onDocClick` 读取 `<pre>` 的 `textContent`（浏览器解码实体）实现。

## 3. 顶部性能栏（实时推理指标）

| 指标 | 计算 |
| --- | --- |
| turns / steps | 用户消息数 / 用户+助手消息数 |
| LLM Time | 总耗时（mmss 格式） |
| TTFT | 首 token 时刻 − 开始时刻 |
| Output tok/s | 已收 token 数 /（当前 − 首 token） |
| TPOT / ITL | 解码均耗 / token 间隔均值 |

- 流式中实时刷新（每收到 token 更新）；结束后写入会话 `perf` 并持久化（`PATCH /api/sessions/{id}/perf`）。
- **header 颜色标记所选模型状态（1.0.7）**：chat-header 边框随所选 Provider 探测结果变化——
  探测在线（Provider 可达、可获取模型）→ `.chat-ok` **绿色**（#52c41a）；默认 / 离线 → `.chat-bad` **红色**（#ff4d4f）。

## 4. 输入栏与偏好

| 项 | 说明 |
| --- | --- |
| Provider 选择 | 来自 Settings → Providers 列表（`GET /api/config/providers`）；localStorage `benchscope_chat_provider` 记忆，无记忆时默认选第一个；切换 → 清空模型并重新探测该 Provider（联动模型列表与 header 状态色） |
| 模型选择 | 来自所选 Provider 的 `/v1/models`；本地记忆（localStorage `benchscope_chat_model`），列表加载后自动选第一个 |
| 对话质量 | high / medium / low → temperature 0.9 / 0.5 / 0.2；localStorage `benchscope_chat_quality` 记忆；1.0.9 起被采样参数中的显式 temperature 覆盖 |
| 对话采样参数（1.0.9） | 顶部性能栏新增三个输入框 **top_k / temp / top_p**（`a-input-number`）：即 `top_k`（1–200，默认 10）、`temperature`（0–2，步进 0.1，默认 0.5）、`top_p`（0–1，步进 0.05，默认 1）；分别 localStorage `benchscope_chat_top_k` / `benchscope_chat_temperature` / `benchscope_chat_top_p` 记忆，随发送请求携带。**布局（1.0.9）**：chat-header 为 `flex-wrap` 行——宽度足够时参数 `margin-left:auto` **右对齐**与性能栏同排；宽度不足时 **换行**到新行仍靠右 |
| 思考开关 | `enable_thinking` → `chat_template_kwargs.enable_thinking`；localStorage `benchscope_chat_thinking` 记忆 |
| 发送/停止（1.0.8） | 非流式中显示圆形「发送」图标按钮（蓝色圆 + 白箭头，`.send-btn`）：有内容且非流式可点（`Enter` 发送、`Shift+Enter` 换行）；流式中显示「停止」方形图标（`.send-stop`）：点击中止数据流（`AbortController.abort`，保存已生成部分，不报错），恢复发送图标 |
| 输入框 | 1–6 行自适应；流式中禁用 |

## 5. 约束与边界

| 项 | 约束 |
| --- | --- |
| 服务依赖 | 需在 Settings → Providers 配置至少一个 Provider；发送时按所选 Provider 调用其 OpenAI 兼容接口，离线/不可达时流式请求失败并提示（header 红色） |
| 流式中操作 | 发送按钮变「停止」可中止数据流、输入框禁用；流式结束前不允许切换会话 |
| 消息上限 | 无截断；日志行保留最近 8000 行（logLines） |
| 思考块 | 默认折叠（`_thinkingOpen=false`），点击展开 |
| 持久化目录 | 会话存储于服务端 `data_dir/sessions`（默认 `~/.benchscope/sessions`），对话日志于 `data_dir/logs/sessions`，非浏览器本地 |
| i18n | 全量中英双语键 |
| 主题 | 使用 antd 变量，亮/暗自适应 |

## 6. 相关文档约定

> **约定**：后续对 Sessions 页面的设计/界面修改、逻辑与策略调整、UI 调整，均需同步更新本文档。
