---
title: RAG Day 12 Batch Embedding 批量文本向量化
project: 基于 RAG 的个人技术知识库问答服务
system_layer: 知识层 / 文档检索服务
document_type: learning_note
status: completed
last_updated: 2026-09-23
tags: [Python, RAG, Ollama, Embedding, Batch, Qwen3, Validation]
---

# RAG Day 12：Batch Embedding 批量文本向量化

**日期：2026-09-23**

## 1. 今日目标

在 Day 11 已完成单文本 Embedding 的基础上，实现：

```text
多段文本
↓
一次调用 Ollama Embedding API
↓
得到多个向量
```

新增核心函数：

```python
embed_texts(texts: list[str]) -> list[list[float]]
```

Day 11：

```text
str
↓
embed_text()
↓
list[float]
```

Day 12：

```text
list[str]
↓
embed_texts()
↓
list[list[float]]
```

---

## 2. 为什么需要 Batch Embedding

RAG 前面已经完成：

```text
Markdown
↓
Document
↓
Chunks
```

真实知识库不会只有一个 Chunk，而是：

```text
Chunk 0
Chunk 1
Chunk 2
...
Chunk N
```

后续要把所有 Chunk 存入向量数据库，因此需要：

```text
多个 Chunk 文本
↓
多个 Embedding
↓
文本和向量一一对应
```

一种做法是循环调用：

```python
for text in texts:
    embed_text(text)
```

这样意味着：

```text
N 条文本
→ N 次 Ollama 请求
```

Day 12 使用 Ollama 本身支持的 Batch Embedding：

```text
N 条文本
→ 一次 Ollama 请求
→ N 个向量
```

---

## 3. Ollama Batch Embedding 数据流

示例输入：

```python
texts = [
    "STM32 UART recovery",
    "Gateway ACK timeout",
    "RAG batch embedding",
]
```

完整数据流：

```text
texts: list[str]
↓
输入合法性检查
↓
逐条 strip()
↓
cleaned_texts
↓
ollama.embed(
    model=EMBEDDING_MODEL,
    input=cleaned_texts
)
↓
Python ollama 客户端
↓
本机 Ollama Service
127.0.0.1:11434
↓
qwen3-embedding:0.6b
↓
生成多个语义向量
↓
response.embeddings
↓
list[list[float]]
```

---

## 4. Python Ollama / Ollama Service / Embedding Model 的职责

这三个概念不能混在一起。

### Python `ollama` 包

作用：

```text
Python 客户端
```

负责：

```text
Python 程序
↓
向 Ollama Service 发请求
↓
接收 Response
```

它本身不是模型，也不是实际执行模型推理的服务。

---

### Ollama Service

通过：

```bash
ollama serve
```

启动。

看到：

```text
Listening on 127.0.0.1:11434
```

说明本机 Ollama 服务已经运行。

职责：

```text
接收 API 请求
↓
管理 / 加载模型
↓
执行模型推理
↓
返回结果
```

本次运行中 Ollama 成功识别：

```text
NVIDIA GeForce RTX 4060 Laptop GPU
CUDA
```

---

### qwen3-embedding:0.6b

这是实际负责 Embedding 的模型。

作用：

```text
文本
↓
Embedding Model
↓
语义向量
```

当前模型每条文本输出：

```text
1024 维向量
```

---

## 5. Batch Embedding 为什么是二维结构

单文本输入：

```python
input = "STM32 UART"
```

Ollama 的 Embedding API 为了统一支持单文本和批量文本，仍然返回：

```python
[
    [float, float, ...]
]
```

所以：

```python
response.embeddings
```

的数据结构是：

```text
list[list[float]]
```

Day 11 的函数只需要一条文本对应的一个向量，因此：

```python
return embeddings[0]
```

最终得到：

```text
list[float]
```

---

批量文本：

```python
input = [
    "STM32 UART",
    "Gateway MQTT",
    "RAG Embedding",
]
```

返回：

```python
[
    [float, float, ...],   # 第 1 条文本
    [float, float, ...],   # 第 2 条文本
    [float, float, ...],   # 第 3 条文本
]
```

因此 Day 12 不再：

```python
return embeddings[0]
```

而是直接：

```python
return embeddings
```

---

## 6. 外层长度和内层长度

对于：

```python
texts = [
    "A",
    "B",
    "C",
]
```

返回结果可以理解为：

```text
shape ≈ (3, 1024)
```

其中：

```python
len(embeddings) == 3
```

表示：

```text
输入了 3 段文本
↓
应该返回 3 个 Embedding
```

而：

```python
len(embeddings[0]) == 1024
```

表示：

```text
当前 Embedding Model 输出的向量维度为 1024
```

