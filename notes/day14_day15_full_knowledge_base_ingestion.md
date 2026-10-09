---
title: RAG Day 14+15 正式知识库批量向量入库
project: 基于 RAG 的个人技术知识库问答服务
system_layer: 知识层 / 文档检索服务
document_type: learning_note
status: completed
last_updated: 2026-10-09
tags: [Python, RAG, ChromaDB, Ollama, Embedding, Batch, Refactoring, Metadata, Recovery, Testing]
---

# RAG Day 14+15：正式知识库批量向量入库

**开发日期：2026-10-08 ～ 2026-10-09**

**阶段：RAG V1 — Vector Store**

**状态：Completed — Development Verification**

## 1. 本次开发目标

在 Day 13 已经完成单真实文档 ChromaDB 入库验证的基础上，将项目推进为可持久化存储全部现有知识文档的正式向量知识库。

本次开发重点：

- 加载正式知识源。
- 批量切分 Document。
- 准备 ChromaDB Record。
- 整理模块职责，复用已有函数。
- 设计分批 Embedding 和入库机制。
- 查询已有 ID，支持中断后继续处理。
- 使用真实 Ollama Embedding 模型生成向量。
- 写入正式 `technical_knowledge` Collection。
- 读回全部 Record，完成完整性验收。

本阶段不包含语义检索、LLM 问答或 FastAPI。

## 2. 本次知识库数据范围

正式知识库使用两个目录：

| 来源目录 | 内容 | 文档数量 |
|---|---|---:|
| `docs_raw/` | LeetCode、Linux Gateway、STM32 技术文档 | 36 |
| `notes/` | RAG Day 2～Day 13 学习与开发笔记 | 11 |
| 合计 | 本轮入库前知识库快照 | 47 |

使用 `load_markdown_directory()` 分别加载两个目录，再用列表 `+` 合并。

加载成功后，得到 47 个 Document。

**说明：这 47 份文档是新增 Day 14+15 学习笔记之前的快照。新增笔记后，知识库来源数量会发生变化，需要重新补充入库。**

## 3. Document 与 Chunk 的区别

Document 代表一份加载后的 Markdown 文档，包含：

- `content`：文档正文。
- `metadata`：标题、项目、来源、日期、标签等信息。

Chunk 是一份 Document 经文本切分得到的一小段内容。

本次复用：

`split_documents(docs_all, 500, 100)`

参数：

- `chunk_size = 500`
- `chunk_overlap = 100`

实际结果：

**47 个 Document → 610 个 Chunk**

每个 Chunk 保留来源 Metadata，并额外具有 `chunk_index`。

这样即使同一文档被切成多个 Chunk，也可以区分每个 Chunk 的位置与来源。

### 为什么要保留 source？

因为最终检索的单位通常是 Chunk，而不是整个 Document。

只有在 Chunk 中保存来源，才能在后续返回检索结果时定位对应 Markdown 文件。

## 4. Python 列表知识复习

### append() 与 extend()

`append(x)` 将对象 `x` 作为一个元素加入列表。

`extend(xs)` 将可迭代对象 `xs` 中的元素逐个加入列表。

因此：

- 单个 Chunk 字典加入 `chunks`，使用 `append(chunk)`。
- 单个 Document 切出来的 Chunk 列表加入 `all_chunks`，使用 `extend(document_chunks)`。

错误地对 Chunk 列表使用 `append()`，可能导致列表多嵌套一层，后续访问 `chunk["metadata"]` 时发生类型错误。

### 列表拼接

`docs_all = docs_a + docs_b`

会生成一个新的列表，原来两个列表不因这个操作而改变。

### 列表切片

`ids[start:start + batch_size]`

取出从 `start` 开始的一批 ID，结束下标不包含在切片中。

最后不足一批时，Python 切片仍能返回剩余元素。

## 5. Chunk ID 唯一性

继续复用 Day 13 的 `build_chunk_id()`。

V1 ID 格式：

`source::chunk_<chunk_index>`

示例：

`docs_raw/leetcode_day05_two_sum.md::chunk_0`

