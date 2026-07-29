---
title: RAG Day 11 Ollama 环境与单文本 Embedding
project: 基于 RAG 的个人技术知识库问答服务
system_layer: 知识层 / 文档检索服务
document_type: learning_note
status: completed
last_updated: 2026-07-29
tags: [Python, RAG, Ollama, Embedding, Qwen3, GPU, Validation]
---

# RAG Day 11 Ollama 环境与单文本 Embedding

## 今日目标

完成 RAG 数据管线中从文本到向量的第一步：

```text
文本 str
→ Python Ollama 客户端
→ Ollama 本地服务
→ qwen3-embedding:0.6b
→ 1024 维 list[float]
```

今天只实现：

```text
单条文本
→ 单条 Embedding 向量
```

暂时不处理：

- 批量 Chunk 向量化；
- ChromaDB；
- 相似度检索；
- 大模型回答；
- FastAPI 接口。

## 当前 RAG 数据流

Day 10 以前已经完成：

```text
docs_raw/*.md
→ Markdown Loader
→ YAML 与正文分离
→ Metadata 校验
→ Document
→ Chunk
```

Day 11 新增：

```text
Chunk content
→ Embedding 模型
→ 数字向量
```

当前完整进度：

```text
Markdown
→ Document
→ Chunk
→ Embedding
```

后续还需要：

```text
Embedding
→ ChromaDB
→ 相似度检索
→ Prompt
→ Ollama 生成模型
→ Answer + Sources
→ FastAPI
```

## 什么是 Embedding

Embedding 用于将文本转换为一组浮点数。

输入示例：

```text
STM32 使用 USART2 接收 Linux 网关下发的控制命令
```

输出概念结构：

```python
[
    -0.0394205,
    -0.035325445,
    -0.009807585,
    -0.12905098,
    0.023100521,
    ...
]
```

这组浮点数表示文本在高维语义空间中的位置。

Embedding 不是：

- 原文；
- 摘要；
- 关键词列表；
- 文本的加密结果。

Embedding 的主要用途是进行语义相似度比较。

例如：

```text
“STM32 串口接收控制命令”
与
“USART2 接收 Linux 下发指令”
```

两段文本虽然字面不同，但语义相近，因此它们的向量通常也比较接近。

## Ollama、模型和 Python 包的区别

### Ollama

Ollama 是本地模型运行器和 API 服务。

职责：

```text
加载本地模型
→ 调用 CPU 或 GPU 计算
→ 接收 API 请求
→ 返回向量或模型输出
```

Ollama 默认监听：

```text
127.0.0.1:11434
```

启动命令：

```bash
ollama serve
```

### qwen3-embedding:0.6b

这是实际执行文本向量计算的 Embedding 模型。

职责：

```text
文本
→ 语义向量
```

本次模型输出长度为：

```text
1024
```

### Python ollama 包

Python 已经是编程语言和解释器，但默认不知道如何调用 Ollama 服务。

安装：

```bash
python -m pip install ollama
```

之后可以在代码中：

```python
import ollama
```

Python 包负责：

```text
Python 代码
→ 向 Ollama 服务发送请求
→ 接收 Ollama 返回的数据
```

它不是重新安装 Python，也不是直接在 Python 内部运行模型。

## 实际调用链路

```text
embedding_service.py
→ ollama.embed()
→ HTTP 请求 localhost:11434
→ Ollama 服务
→ qwen3-embedding:0.6b
→ RTX 4060 执行推理
→ 返回 embeddings
→ Python 取得第一条向量
```

## 环境安装结果

已经完成：

```text
✓ 安装 Ollama
✓ Ollama 命令位于 /usr/bin/ollama
✓ Ollama 服务成功监听 127.0.0.1:11434
✓ Ollama 成功识别 RTX 4060 Laptop GPU
✓ 安装 Python ollama 客户端
✓ 拉取 qwen3-embedding:0.6b
✓ ollama list 能正确显示模型
```

模型检查：

```bash
ollama list
```

结果包含：

```text
qwen3-embedding:0.6b
```

## Ollama 服务与客户端

一个终端运行：

```bash
ollama serve
```

该终端负责保持本地服务运行。

另一个终端进入项目：