所以必须区分：

```text
外层长度
= 输入文本数量

内层长度
= 每条文本的向量维度
```

这两个数字没有直接关系。

---

## 7. `embed_texts()` 的输入校验

核心接口：

```python
embed_texts(texts: list[str]) -> list[list[float]]
```

输入检查流程：

```text
texts
↓
是不是 list
↓
是不是空 list
↓
每个元素是不是 str
↓
strip 后是不是空字符串
↓
加入 cleaned_texts
```

---

### 7.1 `texts` 不是 list

例如：

```python
embed_texts(123)
```

要求：

```text
list[str]
```

实际输入：

```text
int
```

属于类型错误，因此：

```python
TypeError
```

记忆：

```text
“你给我的东西类型就不对”
```

---

### 7.2 空列表

例如：

```python
embed_texts([])
```

`[]` 本身确实是：

```python
list
```

所以类型正确。

但是业务上：

```text
没有任何文本可以进行 Embedding
```

属于：

```text
类型正确
但是值不合法
```

因此：

```python
ValueError
```

---

### 7.3 list 内部元素不是字符串

例如：

```python
embed_texts([
    "hello",
    123,
])
```

第二个元素要求：

```python
str
```

实际是：

```python
int
```

所以属于：

```python
TypeError
```

---

### 7.4 字符串 strip 后为空

例如：

```python
embed_texts([
    "hello",
    "   ",
])
```

第二个元素本身是：

```python
str
```

所以类型没错。

但是：

```python
"   ".strip()
```

结果为：

```python
""
```

因此属于：

```text
类型正确
但是值不合法
```

所以：

```python
ValueError
```

---

## 8. 为什么创建 `cleaned_texts`

原始输入：

```python
texts = [
    "  STM32 UART  ",
    "Gateway ACK",
]
```

逐条处理：

```python
cleaned_text = text.strip()
```

得到：

```python
cleaned_texts = [
    "STM32 UART",
    "Gateway ACK",
]
```

真正发送给 Ollama：

```python
response = ollama.embed(
    model=EMBEDDING_MODEL,
    input=cleaned_texts
)
```

这样做有几个作用：

1. 去除文本首尾无意义空格；
2. 不直接修改调用者原始 `texts`；
3. 使真正送入模型的数据明确；
4. 后面检查输入数量时，可以直接和真正送入 Ollama 的 `cleaned_texts` 对应。

数据流：

```text
texts
↓
validation
↓
strip
↓
cleaned_texts
↓
Ollama
↓
embeddings
```

---

## 9. 返回结果校验

即使用户输入完全合法，也不能假设 Ollama 的返回永远正确。

因此还需要检查：

```text
embeddings 是否为空
↓
返回数量是否和输入数量相同
↓
每个 embedding 是否为空
```

---

### 9.1 Ollama 没有返回任何 Embedding

例如：

```python
embeddings = []
```

此时调用者的输入已经合法。

问题发生在：

```text
程序实际运行阶段
```

因此应该：

```python
RuntimeError
```

---

### 9.2 返回数量不匹配

例如：

```text
输入 3 条文本
```

正常应该返回：

```text
3 个向量
```

但实际只返回：

```text
2 个向量
```

则：

```python
len(embeddings) != len(cleaned_texts)
```

说明 Batch 结果不完整。

属于运行过程异常：

```python
RuntimeError
```

---

### 9.3 某一个 Embedding 为空

例如：

```python
embeddings = [
    [0.1, 0.2, ...],
    [],
    [0.3, 0.4, ...],
]
```

虽然：

```text
外层数量 == 输入数量
```

但是其中一个向量为空。

因此还需要：

```text
遍历所有 embedding
↓
检查每一个是否为空
```

出现这种情况：

```python
RuntimeError
```

---

## 10. `not embeddings` 和数量检查是否重复

当前函数前面已经保证：

```text
len(cleaned_texts) >= 1
```

如果：

```python
embeddings = []
```

那么：

```python
len(embeddings) != len(cleaned_texts)
```

一定成立。

例如：

```text
0 != 3
```

所以从纯逻辑覆盖来看：

```python
not embeddings
```

和：

```python
len(embeddings) != len(cleaned_texts)
```

确实有部分重复。

但是它们表达的错误语义不同：

```text
not embeddings
→ 一个结果都没有返回

数量不匹配
→ 返回了一部分结果，但是数量不完整
```

工程上可以拆成：

```python
if not embeddings:
    raise RuntimeError("no embeddings returned")

if len(embeddings) != len(cleaned_texts):
    raise RuntimeError("embedding count mismatch")
```

这样错误原因更加清楚。

另外：

```python
if not embeddings:
```