不能只使用 `chunk_0`，因为不同源文档都可能具有 `chunk_index = 0`。

本轮实际验证：

- Chunk 数量：610
- ID 数量：610
- `len(set(ids))`：610

**结论：本轮 610 个候选 Chunk 的 ID 没有重复。**

ID 的主要职责是唯一标识记录。Metadata 中的 source 则负责保存来源信息，可用于后续检索结果追溯或筛选。

## 6. Record 数据结构与 Metadata

ChromaDB 的一条 Record 使用四类信息：

| 字段 | 用途 |
|---|---|
| `id` | 唯一标识记录 |
| `document` | Chunk 正文 |
| `metadata` | 来源及相关描述信息 |
| `embedding` | 对应 Chunk 的语义向量 |

批量入库时：

`ids[i]`、`documents[i]`、`metadatas[i]`、`embeddings[i]`

必须指向同一个 Chunk。

若正文和向量顺序不一致，会造成语义检索结果与实际正文不匹配。

### Metadata 类型适配

YAML 中的 `last_updated` 经过 PyYAML 解析，可能成为 Python 的 `datetime.date` 对象。

ChromaDB Metadata 不能直接存储这种 Python 日期对象，所以复用：

`prepare_metadata_for_chroma()`

通过 `metadata.copy()` 创建新字典，再将 `last_updated` 转为字符串。

这样既满足 ChromaDB 的类型要求，又避免直接修改原始 Chunk 的顶层 Metadata 字典。

## 7. 代码模块化重构

本次把原先散落于测试脚本中的 Record 数据准备逻辑整理到正式模块。

### vector_store.py

新增并验证：

`prepare_chunk_records(chunks)`

输入：Chunk 列表。

输出：

- ids
- documents
- metadatas

这个函数只准备 Record 字段，不负责调用 Ollama，也不负责写数据库。

### prepare_document_records(path)

将原有单文件函数调整为：

1. `load_markdown(path)`
2. `split_document(document, 500, 100)`
3. `prepare_chunk_records(chunks)`
4. `embed_texts(documents)`
5. 返回四组数据

这样原有函数和新函数形成明确的复用关系，不再重复编写相同的 Record 准备循环。

### 文件职责

| 文件 | 职责 |
|---|---|
| `document_loader.py` | Markdown 加载与 Metadata 校验 |
| `text_chunker.py` | Document 切分 |
| `embedding_service.py` | Ollama Embedding |
| `vector_store.py` | Record 准备与 ChromaDB 操作 |
| `ingest_knowledge_base.py` | 正式知识库入库流程编排 |
| `day14_check_documents.py` | 数据准备阶段的验证脚本 |
| `day14_test_refactor.py` | 重构回归实验脚本 |

**工程规则：长期业务代码按功能命名；按 Day 命名的文件用于学习记录或阶段性实验。**

## 8. Mock 回归测试

首次接触 Python 的 `unittest.mock.patch()`。

它可以在测试过程中临时替换真实函数。

本次将：

`vector_store.embed_texts`

临时替换为模拟函数，返回与输入文本数量相同的 1024 维全零向量。

Mock 的目的不是测试 Ollama 的语义能力，而是验证重构后的函数调用关系和数据结构。

### 核心概念

- `patch()`：临时替换依赖。
- `side_effect`：指定模拟函数的运行行为。
- `call_count`：记录 Mock 被调用的次数。
- `assert_called_once()`：验证只调用一次。

### 实际运行结果

Day60 文档单文件回归：

- ids：22
- documents：22
- metadatas：22
- embeddings：22
- Mock Embedding 调用次数：1

**Mock 回归通过。**

本次没有使用 Mock 替代正式知识库的真实 Embedding。

### 本次学习中的 Python 知识

`[0.0] * 1024` 表示一条 1024 维向量。

`[[0.0] * 1024 for _ in texts]` 表示为输入的每条文本生成一条模拟向量。

Mock 目前属于初次接触阶段，已经理解用途和基本调用，不代表能够完全脱离参考独立设计 Mock 测试。

## 9. 正式知识库分批策略

本次目标共 610 条 Record。

设置：