```bash
cd ~/projects/rag-technical-knowledge-service
source .venv/bin/activate
```

然后运行 Python 代码或测试。

如果 Ollama 服务没有启动，Python 调用可能出现连接错误。

## embedding_service.py

文件：

```text
src/embedding_service.py
```

接口：

```python
def embed_text(text: str) -> list[float]:
```

输入：

```text
text
→ str
→ 需要转换成向量的文本
```

输出：

```text
list[float]
→ 一条文本对应的完整向量
```

## 模型名称常量

模型名称定义为常量：

```python
EMBEDDING_MODEL = "qwen3-embedding:0.6b"
```

这样做的好处：

- 避免在多个位置重复硬编码；
- 修改模型时只改一个位置；
- 便于后续将模型名移入配置文件；
- 减少拼写错误。

## 参数校验顺序

函数先检查：

```text
text 是否为 str
```

然后才调用：

```python
text.strip()
```

原因是整数等类型没有 `strip()` 方法。

错误顺序：

```python
text = text.strip()
→ 输入 123
→ AttributeError
```

正确顺序：

```text
isinstance(text, str)
→ 类型合法后再 strip()
```

非字符串输入抛出：

```text
TypeError
```

## 空文本检查

```python
text = text.strip()
```

会去除首尾空格。

因此：

```python
"   "
```

处理后变成：

```python
""
```

空文本抛出：

```text
ValueError
```

这样既能拒绝空字符串，也能拒绝只包含空格的字符串。

## 调用 Ollama Embed API

调用形式：

```python
response = ollama.embed(
    model=EMBEDDING_MODEL,
    input=text,
)
```

参数含义：

```text
model
→ 使用哪个 Embedding 模型

input
→ 需要向量化的文本
```

返回对象中的：

```python
response.embeddings
```

是二维向量列表。

## 为什么 embeddings 是二维列表

Ollama 同时支持单条和多条文本输入。

单条输入概念返回：

```python
[
    [
        0.01,
        -0.02,
        0.03,
        ...
    ]
]
```

外层列表表示：

```text
输入了多少条文本
```

内层列表表示：

```text
一条文本对应的完整向量
```

因此：

```python
embeddings
```

类型是：

```text
list[list[float]]
```

而：

```python
embeddings[0]
```

类型是：

```text
list[float]
```

当前函数只接收一条文本，因此最终返回：

```python
embeddings[0]
```

## 空向量检查

代码逻辑：

```python
if not embeddings or not embeddings[0]:
    raise RuntimeError(...)
```

### not embeddings

当：

```python
embeddings = []
```

空列表在布尔判断中等价于：

```text
False
```

所以：

```python
not embeddings
```

结果为：

```text
True
```

表示 Ollama 没有返回任何向量。

### not embeddings[0]

当：

```python
embeddings = [[]]
```

外层列表有一个元素，但第一条向量为空。

所以：

```python
not embeddings[0]
```

结果为：

```text
True
```

### 为什么使用 or

```python
if not embeddings or not embeddings[0]:
```

表示：

```text
外层列表为空
或者
第一条向量为空
→ 都属于无效返回
```

Python 的 `or` 具有短路特性。

当外层列表为空时：

```python
not embeddings
```

已经为 `True`，Python 不会继续访问：

```python
embeddings[0]
```

因此可以避免：

```text
IndexError
```

## 异常类型

当前函数约定：

```text
非字符串
→ TypeError

空字符串或全空格
→ ValueError

模型没有返回有效向量
→ RuntimeError
```

正常输入：

```text
→ 返回 list[float]
```

使用异常而不是打印后返回 `None`，可以让调用者明确知道失败原因。

## 当前函数数据流

```text
接收 text
→ 检查是否为 str
→ strip()
→ 检查是否为空
→ ollama.embed()
→ 取得 response.embeddings
→ 检查外层列表
→ 检查第一条向量
→ 返回 embeddings[0]
```

## test_embedding.py

测试文件：

```text
src/test_embedding.py
```

真实测试文本：

```text
STM32 使用 USART2 接收 Linux 网关下发的控制命令
```

测试内容：