也可以提前防御极端情况下：

```python
embeddings = None
```

避免继续执行：

```python
len(None)
```

产生其他异常。

---

## 11. TypeError / ValueError / RuntimeError 的区别

这是今天重新明确的重要知识点。

### TypeError

表示：

```text
输入的数据类型不符合接口要求
```

例如：

```python
embed_texts(123)
```

或者：

```python
embed_texts([
    "hello",
    123,
])
```

记忆：

```text
“你给我的东西类型就不对”
```

---

### ValueError

表示：

```text
类型本身是正确的
但是这个值不符合要求
```

例如：

```python
embed_texts([])
```

或者：

```python
embed_texts([
    "hello",
    "   ",
])
```

记忆：

```text
“类型是对的，但是这个值不能接受”
```

---

### RuntimeError

表示：

```text
调用者输入已经合法
但是程序运行过程中出现了不应该发生的状态
```

例如：

```text
Ollama 没有返回任何 Embedding

输入 3 条文本
但是只返回 2 个 Embedding

某一个 Embedding 是空列表
```

记忆：

```text
“输入没问题，是程序运行到后面出了问题”
```

---

## 12. 三种异常的判断方法

可以先问：

```text
这个错误发生在输入阶段，
还是程序已经开始正常运行以后？
```

如果是输入阶段：

```text
类型不对
→ TypeError

类型对，但是值不合法
→ ValueError
```

如果输入已经合法，但是运行过程中出现异常状态：

```text
RuntimeError
```

当前 `embed_texts()` 的异常边界：

```text
texts 不是 list
→ TypeError

texts == []
→ ValueError

列表内部元素不是 str
→ TypeError

字符串 strip 后为空
→ ValueError

Ollama 没有返回 embedding
→ RuntimeError

Embedding 数量不一致
→ RuntimeError

其中某个 embedding 为空
→ RuntimeError
```

---

## 13. Batch Embedding 正常测试

测试数据：

```python
texts = [
    "STM32 UART recovery",
    "Gateway ACK timeout",
    "RAG batch embedding",
]
```

调用：

```python
embeddings = embed_texts(texts)
```

需要验证：

```text
embeddings 本身是 list
↓
外层长度 == 3
↓
每个 embedding 都是 list
↓
每个 embedding 长度 == 1024
↓
每一个向量中的元素都是 float
```

实际测试已经通过：

```text
3 条文本
↓
3 个 Embedding

每个 Embedding
↓
1024 维

Embedding 内每个元素
↓
float
```

---

## 14. 两层 `all()` 的理解

数据结构：

```python
embeddings = [
    [float, float, ...],
    [float, float, ...],
    [float, float, ...],
]
```

存在两层：

```text
embeddings
↓
每一个 embedding
↓
每一个 embedding 中的 value
```

检查所有外层元素是不是 list：

```python
assert all(
    isinstance(embedding, list)
    for embedding in embeddings
)
```

检查所有向量长度是否为 1024：

```python
assert all(
    len(embedding) == 1024
    for embedding in embeddings
)
```

检查所有向量中的所有元素是否为 float：

```python
assert all(
    all(
        isinstance(value, float)
        for value in embedding
    )
    for embedding in embeddings
)
```

含义：

```text
对于每一个 embedding
↓
检查其中的每一个 value
↓
所有 value 都必须是 float
↓
所有 embedding 都必须满足这个要求
```

---

## 15. `isinstance(value, float)` 与 `isinstance(type(value), float)`

测试时出现过错误写法：

```python
isinstance(type(value), float)
```

例如：

```python
value = 0.123
```

那么：

```python
type(value)
```

结果是：

```python
<class 'float'>
```

这是：

```text
一个类型对象
```

而不是：

```text
0.123 这个浮点数本身
```

真正应该检查的是：

```python
isinstance(value, float)
```

即：

```text
直接检查 value 自己是不是 float
```

---

## 16. 为什么业务函数里暂时不写死 1024

当前模型：

```text
qwen3-embedding:0.6b
```

输出：

```text
1024 维
```

但是：

```text
Embedding
```

并不天然等于：

```text
1024 维
```

以后如果换其他模型，可能是：

```text
768
1024
1536
其他维度
```

因此目前 `embed_texts()` 的职责是：

```text
输入合法
↓
调用 Ollama
↓
确保返回存在
↓
确保返回数量和输入数量对应
↓
确保每一个向量非空
```

而：

```text
当前选择的 qwen3-embedding:0.6b
是否真的输出 1024 维
```

由测试进行验证：

```python
len(embedding) == 1024
```

这样不会把：

```text
某一个具体模型的特征
```

硬编码到通用业务函数中。

---

## 17. Batch Embedding 异常测试

