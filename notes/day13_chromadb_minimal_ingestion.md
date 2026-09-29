---
title: RAG Day 13 ChromaDB 最小向量入库
project: 基于 RAG 的个人技术知识库问答服务
system_layer: 知识层 / 文档检索服务
document_type: learning_note
status: completed
last_updated: 2026-09-29
tags: [Python, RAG, ChromaDB, Vector Database, Embedding, Batch, Persistence, Metadata]
---

# RAG Day 13：ChromaDB 最小向量入库

**日期：2026-09-29**

## 1. 今日目标

在 Day 12 已完成 Batch Embedding 的基础上，第一次把：

```text
Chunk
+
Embedding
+
Metadata
+
唯一 ID
↓
ChromaDB
```

形成真实的持久化向量记录。

今日重点不是 Retrieval，而是先完成：

```text
创建本地持久化数据库
↓
创建 Collection
↓
Record add()
↓
Record get()
↓
真实 Chunk 入库
↓
真实文档 Batch 入库
↓
读回验证
```

今日暂不实现：

```text
Top-K Retrieval
Question Embedding
RAG Answer
FastAPI /query
Orange Pi 接入
```

---

## 2. ChromaDB 环境准备

项目虚拟环境最开始没有 ChromaDB：

```text
ModuleNotFoundError:
No module named 'chromadb'
```

安装：

```bash
pip install chromadb
```

验证：

```bash
python -c "import chromadb; print(chromadb.__version__)"
```

实际版本：

```text
1.5.9
```

同时确认：

```python
chromadb.PersistentClient
```

在当前版本中可以正常使用。

---

## 3. 为什么安装 ChromaDB 后突然增加很多依赖

安装：

```text
chromadb
```

并不代表只安装一个 Python 包。

真实关系是：

```text
项目
↓
直接依赖 chromadb
↓
chromadb 自己依赖其他包
↓
这些包可能继续依赖其他包
```

例如出现：

```text
aiohttp
grpcio
flatbuffers
click
filelock
fsspec
...
```

这些多数属于：

```text
Transitive Dependencies
间接依赖 / 传递依赖
```

而不是本项目主动选择的核心技术栈。

当前需要重点理解的直接依赖仍然是：

```text
PyYAML
→ YAML Metadata

ollama
→ 本地 Embedding 模型调用

chromadb
→ 向量数据库
```

`pip freeze` 的意义：

```text
记录当前虚拟环境中所有已安装包及其版本
```

因此：

```bash
pip freeze > requirements.txt
```

会把直接依赖和间接依赖一起记录进去。

本项目现阶段继续沿用已有的 full-freeze `requirements.txt` 风格，暂不重构依赖管理。

---

## 4. ChromaDB 本地持久化

创建：

```python
chromadb.PersistentClient(
    path="data/chroma"
)
```

这里：

```text
PersistentClient
→ 本地持久化 ChromaDB Client

path="data/chroma"
→ ChromaDB 数据保存位置
```

第一次运行后实际生成：

```text
data/chroma/
└── chroma.sqlite3
```

因此数据不是只存在 Python 内存中。

数据流：

```text
程序运行
↓
PersistentClient
↓
data/chroma
↓
磁盘持久化

程序退出
↓
数据仍然存在

下次启动
↓
仍然可以重新读取
```

---

## 5. ChromaDB 数据目录不提交 Git

`data/chroma/` 属于：

```text
程序运行产生的本地数据库
```

不是源码。

因此 `.gitignore` 增加：

```gitignore
# ChromaDB local persistent data
data/chroma/
```

验证：

```bash
git status --short
```

没有出现：

```text
?? data/chroma/
```

说明忽略规则生效。

当前边界：

```text
src/vector_store.py
→ 源码
→ Git 跟踪

requirements.txt
→ 依赖环境
→ Git 跟踪

.gitignore
→ 工程配置
→ Git 跟踪

data/chroma/
→ 本地向量数据库
→ Git 忽略
```

---

## 6. PersistentClient / Collection / Record

今日建立三个核心概念。

### PersistentClient

表示：

```text
本地 ChromaDB 数据库 Client
```

负责连接和管理：

```text
data/chroma/
```

---

### Collection

Collection 是 ChromaDB 中一个逻辑数据集合。

例如：

```text
technical_knowledge
day13_test
day13_real_test
day13_batch_test
```

这些 Collection 可以位于同一个：

```text
data/chroma/
```

数据库实例中。

