---
title: "RAG Day 18+19：Context Assembly、Ollama 问答与异常传播"
project: "基于 RAG 的个人技术知识库问答服务"
system_layer: "知识层 / RAG 问答编排"
document_type: learning_note
status: completed
last_updated: 2026-10-12
tags: [Python, RAG, Context-Assembly, Ollama, ChromaDB, Retrieval, LLM, Source, Exception, Debug]
---

# RAG Day 18+19：Context Assembly、真实 LLM Answer 与错误处理

- 开发与验收记录日期：2026-10-12
- 阶段：RAG V1 — Answer + Sources 的最小开发验证
- 范围：基于已完成的真实 Top-K 检索，实现 Context Assembly、Ollama Chat 以及必要故障传播
- **结论：Minimal RAG Answer — Development Verification PASS；RAG V1 尚未完成或冻结。**
- 证据性质：以下测试由用户在本地 WSL/Ollama/ChromaDB 中执行并通过终端截图确认；本笔记撰写时没有再次运行这些服务或获取新的 Git HEAD。

## 1. 前置能力与本次目标

前置能力（Day 16+17 已完成）：

- `src/retrieval_service.py` 提供 `retrieve(question: str, top_k: int = 3) -> list[dict]`。
- `retrieve()` 内部调用 `embedding_service.embed_text()`、ChromaDB `collection.query()`，返回多个包含 `id`、`text`、`source`、`metadata`、`distance` 的字典。
- 历史知识库边界：首轮 47 Document / 610 Record 已做较完整读回验收；后续补录至 632 Record、Pending records: 0，但 632 条未做同等级完整读回。Day 16+17 新笔记补录后的实际数量仍为 **UNKNOWN**。

本阶段目标：

```text
Question
  -> retrieve(question, top_k)
  -> list[dict]（候选 Chunk）
  -> build_context(chunks, max_char)
  -> (context: str, sources: list[dict])
  -> ollama.chat(model, messages)
  -> LLM answer: str
  -> {question, answer, sources}: dict
```

本阶段不重新实现文档加载、Embedding、ChromaDB 入库和 Top-K 查询，也没有开发 FastAPI `/query`。

## 2. 本次新增的正式模块与函数契约

源文件：`src/rag_service.py`（用户本地开发；在本次学习笔记生成时尚未提供该文件已提交 GitHub 的证据）。

### `build_context(chunks: list[dict], max_char: int = 3000) -> tuple[str, list[dict]]`

职责：把候选 Chunk 整理成可读的参考资料文本，并记录**实际纳入 Context** 的来源。

- 输入：`chunks` 是字典列表，不是单个字典；`max_char` 为正整数，且应拒绝 `bool`。
- 输出一：`context` 是包含编号、`source`、`id`、正文的字符串。
- 输出二：`sources` 是对应本次纳入 Context 的来源字典列表，例如 `[{"id": "A", "source": "a.md"}]`。
- 采用按 Top-K 排序逐条拼接完整 Chunk 的简单策略：构建 `block`，检查 `len(context) + len(block) > max_char` 时 `break`，确保 Context 不超过上限；没有纳入 Context 的 Chunk 也不能加入 `sources`。
- `chunks=[]` 返回 `("", [])`。已实现对空正文或缺失来源的早退策略；这种策略可能导致跳过后续可用 Chunk，属于待明确和测试的边界。
- `max_char` 限制的是 Python 字符数，**不是 LLM Token 数或真实上下文窗口限制**。

### `answer_question(question: str, top_k: int = 3) -> dict`

职责：调用 `retrieve()` → `build_context()` → `ollama.chat()`，返回结构化结果。

```python
{
    "question": "用户问题",
    "answer": "模型基于参考资料生成的回答，或资料不足的说明",
    "sources": [{"id": "Chunk ID", "source": "文档路径"}]
}
```

- 如果 Context 为空或没有可用来源，返回“参考资料不足”，不调用 Chat 伪造答案。
- 组织 `messages=[system_prompt, user_prompt]`：每条消息包含 `role` 与 `content`。
- System Prompt 约束根据资料回答、资料不足时说明、不得虚构来源、将检索文档中的指令作为数据而不是新系统指令。
- User Prompt 明确分开问题和参考资料。
- `ollama.chat()` 的回答正文通过 `response.message.content` 读取。
- 当前 `sources` 的准确语义是**提供给模型的候选参考资料**，尚不能证明其中每条都实际支持答案中的事实。

## 3. Ollama 双模型与 API 职责

本地 `ollama list` 已确认：

| 模型 | 职责 | Python 调用 |
|---|---|---|
| `qwen3-embedding:0.6b` | 将文档或问题映射到向量 | `ollama.embed(model=..., input=...)` |
| `qwen3:4b` | 基于 Question + Context 生成自然语言回答 | `ollama.chat(model=..., messages=[...])` |