`batch_size = 16`

使用：

`range(0, len(pending_ids), batch_size)`

遍历待处理记录。

使用相同下标范围切分：

- batch_ids
- batch_documents
- batch_metadatas

一批处理完成后，再进入下一批。

### 分批结果

610 条数据在首次全量处理时对应：

- 38 个完整批次，每批 16 条。
- 1 个剩余批次，2 条。
- 合计 39 批。

先单独写入 16 条进行验证，再通过重新执行正式入库程序补齐剩余 594 条。

分批数量检查通过。

## 10. 为什么不使用 sleep？

Python 普通 `for` 循环没有默认休眠时间，默认不会自动调用 `sleep()`。

本次调用的是同步函数：

1. `embed_texts()` 等待 Ollama 返回向量。
2. `collection.add()` 等待 ChromaDB 写入完成。
3. 两步完成后才进入下一轮循环。

因此本地运行稳定时，不需要为了批量处理而无条件增加 `time.sleep()`。

如果未来使用受限流控制的云端 API，或者出现资源压力，再考虑限流、退避重试或调整 Batch Size。

## 11. 已有 ID 查询与断点恢复

正式入库使用：

`technical_knowledge`

启动时先通过 ChromaDB 查询候选 ID 中哪些已经存在。

再将已有 ID 转换为 `set`，用于快速判断。

本次实现：

`filter_pending_records(ids, documents, metadatas, existing_ids)`

作用：

**同步筛选尚未入库的 ID、正文和 Metadata。**

### 为什么必须同步筛选？

因为如果只过滤 ID，不过滤正文和 Metadata，那么各列表的下标关系可能错位。

后续生成 Embedding 时，可能将错误正文和错误 ID 组合成一条 Record。

### enumerate()

使用：

`for index, chunk_id in enumerate(ids):`

同时取得索引和当前 ID，再用同一个索引提取对应的 Document 和 Metadata。

### 错误处理

当三个输入列表长度不一致时，应使用 `raise ValueError(...)` 明确中止，而不是仅打印错误并返回 `None`。

### 人工构造的 A/B/C 测试

输入 ID：

A、B、C。

模拟已有 ID：

B。

实际输出保留：

A、C。

对应的正文和 Metadata 同步保留，未发生错位。

**筛选函数的正常路径测试通过。**

### 当前断点恢复边界

重新运行入库程序时，可以跳过数据库中已经存在的 ID，从未入库的 ID 继续向量化。

但本次机制是以 ID 是否存在为基础的增量补录，不是完整的文档版本同步系统。

如果某个源文件内容发生修改，但已有 `source::chunk_index` ID 没有变化，还需要未来补充内容变化检测及更新策略。

## 12. 正式真实入库

本次使用：

- ChromaDB 本地持久化数据库
- Collection：`technical_knowledge`
- Embedding Model：`qwen3-embedding:0.6b`
- Batch Size：16
- Embedding Dimension：1024

真实运行流程：

Markdown → Document → Chunk → Record 字段 → 查询已有 ID → 筛选未入库数据 → 分批 Ollama Embedding → ChromaDB add。

### 第一批真实验证

首次运行：

`Saved: 16 Total: 16`

正式 Collection 成功写入 16 条真实向量记录。

随后通过独立 Python 只读命令，从 ChromaDB 获取真实 Record。

读回结果：

- Collection Count：16
- ID：`docs_raw/leetcode_day05_two_sum.md::chunk_0`
- Source：`docs_raw/leetcode_day05_two_sum.md`
- Document Length：500
- Embedding Dimension：1024

**真实单批入库及读回验证通过。**

### 剩余批量入库

删除用于限制首次运行的 `break` 后，重新执行入库程序。

由于已有 16 条记录已经保存，程序通过现有 ID 筛选机制继续处理剩余记录。

实际日志持续增加：

`Saved: 16 Total: ...`

最后一批：

`Saved: 2 Total: 610`

**正式 Collection 达到 610 条记录。**

这次是真实 Ollama 向量化，不是 Mock 数据。

## 13. 正式知识库完整性验收

**验收日期：2026-10-09**