Collection 并不是简单地对应：

```text
data/chroma/<collection_name>/
```

底层存储结构由 ChromaDB 自己管理。

---

### Record

一条 ChromaDB Record 当前使用四个核心字段：

```text
id
document
embedding
metadata
```

对应本项目：

```text
id
→ Chunk 唯一 ID

document
→ Chunk 正文 content

embedding
→ Chunk 对应的语义向量

metadata
→ Chunk metadata
```

完整关系：

```text
Chunk
├── content
└── metadata

        +

Embedding

        +

Unique ID

        ↓

ChromaDB Record
```

---

## 7. Collection 创建函数

实现了 Collection 获取 / 创建入口。

职责：

```text
collection_name
↓
PersistentClient
↓
get_or_create_collection()
↓
Collection
```

Collection 名由调用者传入，而不是在函数中永久写死。

这样可以区分：

```text
day13_real_test
→ 单真实 Chunk 测试

day13_batch_test
→ 整篇真实文档 Batch 测试

technical_knowledge
→ 后续正式知识库 Collection
```

今日真实测试没有把实验数据写入正式：

```text
technical_knowledge
```

Collection。

---

## 8. 今日 Debug：`.` 与 `_`

最开始误写：

```python
chromadb_PersistentClient
```

Python 把它识别成：

```text
一个完整变量名
```

因此产生：

```text
NameError
```

正确写法：

```python
chromadb.PersistentClient
```

其中：

```text
.
→ 对模块 / 对象进行属性访问
```

这与：

```python
response.embeddings
```

属于相同 Python 语法。

---

## 9. 今日 Debug：AttributeError

测试中误写：

```python
client.get_or_create_collention(...)
```

实际方法：

```python
client.get_or_create_collection(...)
```

因此得到：

```text
AttributeError
```

这次进一步明确：

```text
NameError
→ 名字本身没有定义

AttributeError
→ 对象存在，但对象没有访问的这个属性 / 方法
```

---

## 10. ChromaDB `add()` 是 Batch API

测试 Record 使用：

```text
id:
test_001

document:
STM32 uses UART for communication.

embedding:
[0.1, 0.2, 0.3]

metadata:
source = day13_test
chunk_index = 0
```

但 `collection.add()` 本身是批量接口，因此参数结构为：

```text
ids
→ list[str]

documents
→ list[str]

embeddings
→ list[list[float]]

metadatas
→ list[dict]
```

即使只有一条数据，也需要：

```text
1 个 ID
1 个 document
1 个 embedding
1 个 metadata
```

外层仍然保持 Batch 结构。

---

## 11. 单条假 Record add / get 验证

使用独立测试 Collection 完成：

```text
add()
↓
磁盘持久化
↓
get()
↓
成功读回
```

成功读回：

```text
id
→ test_001

document
→ STM32 uses UART for communication.

embedding
→ [0.1, 0.2, 0.3]

metadata
→ source = day13_test
→ chunk_index = 0
```

证明：

```text
PersistentClient
Collection
add()
get()
```

最小闭环工作正常。

---

## 12. `add()` 与 `get()` 的职责

当前理解：

```text
collection.add()
→ 向 Collection 写入 Record

collection.get()
→ 根据 ID 等条件直接读取已存 Record
```

需要特别区分：

```text
get()
≠
向量相似度检索
```

今天的：

```python
collection.get(...)
```

只是验证：

```text
刚才写入的数据能否正确读回来
```

未来真正的语义检索会使用：

```text
query()
```

但 Day 13 尚未进入 Retrieval。

---

## 13. Chunk 唯一 ID

不能只使用：

```text
chunk_0
```

因为多个文档都会存在：

```text
chunk_index = 0
```

例如：

```text
document A → chunk_0
document B → chunk_0
document C → chunk_0
```

因此当前 V1 使用：

```text
source + chunk_index
```

构造唯一 ID。

实现的数据结构：

```text
docs_raw/a.md::chunk_0
docs_raw/a.md::chunk_1
docs_raw/b.md::chunk_0
```

当前函数：

```python
build_chunk_id(chunk: dict) -> str
```

从：

```text
chunk["metadata"]["source"]
chunk["metadata"]["chunk_index"]
```

构建稳定 ID。

真实测试结果：

```text
docs_raw/linux_gateway_day60_full_system_integration.md::chunk_0
```

---

## 14. Chroma Metadata 边界转换

真实 Chunk metadata 中：

```text
last_updated
```