今天完成了三个输入异常测试。

### 空列表

输入：

```python
embed_texts([])
```

预期：

```python
ValueError
```

实际成功捕获。

---

### 列表内部存在错误类型

输入：

```python
embed_texts([
    "hello",
    123,
])
```

预期：

```python
TypeError
```

实际成功捕获。

---

### 列表内部存在空文本

输入：

```python
embed_texts([
    "hello",
    "",
])
```

或者：

```python
embed_texts([
    "hello",
    "   ",
])
```

预期：

```python
ValueError
```

实际成功捕获。

---

## 18. 为什么异常测试需要 `else`

如果只写：

```python
try:
    embed_texts([])
except ValueError:
    print("success")
```

存在一个问题。

假设未来函数被修改坏了：

```python
embed_texts([])
```

居然没有抛出异常。

那么：

```text
except 不会执行
↓
程序继续往下走
↓
测试可能仍然看起来正常
```

所以应该写：

```text
try
↓
调用一个“应该报错”的函数

except 预期异常
↓
说明测试成功

else
↓
说明本来应该报错但没有报错
↓
主动 AssertionError
```

例如：

```python
try:
    embed_texts([])
except ValueError as error:
    print("成功捕获", error)
else:
    raise AssertionError("空列表应该抛出 ValueError")
```

这样才能真正验证：

```text
预期异常确实发生了
```

---

## 19. Day 12 最终核心数据流

```text
Chunks
↓
取出多个 Chunk 的 content
↓
list[str]
↓
embed_texts()
↓
检查 texts 是否为 list
↓
检查 list 是否为空
↓
检查每个元素是不是 str
↓
strip()
↓
检查是否为空文本
↓
cleaned_texts
↓
一次 ollama.embed()
↓
Python Ollama Client
↓
Ollama Service
↓
qwen3-embedding:0.6b
↓
response.embeddings
↓
检查是否返回结果
↓
检查向量数量是否和输入文本数量一致
↓
检查每一个向量是否为空
↓
list[list[float]]
```

---

## 20. Day 11 → Day 12 的变化

Day 11：

```text
一个文本
↓
一个 Embedding
```

接口：

```python
embed_text(text: str) -> list[float]
```

Day 12：

```text
多个文本
↓
一次 Batch Embedding
↓
多个 Embedding
```

接口：

```python
embed_texts(texts: list[str]) -> list[list[float]]
```

主要变化：

```text
单文本
→ 多文本

str
→ list[str]

一个向量
→ 多个向量

list[float]
→ list[list[float]]

return embeddings[0]
→ return embeddings

检查第一条向量
→ 检查所有向量

1 : 1
→ N : N
```

---

## 21. 今日完成内容

RAG Day 12 已完成：

- [x] 复习 Day 11 单文本 Embedding
- [x] 重新理解 Python Ollama Client / Ollama Service / Embedding Model
- [x] 确认本机 Ollama Service 正常启动
- [x] 确认 RTX 4060 / CUDA 被 Ollama 识别
- [x] 理解 1024 维 Embedding 的含义
- [x] 区分外层文本数量与内层向量维度
- [x] 实现 `embed_texts()`
- [x] 使用 `cleaned_texts`
- [x] 使用一次 `ollama.embed()` 完成 Batch Embedding
- [x] 检查 Embedding 返回是否为空
- [x] 检查 Embedding 返回数量
- [x] 检查每一个 Embedding 是否为空
- [x] 区分 TypeError / ValueError / RuntimeError
- [x] 完成 3 条文本 Batch Embedding 实测
- [x] 验证返回 3 个 Embedding
- [x] 验证每条 Embedding 长度为 1024
- [x] 验证所有向量元素均为 float
- [x] 完成空列表异常测试
- [x] 完成列表元素类型异常测试
- [x] 完成列表内部空文本异常测试
- [x] 为异常测试加入 `else -> AssertionError`

---

## 22. 当前 RAG 项目进度

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

ChromaDB
← 下一阶段

Vector Retrieval
未开始

LLM Answer
未开始

FastAPI
未开始
```

---

## 23. 下一学习日

下一次进入：

```text
RAG Day 13
ChromaDB 最小向量入库
```

开始把：

```text
Chunk
+
Embedding
+
Metadata
```

真正组合成可以存入向量数据库的数据。

后续主链路：

```text
Markdown
↓
Document
↓
Chunk
↓
Batch Embedding
↓
ChromaDB
↓
Question Embedding
↓
Top-K Retrieval
↓
LLM Answer
↓
FastAPI /query
↓
Orange Pi 调用
```

当项目推进到：

```text
FastAPI /query
```

阶段时，需要提醒购买香橙派。