- `embed()` 的关键输出为 `embeddings`，检索与入库在相同向量空间中运行。
- `chat()` 的关键输出为 `response.message.content`。
- `query_embeddings=[question_embedding]` 使用外层列表，是因为 ChromaDB 查询接口支持**多条查询向量**。
- `results["documents"][0]` 是**第一个问题的全部返回正文列表**；`results["documents"][0][1]` 才是该问题第二条检索结果的正文。
- 这些 API 不能凭名称猜参数：曾把 ChromaDB `query_embeddings` 误写为 `question_embeddings`，也曾把 Ollama `messages` 误写为 `message`。

## 4. Python 数据结构与本次重复错误

### 类型边界

```text
retrieve()        -> list[dict]
build_context()   -> tuple[str, list[dict]]
ollama.chat()     -> SDK 响应对象
response.message.content -> str
answer_question() -> dict
```

### 错误与修复

1. **列表与字典混用**：`chunks["text"]` 是错误的，因为 `chunks` 是列表；遍历得到 `chunk` 字典后才使用 `chunk["text"]`。
2. **`enumerate` 的顺序**：`for index, chunk in enumerate(chunks, start=1)`，返回顺序是 `(index, value)`；`range(3)` 产生 `0, 1, 2`。
3. **共享可变字典引用**：循环外新建一次 `source={}` 再反复修改和 `append()`，会使列表里多个位置指向同一对象；应循环内为每条来源创建独立字典。
4. **Context 总长度**：不能只检查 `len(chunk["source"])`；应检查当前 Context 与新增完整 block 的长度之和。
5. **变量名称一致性**：`sources=[]` 与 `source={}` 不可混淆；空列表场景应该返回类型一致的 `(content, sources)`。
6. **Chat 消息结构**：仅创建 `system_prompt={}`、`user_prompt={}` 不会自动填充 `messages=[]`；需显式组织 `messages=[system_prompt, user_prompt]`。
7. **函数返回类型**：标注 `-> dict` 时不能只 `return answer` 字符串；应返回 question/answer/sources 组成的 dict。

### `break` / `continue` / `return`

- `break`：停止本次循环，退出循环后继续函数剩余代码；本项目用于 Context 容量达到上限。
- `continue`：跳过当前循环的一条记录，进入下一条；若要跳过坏 Chunk，可在明确策略后使用。
- `return`：直接结束函数并返回结果；本项目用于空资料早退。

## 5. `PYTHONPATH`、模块导入和测试入口

- `python src/rag_service.py`：脚本所在的 `src` 通常会进入模块搜索路径，因此能导入同目录的 `retrieval_service.py`。
- 从项目根目录使用 `python - <<'PY'` 测试时，`PYTHONPATH=src` 可为**当前命令**补充模块搜索路径：`PYTHONPATH=src python - <<'PY' ... PY`。
- `PYTHONPATH` 控制导入时的搜索路径；不控制 ChromaDB 的资料检索，也不会替代 Ollama 服务。
- `if __name__ == "__main__":`：直接运行该文件时执行测试；被别的模块（将来包括 FastAPI）导入时不自动执行测试请求。
- 导入模块时顶层可执行语句会在首次导入时运行，因此不能把昂贵的 `answer_question()` 测试调用留在 `__main__` 保护之外。

## 6. 异常传播与错误分类

从 `answer_question()` 同时包裹 Retrieval、Context、Chat 的 `try` 中处理相应 Ollama 故障：

```python
except ollama.ResponseError as e:
    raise RuntimeError(f"Ollama model request fail: {e}") from e
except ConnectionError as e:
    raise RuntimeError(f"connect fail: {e}") from e
except httpx.TimeoutException as e:
    raise RuntimeError("Ollama timeout") from e
```

第三类异常要求模块导入 `httpx`；当前截图中超时分支存在，但**尚无真实超时运行验证**。

- Ollama SDK 当前版本的服务连接失败在本次实测中表现为内置 `ConnectionError`。
- `except` 匹配并捕获指定异常；`raise` 向上层传播一个错误；`raise ... from e` 显式建立因果链，新的异常 `__cause__` 保留原始错误。
- `retrieve()` 内部 `ollama.embed()` 发生故障，如在外层 `try` 范围内且内部未处理，可以传播到 `answer_question()` 并被匹配的 `except` 捕获。
- `TypeError` / `ValueError` 等参数错误应与服务错误区分，不统一改写为“资料不足”。
- 三种必须分开的状态：**用户输入不合法 / 知识证据不足 / 依赖服务失败**。这决定后续 FastAPI 错误响应设计。

## 7. 实际开发测试与可证结论

以下结果仅基于本话题中的用户终端运行记录，不扩大为新的独立回归或生产认证。