经过 PyYAML 后并不是字符串，而是：

```python
datetime.date
```

真实结果：

```text
before value:
2026-08-11

before type:
<class 'datetime.date'>
```

而 ChromaDB metadata 应使用稳定的基础数据类型。

因此实现：

```python
prepare_metadata_for_chroma(metadata: dict) -> dict
```

数据流：

```text
原 metadata
↓
metadata.copy()
↓
读取 last_updated
↓
如果不是 str
↓
str(last_updated)
↓
返回新的 metadata
```

实际转换：

```text
before:
datetime.date(2026, 8, 11)

after:
"2026-08-11"
```

类型：

```text
datetime.date
↓
str
```

---

## 15. 为什么使用 `metadata.copy()`

不能直接在：

```python
chunk["metadata"]
```

上修改：

```text
last_updated
```

因为 ChromaDB 只是其中一个下游。

原始 Chunk metadata 仍然属于项目自己的数据结构。

因此：

```python
metadata_copy = metadata.copy()
```

让：

```text
原始 Chunk metadata
```

保持不变，而：

```text
Chroma metadata
```

可以进行数据库适配。

---

## 16. 第一条真实 Chunk 数据流

选择真实知识文档：

```text
docs_raw/linux_gateway_day60_full_system_integration.md
```

使用：

```text
chunk_size = 500
chunk_overlap = 100
```

数据流：

```text
真实 Markdown
↓
load_markdown()
↓
Document
↓
split_document()
↓
chunks[0]
↓
build_chunk_id()
↓
prepare_metadata_for_chroma()
↓
embed_text()
↓
1024 维真实 Embedding
```

真实 Chunk：

```text
source:
docs_raw/linux_gateway_day60_full_system_integration.md

chunk_index:
0
```

真实 ID：

```text
docs_raw/linux_gateway_day60_full_system_integration.md::chunk_0
```

真实 Embedding：

```text
type:
<class 'list'>

length:
1024
```

---

## 17. 不打印完整 1024 维向量

真实：

```python
embed_text(...)
```

返回：

```text
list[float]
```

长度：

```text
1024
```

如果：

```python
print(embedding)
```

会把 1024 个浮点数全部输出到终端。

实际 Debug 时只需要检查：

```text
类型
长度
前几个元素
```

例如：

```text
embedding type
embedding length
embedding first 5
```

因为 Embedding 单个坐标本身通常没有人类直接可读的语义。

真正重要的是：

```text
完整向量之间的距离 / 相似度
```

---

## 18. 第一条真实 Chunk ChromaDB 入库

为了不污染正式：

```text
technical_knowledge
```

使用独立 Collection：

```text
day13_real_test
```

真实写入：

```text
ID
→ docs_raw/linux_gateway_day60_full_system_integration.md::chunk_0

document
→ Day60 第 0 个真实 Chunk 正文

embedding
→ qwen3-embedding:0.6b 生成的 1024 维向量

metadata
→ Day60 Chunk metadata
```

成功读回后验证：

```text
id:
docs_raw/linux_gateway_day60_full_system_integration.md::chunk_0

source:
docs_raw/linux_gateway_day60_full_system_integration.md

chunk_index:
0

embedding count:
1

embedding length:
1024
```

证明真实单 Chunk：

```text
Loader
→ Chunker
→ Metadata Adapter
→ Ollama Embedding
→ ChromaDB
```

完整打通。

---

## 19. Batch Record 数据准备

为了批量处理整篇真实文档，实现：

```python
prepare_document_records(path: str)
```

职责：

```text
load Markdown
↓
split_document()
↓
遍历所有 chunks

每个 Chunk：
├── build_chunk_id()
│   ↓
│   ids.append(...)
│
├── content
│   ↓
│   documents.append(...)
│
└── metadata
    ↓
    prepare_metadata_for_chroma()
    ↓
    metadatas.append(...)

循环结束
↓
embed_texts(documents)
↓
embeddings
```

最后返回：

```text
ids
documents
metadatas
embeddings
```

---

## 20. 为什么不在 `for` 循环中逐条 `add()`

一种实现方式是：

```text
Chunk 0
→ embed
→ add

Chunk 1
→ embed
→ add

Chunk 2
→ embed
→ add
```

功能上并非绝对错误。

但这样意味着：

```text
N 个 Chunk
→ N 次 Embedding 请求
→ N 次数据库 add
```

当前项目已经实现：

```python
embed_texts()
```

而 ChromaDB 的：