使用独立只读 Python 命令，对现有 Markdown 重新加载并切分，生成预期 ID，再读取 ChromaDB 的正式记录。

验收项目：

- Document 总数
- Chunk 总数
- Collection Count
- 全量 ID 集合是否匹配
- 逐条 Document 正文是否匹配
- Metadata 中的 source 是否匹配
- Metadata 中的 chunk_index 是否匹配
- last_updated 是否为字符串
- Embedding 是否为 1024 维
- 原始文档来源是否全部覆盖

### 实际验收输出

| 检查项目 | 实际结果 |
|---|---:|
| Documents | 47 |
| Chunks | 610 |
| Stored Records | 610 |
| Matched IDs | 610 |
| Covered Sources | 47 |
| Embedding Dimension | 1024 |
| Result | PASS |

### 验收结论

本轮 47 份原始知识文档、610 个 Chunk，全部具有对应的正式 ChromaDB Record。

预期 ID 与已存储 ID 全部匹配。

逐条正文、source、chunk_index、日期类型和向量维度检查通过。

**RAG V1 首轮正式知识库全量向量入库：Development Verification PASS。**

注意：这不是语义检索效果评估，也不是 LLM 问答质量验收。

## 14. 本次开发中学到的工程原则

### 先明确函数职责

避免同一段 Record 处理逻辑分散在多个脚本中。

### 优先复用已有模块

先检查项目中是否已经存在需要的函数，再决定是否新增功能。

### 区分实验代码与正式代码

实验脚本可以按 Day 命名；正式业务代码采用功能名称。

### 不重复计算已有向量

入库前检查数据库已存在的 ID，只处理尚未入库的数据。

### 保持四组 Record 字段对应

ID、正文、Metadata、Embedding 必须严格对齐。

### 真实验收不能只看数量

`count() == 610` 不足以单独证明入库完整。

本次额外检查了 ID、正文、Metadata、向量维度和全部来源覆盖。

### 测试等级不能混淆

- 语法检查：只能证明语法可编译。
- Mock 测试：验证模拟条件下的函数调用关系。
- 真实入库：验证 Ollama 和 ChromaDB 实际连接。
- 全量读回：验证正式知识库保存内容的完整性。

## 15. 当前尚未完成的功能

- Question Embedding → ChromaDB `query()`。
- Top-K Vector Retrieval。
- 检索结果的正文和来源输出。
- RAG Context Assembly。
- Ollama LLM Answer。
- Answer + Sources。
- FastAPI `/query`。
- Orange Pi Agent 接入。

后续还需要考虑的工程改进包括：

- 源文档修改后如何更新已有 Record。
- 删除源文档后如何清理旧记录。
- 批量入库失败时的异常处理和日志。
- 配置化 Chunk Size、Overlap、Batch Size。
- README 与当前代码结构同步。
- 更完善的自动化测试。

这些改进不阻塞下一阶段最小 Retrieval 闭环。

## 16. 下一阶段：Top-K Retrieval

下一阶段直接复用已建好的 `technical_knowledge` Collection。

目标数据流：

用户自然语言问题 → `embed_text(question)` → 问题向量 → `collection.query()` → Top-K 相似 Chunk → 输出正文和来源。

最小验收要求：

输入真实技术问题，能够从正式知识库返回相关 Chunk，并显示 source、ID、正文。

这一步完成后再进入 LLM Answer。

然后实现 FastAPI `/query`，供后续 Orange Pi Agent 通过 HTTP 调用。

## 17. 本轮结束时的实际项目状态

**已完成：RAG V1 正式知识库首轮批量向量入库和完整性验收。**

**未完成：Retrieval、RAG Answer、FastAPI、Orange Pi 集成。**

备注：本笔记创建后将成为 `notes/` 下的新知识源，原本 47 Document / 610 Chunk 的验收数据属于创建笔记之前的知识库快照。新笔记需要通过现有增量入库机制补录，补录后的具体 Document、Chunk 和 Record 总数以重新运行的实际结果为准。

---

**Day 14+15 Conclusion：正式知识库已建立，下一阶段进入真实语义检索。**