```text
✓ 返回类型是否为 list
✓ 向量长度是否为 1024
✓ 每个元素是否为 float
✓ 向量是否非空
✓ 空文本是否抛出 ValueError
✓ 非字符串是否抛出 TypeError
```

## assert embedding

非空列表在布尔判断中为：

```text
True
```

因此：

```python
assert embedding
```

表示：

```text
向量必须非空
```

错误写法：

```python
assert not embedding
```

该写法表示：

```text
只有向量为空时才通过
```

会与预期相反。

## all() 检查元素类型

```python
assert all(
    isinstance(value, float)
    for value in embedding
)
```

含义：

```text
遍历向量中的每个元素
→ 检查是否为 float
→ 所有元素都满足才返回 True
```

## 测试文件位置问题

测试文件曾被错误创建在：

```text
src/__pycache__/test_embedding.py
```

`__pycache__` 用于保存 Python 自动生成的字节码缓存，不应存放源码。

正确路径：

```text
src/test_embedding.py
```

从项目根目录运行：

```bash
python src/test_embedding.py
```

如果当前目录已经进入 `src/`，则运行：

```bash
python test_embedding.py
```

不能在 `src/` 中再次写：

```bash
python src/test_embedding.py
```

否则会寻找：

```text
src/src/test_embedding.py
```

## 实际运行结果

输出：

```text
向量类型：<class 'list'>
向量长度：1024
前五个元素：[-0.0394205, -0.035325445, -0.009807585, -0.12905098, 0.023100521]
成功捕获空文本：text can not be empty
成功捕获错误类型：text type error
```

Ollama 服务端返回：

```text
POST /api/embed
HTTP 200
```

说明：

```text
Python 客户端成功访问 Ollama
→ Ollama 成功加载模型
→ GPU 完成向量计算
→ Python 成功取得向量
```

## 首次调用为什么较慢

第一次调用模型时，Ollama 需要：

```text
从磁盘加载模型
→ 分配内存和显存
→ 初始化推理环境
→ 执行第一次计算
```

因此首次调用可能需要十几秒或更长。

后续调用模型仍在内存中时，速度通常明显更快。

## 当前已完成能力

```text
[x] Markdown 文件读取
[x] YAML Front Matter 解析
[x] Metadata 校验
[x] 目录批量加载
[x] Document 结构
[x] 单 Document 切分
[x] 多 Documents 批量切分
[x] 真实知识库 Chunk 统计
[x] Ollama 本地环境
[x] Embedding 模型
[x] 单文本向量化
[x] 单文本 Embedding 测试
[ ] 批量 Chunk 向量化
[ ] ChromaDB
[ ] Top-K 相似度检索
[ ] Ollama 生成式模型
[ ] Prompt 构造
[ ] 来源返回
[ ] FastAPI
```

## 当前边界

Day 11 已经证明：

```text
一段文本
→ 能生成一条有效的 1024 维向量
```

尚未证明：

- 所有 Chunk 都能成功生成向量；
- Chunk 数量与向量数量一致；
- 不同文本的向量维度始终一致；
- 语义相近文本的向量距离更近；
- 向量能够写入 ChromaDB；
- 查询能够找回相关 Chunk。

## 面试表达

我在本地 WSL 环境中安装并运行 Ollama，拉取了 `qwen3-embedding:0.6b` 模型，并通过 Python 官方客户端调用本地 Embed API。

我封装了 `embed_text()` 函数，输入一条字符串，先进行类型和空文本校验，再调用 Ollama 生成向量。由于 Ollama 的接口统一支持批量输入，所以返回的 `embeddings` 是二维列表，单文本函数最终返回 `embeddings[0]`。

我还验证了返回结果为非空 `list[float]`、长度为 1024，并测试了空文本和错误类型的异常分支。

当前已经完成从单条 Chunk 正文到 Embedding 向量的最小闭环，下一步将实现批量 Chunk 向量化。

## 下一步

RAG Day 12：

```text
多个 Chunks
→ 提取每个 chunk["content"]
→ 批量调用 Embedding
→ 返回多条向量
→ 验证向量数量等于 Chunk 数量
→ 验证所有向量维度一致
```

随后进入：

```text
Chunk
+
Embedding
+
Metadata
→ ChromaDB
```
