---
title: RAG Day 16+17 真实 Top-K 语义检索
project: 基于 RAG 的个人技术知识库问答服务
system_layer: 知识层 / 文档检索服务
document_type: learning_note
status: completed
last_updated: 2026-10-09
tags: [Python, RAG, Ollama, ChromaDB, Embedding, Retrieval, Top-K, Metadata, Source, Testing]
---

# RAG Day 16+17：真实 Top-K 语义检索

开发日期：2026-10-09

阶段：RAG V1 — Retrieval

状态：Completed — Development Verification

## 1. 本次开发目标

在 Day 14+15 已完成正式知识库向量入库的基础上，实现真实的语义检索功能。

本阶段要求：

- 接收自然语言问题。
- 调用 Ollama Embedding 模型生成问题向量。
- 从正式 ChromaDB Collection 检索 Top-K Chunk。
- 将检索结果转换为结构化 Python 数据。
- 保留每条 Chunk 的 ID、正文、Metadata、Source、Distance。
- 使用真实技术问题进行检索验收。

本阶段不负责让 LLM 生成最终答案。

## 2. 开发前的知识库基线

GitHub 上一次已确认的提交：

`2b587ab`

正式 Collection：

`technical_knowledge`

本地持久化位置：

`data/chroma/`

Embedding 模型：

`qwen3-embedding:0.6b`

向量维度：

1024

Day 14+15 历史验证：

- 47 份 Document / 610 条 Record：完整性验收 PASS。
- 新增 Day 14+15 笔记后：Collection 达到 632 条。
- 修复后再次运行入库程序：Pending records = 0。
- 632 条尚未进行与首轮相同等级的完整逐条读回验收。

本次 Retrieval 直接利用已经建立的正式知识库，不重新执行全量向量入库。

## 3. RAG Retrieval 的系统调用链

输入：

用户自然语言问题。

数据流：

```text
用户问题 question
        ↓
embed_text(question)
        ↓
生成 1024 维问题向量
        ↓
ChromaDB PersistentClient
        ↓
technical_knowledge Collection
        ↓
collection.query()
        ↓
Top-K 相似 Chunk
        ↓
整理 ID / 正文 / Source / Metadata / Distance
        ↓
返回 list[dict]
```

与向量入库的区别：

入库：

Document → Chunk → Embedding → ChromaDB

检索：

Question → Embedding → ChromaDB Query → Relevant Chunks

检索阶段不需要对知识库中已保存的所有 Chunk 重新执行 Embedding。

## 4. 本次新增正式模块

文件：

`src/retrieval_service.py`

主要接口：

```python
def retrieve(question: str, top_k: int = 3) -> list[dict]:
    ...
```

输入：

- question：自然语言问题。
- top_k：希望返回的相关 Chunk 数量。

输出：

- list[dict]：结构化检索结果列表。

职责边界：

retrieval_service.py 负责检索。

embedding_service.py 负责生成 Embedding。

ChromaDB 负责存储和向量查询。

后续 RAG Answer 模块调用 retrieve() 获取相关资料，而不是重新实现向量检索。

## 5. 获取正式 ChromaDB Collection

本次使用：

```python
client = chromadb.PersistentClient(path="data/chroma")

collection = client.get_collection(
    name="technical_knowledge"
)
```

PersistentClient：

连接本地持久化数据库。

get_collection()：

获取已经存在的 Collection。

与 get_or_create_collection() 的区别：

- get_collection()：不存在则报错。
- get_or_create_collection()：不存在时可以新建。

检索阶段更适合使用 get_collection()，避免错误路径或名称导致程序悄悄创建空 Collection。

## 6. Question Embedding

复用已有模块：

`src/embedding_service.py`

已有接口：

```python
embed_text(text: str) -> list[float]
```

本次调用：

```python
question_embedding = embed_text(question)
```

输入一条自然语言问题。

输出一条 1024 维向量。

