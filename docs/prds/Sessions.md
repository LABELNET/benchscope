# benchscope Sessions 页面 — 功能与约束说明

> **版本**：v1.0.7  
> **最后更新**：2026-08-29  
> **文档状态**：Sessions（SSE 流式对话）页面的功能逻辑与约束条件说明  
> **关联文档**：[Performance.md](./Performance.md) · [Dashboard.md](./Dashboard.md)

---

## 0. 总览

Sessions 页面提供与 OpenAI 兼容推理服务的 **SSE 流式对话**：

- 左侧：会话列表（新建 / 删除 / 清空），会话持久化于 `~/.benchscope/sessions/*.json`（受 `data_dir` 配置影响，见 [Settings.md](./Settings.md)）
- 右侧：会话标题栏（实时推理性能数据，**header 颜色标记所选模型状态**）+ 消息区（思考块 / Markdown 回复）+ 底部输入栏（**Provider** / 模型 / 质量 / 思考开关 / 发送）

---

## 1. 会话管理

| 功能 | 行为 |
| --- | --- |
| 新建会话 | 左侧「+ 新建」按钮 → `POST /api/sessions`（携带当前模型）→ 自动选中 |
| 会话列表 | 标题（取首条用户消息前 50 字）、点击切换；hover 显示删除（×，popconfirm） |
| 删除会话 | `DELETE /api/sessions/{id}`，删除持久化文件 |
| 清空会话 | header「清空」按钮（popconfirm）→ `DELETE /api/sessions`，清空全部 |
| 持久化 | 每条消息与性能数据（`perf`）写入会话 JSON；刷新页面后恢复 |

## 2. 对话与流式（SSE）

- 发送：`POST /api/sessions/{id}/chat`（`fetch` 流式读取，非 axios）。
  - 请求体：`{ message, model, quality, enable_thinking, provider_id }`（**provider_id 1.0.7 新增**，来自输入栏 Provider 下拉，缺省沿用会话已绑定的 provider_id）
- 后端 `session_manager.stream_chat`：按 `provider_id` 从 `config.list_providers()` 解析该 Provider 的 API 配置（`_provider_api_config`），
  调用其 OpenAI 兼容端点（`base_url` + `endpoint`，默认 `/v1/chat/completions`），`stream: true`；无 provider_id 时回退全局 `config.api`。
- 流式解析：
  - `delta.reasoning_content` → 思考增量（`thinking` 事件）
  - `delta.content` → 正文增量（`token` 事件），实时渲染
  - `data: [DONE]` → 结束
- **思考/正文分离**：后端按已知推理标签对（`<think>` / `<reasoning>` / `<thinking>` / `<reflection>` / `<analysis>` 及其全角变体）解析 `parse_think_tags`，未闭合标签剩余内容归为思考；消息落库为 `content` + `thinking` 两段。
- 前端 Markdown 渲染（`renderMarkdown`，自实现）：代码块（含语言标识 + 复制按钮）、行内代码、加粗/斜体、列表（`-`/`*`/`1.`）。

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
| 对话质量 | high / medium / low → temperature 0.9 / 0.5 / 0.2；localStorage `benchscope_chat_quality` 记忆 |
| 思考开关 | `enable_thinking` → `chat_template_kwargs.enable_thinking`；localStorage `benchscope_chat_thinking` 记忆 |
| 发送 | 有内容且非流式中可点；`Enter` 发送、`Shift+Enter` 换行 |
| 输入框 | 1–6 行自适应；流式中禁用 |

## 5. 约束与边界

| 项 | 约束 |
| --- | --- |
| 服务依赖 | 需在 Settings → Providers 配置至少一个 Provider；发送时按所选 Provider 调用其 OpenAI 兼容接口，离线/不可达时流式请求失败并提示（header 红色） |
| 流式中操作 | 发送按钮禁用、输入框禁用；流式结束前不允许切换操作 |
| 消息上限 | 无截断；日志行保留最近 8000 行（logLines） |
| 思考块 | 默认折叠（`_thinkingOpen=false`），点击展开 |
| 持久化目录 | 会话存储于服务端 `data_dir/sessions`（默认 `~/.benchscope/sessions`），非浏览器本地 |
| i18n | 全量中英双语键 |
| 主题 | 使用 antd 变量，亮/暗自适应 |

## 6. 相关文档约定

> **约定**：后续对 Sessions 页面的设计/界面修改、逻辑与策略调整、UI 调整，均需同步更新本文档。