```python
collection.add()
```

本身也支持 Batch。

因此当前更合理的数据流：

```text
N 个 Chunk
↓
循环构建 ids / documents / metadatas
↓
一次 embed_texts(documents)
↓
N 个 embeddings
↓
一次 collection.add()
```

这也把此前各阶段串起来：

```text
split_document()
→ Batch Chunk

embed_texts()
→ Batch Embedding

collection.add()
→ Batch Vector Record
```

---

## 21. Batch 数据必须严格 N:N:N:N 对齐

对于每一个 Chunk：

```text
Chunk 0
├── ids[0]
├── documents[0]
├── metadatas[0]
└── embeddings[0]

Chunk 1
├── ids[1]
├── documents[1]
├── metadatas[1]
└── embeddings[1]
```

因此必须保证：

```python
len(ids)
==
len(documents)
==
len(metadatas)
==
len(embeddings)
==
len(chunks)
```

否则：

```text
ID
正文
Metadata
向量
```

可能发生错位。

---

## 22. Day60 Batch 数据实测

真实 Day60 文档经过：

```text
chunk_size = 500
chunk_overlap = 100
```

后：

```text
chunks count:
22
```

Batch 数据准备结果：

```text
chunks count:      22
ids count:         22
documents count:   22
metadatas count:   22
embeddings count:  22
```

第一个：

```text
first id:
docs_raw/linux_gateway_day60_full_system_integration.md::chunk_0

first source:
docs_raw/linux_gateway_day60_full_system_integration.md

first chunk_index:
0

first embedding length:
1024
```

说明：

```text
22 : 22 : 22 : 22
```

结构对齐成立。

---

## 23. 整篇真实文档 Batch ChromaDB 入库

使用新的独立测试 Collection：

```text
day13_batch_test
```

避免和：

```text
day13_real_test
technical_knowledge
```

混淆。

执行：

```text
prepare_document_records()
↓
22 IDs
22 Documents
22 Metadatas
22 Embeddings
↓
一次 collection.add()
```

实际：

```text
collection.count()
→ 22
```

证明整篇 Day60 文档的 22 个真实 Chunk 已一次 Batch 写入测试 Collection。

---

## 24. Batch 入库后真实读回验证

从：

```text
day13_batch_test
```

中指定读取：

```text
chunk_0
```

实际结果：

```text
stored count:
22

id:
docs_raw/linux_gateway_day60_full_system_integration.md::chunk_0

document preview:
# Linux-STM32 物联网边缘网关 — Day 60
...

source:
docs_raw/linux_gateway_day60_full_system_integration.md

chunk_index:
0

embedding length:
1024
```

证明经过一次 Batch `add()` 后：

```text
ids[0]
documents[0]
metadatas[0]
embeddings[0]
```

仍然正确对应同一个 Chunk。

---

## 25. 当前 `vector_store.py` 形成的核心职责

当前主要函数职责：

```text
create_chromadb(collection_name)
→ 创建 / 获取指定 Collection

build_chunk_id(chunk)
→ 根据 source + chunk_index 创建唯一 ID

prepare_metadata_for_chroma(metadata)
→ 将项目 metadata 转为 Chroma 可稳定存储格式

prepare_document_records(path)
→ Markdown → Chunks → IDs/Documents/Metadata/Embeddings

add_real_chunks()
→ 将整篇真实文档 Batch 写入测试 Collection
```

职责开始从：

```text
所有逻辑混在一起
```

拆分为：

```text
数据读取
数据切分
ID 生成
Metadata 转换
Embedding
Record 准备
数据库持久化
```

---

## 26. `if __name__ == "__main__"` 的作用

数据库写入函数不应该直接放在模块顶层执行。

使用：

```python
if __name__ == "__main__":
    ...
```

可以保证：

```text
直接运行 vector_store.py
→ 执行测试入口

其他文件 import vector_store
→ 不自动执行数据库写入
```

这对：

```text
有副作用的数据库操作
```

尤其重要。

---

## 27. 今日真实完成边界

今日已经完成：

```text
ChromaDB 安装
✅

PersistentClient
✅

本地磁盘持久化
✅

Collection 创建
✅

单条假 Record add/get
✅

Chunk 唯一 ID
✅

Metadata Chroma 适配
✅

真实单 Chunk 1024维 Embedding
✅

真实单 Chunk ChromaDB add/get
✅

真实整篇 Markdown → 22 Chunks
✅

22 Chunks Batch Embedding
✅

22 条 Batch ChromaDB add
✅

Batch 写入后读回验证
✅
```