| 验证项 | 实际观察 | 本阶段结论 |
|---|---|---|
| 两条手工 Chunk 的 Context Assembly | 两条正文和两个 Source 对齐，长度受限，空列表和极小长度返回空结果 | 基础测试 PASS |
| STM32 向网关返回 ACK | 真实 `retrieve()` → Context → `qwen3:4b`，返回结构化答案与来源；模型指出证据无法确定完整协议细节 | 最小真实问答运行 PASS；答案完整性有限 |
| MQTT LWT | 命中 Gateway Day50 资料，回答 Broker 异常断连遗嘱等核心机制 | 代表性问答 PASS；须区分 LWT 协议能力与业务处理 |
| ChromaDB `last_updated` | 命中 RAG Day13 Metadata 笔记，解释 `datetime.date` 转换为 ChromaDB 支持类型 | 代表性问答 PASS |
| “我的下周课程表是什么？” | 模型说明参考资料不足，但仍返回无关技术笔记作为 `sources` | 代表性拒答行为基本正确；Supporting Sources 语义尚未解决 |
| 非法参数 5 组 | 空问题、空白问题、`top_k=0` 返回 ValueError；`top_k=True`、`top_k="3"` 返回 TypeError | 5/5 PASS |
| 模型不存在 | 将 `CHAT_MODEL` 临时改为不存在值；`RuntimeError` 的 `__cause__` 是 Ollama `ResponseError` (404) | 转换及保留原因 PASS |
| 连接失败 | 临时 `OLLAMA_HOST=http://127.0.0.1:11435`；外层 RuntimeError 的 `__cause__` 是 ConnectionError | Embedding/Retrieval 链路连接故障处理 PASS |
| 模型超时 | 仅实现异常分支 | NOT TESTED |
| 检索结果嵌套列表等长检查 | 原 `retrieve()` 使用 zip，尚可能对字段长度不一致静默截断 | NOT IMPLEMENTED/TESTED |
| 当前知识库总 Record 数 | 本阶段没有提供新增 Day16+17 笔记补录后计数 | UNKNOWN |

注：故障测试中一度出现 `ollama.ResponseErro` 拼写错误（AttributeError），随后更正为 `ollama.ResponseError`，模型不存在的真实测试最终通过。此类关键字/API 拼写问题需要列入复习队列。

## 8. 当前 Sources 的已知限制

`build_context()` 中的 `sources` 保证“哪些候选 Chunk 实际加入 Context”，**不等于**“最终答案每一句话都被这些 Chunk 支持”。

典型反例：用户询问下周课程表，ChromaDB 仍返回技术笔记 Top-K；模型虽然没有编造课程安排，返回的 `sources` 却依然含不相关笔记。

因此：

- 不能把向量 `distance` 当成正确率或足够证据的证明。
- 初步 distance 阈值方案可作为后续实测候选筛选手段，但没有跨模型通用的阈值，也不能单独保证证据充分性。
- 后续 FastAPI 设计时须明确 `sources` 表示候选参考资料还是确认支持答案的证据；在完成可靠性修正前不得宣传来源严格可核查。
- 暂不因此引入 Reranker、Hybrid Search、复杂 Agent 或大规模质量评估平台。

## 9. 个人学习复盘与复测队列

当前薄弱点为 Python 数据结构、第三方 API 参数契约、导入/执行时机以及异常调用链；项目运行成功不等于这些知识已经独立掌握。

闭卷复测建议：

1. 画出 `question → embed_text → collection.query → retrieve → build_context → ollama.chat → dict`，解释每步所在模块和输入/输出类型。
2. 给嵌套的 `results["documents"]`，写出第一组查询的第二条正文的下标。
3. 判断一次循环外创建 `source={}`、三次 `append(source)` 后为何得到相同引用；说出 `range(3)` 的实际取值。
4. 比较 `enumerate()`（index + value）和 `zip()`（多列表同位置元素），以及字段列表不等长的风险。
5. 比较 `break`、`continue`、`return`，演示一个 Chunk 超限后 Sources 该如何变化。
6. 解释 `messages` 的 `role/content` 数据契约以及 `ollama.embed()` 与 `ollama.chat()` 的差别。
7. 解释 `PYTHONPATH=src`、顶层模块执行和 `if __name__ == "__main__":`。
8. 解释 `except`、`raise`、`from e`、`__cause__`；定位 `retrieve()` 内 Embedding 的 ConnectionError 如何传播。
9. 用 Gateway ACK 或 MQTT LWT 的真实文档，区别“检索相关”“资料支持”“模型回答”三个不同层次。

后续每个新开发阶段仍先做简短闭卷复习，针对同类错误增加代码阅读、Debug 和独立解释；但不在连续编写代码过程中反复打断。

## 10. 进入下一阶段之前的项目边界

已完成到最小真实 RAG Answer 开发验证；仍待：

- FastAPI `/query` 的请求、响应 Schema、HTTP 实际调用与基本错误处理。
- 来源语义与无关问题的可靠性边界。
- `retrieve()` 结果列表对齐校验、超时等有界回归，以及本地 ChromaDB 当前数据一致性与数量核对。
- README、依赖、配置和可复现运行说明。
- 开发完成 → 必要真实回归 → V1 功能与版本冻结 → 正式技术面/压力面 → 按需求进入 Maintenance 或后续有目标的开发。

RAG 继续作为 Python AI 知识服务，不与 Orange Pi V1.5 RK3588 RKNN NPU 推理强行绑定。未来 Orange Pi V2 可以通过 HTTP 调用 RAG API；RAG 不负责 Gateway UART/MQTT/ACK 或 STM32 设备控制。

**本笔记完成并不代表代码已提交 GitHub、Drive 已同步、FastAPI 已实现或 RAG V1 已冻结。**