注意：

文档入库和问题检索应使用兼容的 Embedding 模型及向量维度。

当前继续使用：

`qwen3-embedding:0.6b`

不能随意换成另一个模型，否则即使维度相同，也可能导致向量空间不兼容，影响检索结果。

## 7. ChromaDB query() API

核心调用：

```python
results = collection.query(
    query_embeddings=[question_embedding],
    n_results=top_k,
    include=["documents", "metadatas", "distances"]
)
```

### query_embeddings

用于传入查询向量。

正确的参数名是：

`query_embeddings`

开发中曾错误写成：

`question_embeddings`

实际运行报错：

`TypeError: Collection.query() got an unexpected keyword argument 'question_embeddings'`

根据异常提示修改为正确参数后，真实查询恢复正常。

### 为什么需要一层列表？

`question_embedding` 表示一条向量：

```python
[0.1, 0.2, ...]
```

而：

```python
[question_embedding]
```

表示包含一条向量的列表。

ChromaDB 支持一次输入多个查询向量，因此 query_embeddings 接收批量形式的数据。

本次只查询一个问题，所以只传入一条向量。

### n_results

控制每个问题返回的记录数量。

例如：

`n_results=3`

表示最多返回 3 条相关 Chunk。

### include

用于指定查询结果中的附加字段：

- documents：Chunk 正文。
- metadatas：Chunk Metadata。
- distances：向量距离。

注意 ChromaDB 使用 `distances`，而不是 `distance`。

## 8. Query 的返回数据结构

ChromaDB 查询返回按问题分组的结果。

例如：

```python
results = {
    "ids": [["A", "B", "C"]],
    "documents": [["正文A", "正文B", "正文C"]],
    "metadatas": [[
        {"source": "a.md"},
        {"source": "b.md"},
        {"source": "c.md"}
    ]],
    "distances": [[0.2, 0.4, 0.6]]
}
```

以上是结构示例，不是真实检索输出。

因为本次只有一个问题，所以使用：

```python
results["ids"][0]
results["documents"][0]
results["metadatas"][0]
results["distances"][0]
```

其中 `[0]` 指第一组查询结果，而不是只保留第一条 Chunk。

## 9. Python zip() 的使用

本次使用：

```python
for record_id, document, metadata, distance in zip(
    results["ids"][0],
    results["documents"][0],
    results["metadatas"][0],
    results["distances"][0]
):
    ...
```

作用：

同时遍历四个列表中位置对应的元素。

例如：

```python
ids = ["A", "B"]
documents = ["正文A", "正文B"]

for record_id, document in zip(ids, documents):
    print(record_id, document)
```

输出：

```text
A 正文A
B 正文B
```

注意：

zip() 默认在最短的列表结束时停止。

本次实际检索正常，但未来完善输入输出校验时，可以增加结果列表长度一致性检查，避免静默截断异常数据。

## 10. zip() 与 enumerate() 的区别

enumerate()：

在遍历单个列表时，同时取得下标和元素值。

Day 14+15 使用位置：

`vector_store.py → filter_pending_records()`

当时通过 index 同步筛选：

- pending_ids
- pending_documents
- pending_metadatas

zip()：

同时遍历多个列表中位置对应的元素。

Day 16+17 使用位置：

`retrieval_service.py`

用于整理：

- Record ID
- Document
- Metadata
- Distance

两者都可以用于处理对齐数据，但适用场景不同。

## 11. 将查询结果整理为 list[dict]

本次业务接口不直接暴露 ChromaDB 的原始嵌套返回结构。

目标结构：

```python
[
    {
        "id": "某个 Chunk ID",
        "text": "Chunk 正文",
        "source": "docs_raw/example.md",
        "metadata": {
            "source": "docs_raw/example.md",
            "chunk_index": 0
        },
        "distance": 0.5
    }
]
```

其中 source 从 Metadata 中读取：