但需要严格区分：

```text
以上真实数据目前主要写入独立测试 Collection：
day13_real_test
day13_batch_test
```

正式：

```text
technical_knowledge
```

Collection 尚未执行完整知识库批量灌入。

因此不能写成：

```text
“整个知识库已经完成向量数据库构建”
```

更准确的是：

```text
ChromaDB 最小持久化、单 Chunk 真实入库以及单文档 Batch 入库链路已验证。
```

---

## 28. 当前 RAG 项目数据流

目前真实完成：

```text
Markdown
↓
Loader
↓
Document
↓
Metadata Validation
↓
Chunking
↓
Batch Chunks
↓
Batch Embedding
↓
ChromaDB Record Preparation
↓
ChromaDB Persistent Storage
```

下一阶段才是：

```text
Question
↓
Question Embedding
↓
ChromaDB Vector Query
↓
Top-K Chunks
```

---

## 29. Day 13 与 Day 12 的关系

Day 12 完成：

```text
list[str]
↓
embed_texts()
↓
list[list[float]]
```

Day 13 第一次真实使用：

```text
多个 Chunk content
↓
documents
↓
embed_texts(documents)
↓
embeddings
↓
collection.add()
```

因此 Day 12 的 Batch Embedding 不再只是独立测试，而是进入真实 RAG 数据管线。

---

## 30. 今日关键工程理解

### 1. Vector Database 不只是保存向量

Record 同时需要：

```text
ID
Document
Embedding
Metadata
```

这样未来检索到向量时才能同时拿回：

```text
原始文本
来源
Chunk 位置
其他 Metadata
```

---

### 2. Metadata 存在系统边界

项目自己的：

```text
Python Metadata
```

不一定能直接进入：

```text
数据库 Metadata
```

因此需要：

```text
prepare_metadata_for_chroma()
```

作为边界转换层。

---

### 3. Batch 不只是性能优化

Batch 处理还要求保持：

```text
ids
documents
metadatas
embeddings
```

严格顺序对齐。

否则即使每个数组单独看都正确，也可能把错误向量关联到错误正文。

---

### 4. 正式数据和测试数据要隔离

今日分别使用测试 Collection：

```text
day13_test
day13_real_test
day13_batch_test
```

目的：

```text
测试失败
↓
只污染测试 Collection

technical_knowledge
↓
保持正式数据边界
```

---

## 31. 当前尚未完成

截至 Day 13 结束：

```text
正式 technical_knowledge 全知识库批量入库
未完成

Top-K Vector Retrieval
未完成

Question Embedding → Retrieval
未完成

RAG LLM Answer
未完成

Answer + Sources
未完成

FastAPI /query
未完成

Orange Pi Agent 接入
未完成
```

---

## 32. 当前项目进度

```text
Markdown Loader
✓

YAML Front Matter
✓

Metadata Validation
✓

Document
✓

Fixed-size Chunking
✓

Batch Chunking
✓

真实知识库 Chunk 统计
✓

Single-text Embedding
✓ Day 11

Batch Embedding
✓ Day 12

ChromaDB PersistentClient
✓ Day 13

ChromaDB Record add/get
✓ Day 13

真实单 Chunk 向量入库
✓ Day 13

单真实文档 Batch 向量入库
✓ Day 13

正式全知识库向量入库
未完成

Top-K Retrieval
← 后续阶段

RAG Answer
未开始

FastAPI
未开始
```

---

## 33. 下一学习日

下一学习日开始前仍按固定规则：

```text
先闭卷复习 Day 13
↓
检查遗忘点
↓
必要时开卷恢复
↓
再进入新内容
```

重点复习：

```text
PersistentClient / Collection / Record

add() 与 get() 的区别

id / document / embedding / metadata 的职责

source + chunk_index 为什么可以形成当前 V1 Chunk ID

为什么 last_updated 要做 Chroma Metadata 转换

为什么 Batch 需要 N:N:N:N 对齐

为什么 embeddings=embeddings，
而不是 embeddings=[embeddings]

为什么测试 Collection 和正式 Collection 要隔离
```

下一阶段开始进入：

```text
Vector Retrieval
```

预计核心数据流：

```text
Question
↓
Question Embedding
↓
ChromaDB query
↓
Top-K Relevant Chunks
```

在 Retrieval 完成前，不宣称已经形成完整 RAG 问答。