```python
metadata["source"]
```

不需要重新解析 Chunk ID。

### 本次开发出现的问题

最初在 for 循环外创建：

```python
record = {}
```

然后反复修改同一个 record。

这会导致原先记录被覆盖，最终只能返回最后一次循环的数据。

修正方式：

先创建结果列表：

```python
retrieved_records = []
```

然后每次循环内部创建新的字典：

```python
record = {}
```

填写字段后执行：

```python
retrieved_records.append(record)
```

最后：

```python
return retrieved_records
```

这样可以保留全部 Top-K 结果。

## 12. 参数校验

本次对以下输入进行校验：

### question

必须是字符串。

对问题执行：

```python
question.strip()
```

去除首尾空白。

如果只包含空格，拒绝执行检索。

### top_k

要求：

- Python int 类型。
- 不能为 bool。
- 必须大于 0。

特别注意：

```python
isinstance(True, int)
```

结果为 True。

所以仅用 isinstance(top_k, int) 不足以排除布尔值。

可以先判断 bool，再判断 int。

### 本轮验证边界

参数校验逻辑已写入源码并经过代码审查。

本轮主要运行了三组合法的真实查询；不能据此宣称全部异常输入都已经经过独立运行测试。

## 13. if __name__ == "__main__"

本次将三个测试问题放在：

```python
if __name__ == "__main__":
    ...
```

内部。

原因：

直接执行 retrieval_service.py 时，可以运行测试问题。

其他模块导入 retrieve() 时，不会自动执行这些测试查询。

这为未来 RAG Answer 和 FastAPI 直接复用 retrieve() 做准备。

## 14. Distance 的含义

检索结果提供 distance。

它表示查询向量与候选向量之间的距离。

在常见距离度量下，值越小代表距离越近。

注意：

- distance 不是百分比。
- distance 不直接代表答案正确率。
- Top-K 的第一名不一定包含正确答案。
- 是否真正相关仍需要观察返回正文。

本阶段暂不设置统一的 distance 阈值。

后续可以根据实际知识库查询结果再决定是否加入相关性过滤。

## 15. 真实检索验收

执行：

```bash
python src/retrieval_service.py
```

使用：

- 本地真实 Ollama Embedding。
- 正式 technical_knowledge Collection。
- top_k=3。
- 非 Mock 向量。
- ChromaDB 真实 query()。

### 测试 1：STM32 ACK

问题：

`STM32 如何向网关返回 ACK？`

实际命中与问题相关的：

- Linux Gateway Day 58 ACK 超时及异常 ACK。
- STM32 V2 Day 10 UART LED Command ACK。
- Linux Gateway Day 47 Command ACK。

结论：

检索到真实通信确认机制相关的知识内容。

### 测试 2：MQTT LWT

问题：

`MQTT 的 LWT 有什么作用？`

实际命中：

Linux Gateway Day 50 MQTT LWT 相关文档 Chunk。

结果包含在线状态、离线通知、Last Will 等相关内容。

结论：

能够检索到真实 MQTT LWT 技术资料。

### 测试 3：ChromaDB Metadata

问题：

`为什么 ChromaDB 的 last_updated 要转换成字符串？`

实际命中：

RAG Day 13 ChromaDB 最小向量入库笔记中的 Metadata 类型转换相关内容。

包含：

- PyYAML 日期解析。
- datetime.date。
- ChromaDB Metadata 类型适配。
- metadata.copy()。

结论：

能够检索到 RAG 项目自身的技术学习笔记。

### 验收总结

三组真实问题均成功执行检索并返回 Top-3 结果。

结果包含：

- ID
- Chunk 正文
- Source
- Metadata
- Distance

人工观察结果与测试问题具有明确的主题相关性。

**RAG V1 最小 Top-K Retrieval：Development Verification PASS。**

注意：

这属于三个代表性问题的功能和相关性验证。

尚未建立大规模标准问答集，也没有完成 Recall@K、MRR、nDCG 等量化检索质量评估。

## 16. 本阶段主要 Bug 与经验

### Bug 1：API 参数名称错误

错误：

`question_embeddings`

正确：

`query_embeddings`

经验：

Python 函数的关键字参数名称由被调用的 API 规定，不能按照个人习惯修改。

### Bug 2：查询与结果遍历顺序错误

必须先执行：

```python
results = collection.query(...)
```

然后使用 zip() 遍历 results。

不能在 results 尚未赋值时访问其字段。

### Bug 3：循环中重复覆盖字典

一个 record 字典反复写入不同 Chunk 会覆盖原有字段。

解决方式：

每条结果创建新的字典，加入结果列表。

### Bug 4：返回结构与函数类型标注不一致

函数标注：

```python
-> list[dict]
```

应返回结果列表，而不是直接返回单个 dict。

### 工程经验

业务函数尽量返回结构化数据。

测试输出放在主程序入口，而不是让正式检索函数始终打印大量正文。

## 17. Day 14+15 复习记录

本次在 Retrieval 开发完成后，补做 Day 14+15 的知识追问。

### 断点恢复

理解：

在 Embedding 之前筛选已经入库的 ID，可以避免对已存储 Chunk 重复计算向量。

需要区分：

- 重复检查记录是否存在。
- 重复进行 Embedding 计算。
- 重复调用数据库写入。

三者不是同一个操作。

### enumerate 与数据对齐

对于：

```python
ids = ["A", "B", "C"]
documents = ["正文A", "正文B", "正文C"]
existing_ids = {"B"}
```

正确待处理数据：

```python
pending_ids = ["A", "C"]
pending_documents = ["正文A", "正文C"]
```

Metadata 也必须保持相同的筛选关系。

复习结果：通过。

## 18. 当前真实项目状态

已完成：

- Markdown 文档加载。
- YAML Metadata 解析与校验。
- Document Chunking。
- 单条和批量 Embedding。
- ChromaDB 持久化。
- 正式知识库批量入库。
- 根据已存在 ID 跳过重复 Embedding。
- Question Embedding。
- ChromaDB Top-K query()。
- 结构化检索结果。
- Source 追溯。
- 三组真实问题检索验证。

尚未完成：

- RAG Context Assembly。
- Ollama LLM Answer。
- Answer + Sources。
- FastAPI /query。
- Orange Pi Agent 接入。
- 系统性的检索质量评估。
- 同 ID 文档内容变化后的自动更新机制。

## 19. 下一阶段开发计划

下一阶段：

RAG Answer + Sources。

建议新增正式业务模块：

`src/rag_service.py`

预期调用链：

```text
用户问题
    ↓
retrieve(question, top_k)
    ↓
相关 Chunk 列表
    ↓
Context Assembly
    ↓
Ollama LLM Generate
    ↓
Answer + Sources
```

最小目标：

输入自然语言问题，程序能够：

1. 从真实 ChromaDB 检索相关知识。
2. 将相关 Chunk 组成上下文。
3. 调用 Ollama 语言模型生成答案。
4. 返回答案与文档来源。
5. 对检索不到可靠资料的情况给出合理说明。

之后实现：

FastAPI `/query`

通过 HTTP 将完整问答功能暴露给后续 Orange Pi Agent。

## 20. 本次结论

Day 16+17 完成了真实 Top-K Retrieval 最小功能。

知识库已经能够根据自然语言问题返回相关技术文档 Chunk，并保留 ID、正文、来源和距离。

但当前返回的是检索结果，不是 LLM 生成的最终回答。

**RAG V1 已完成向量知识库入库与基本语义检索，下一阶段进入 RAG Answer。**

备注：本学习笔记自身尚未计入前述 632 条历史数据库快照。保存后可通过现有增量入库程序补录，新增数量以实际运行结果为准。
