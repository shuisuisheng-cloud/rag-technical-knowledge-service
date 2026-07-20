---
title: RAG Day 9 批量 Document 切分
project: 基于 RAG 的个人技术知识库问答服务
system_layer: 知识层 / 文档检索服务
document_type: learning_note
status: completed
last_updated: 2026-07-18
tags: [Python, RAG, Chunking, BatchProcessing, Metadata, Testing]
---

# RAG Day 9 批量 Document 切分

## 今日目标

Day 8 已经实现：

```text
一个 Document
→ split_document()
→ 多个 Chunk
```

Day 9 需要实现：

```text
多个 Documents
→ split_documents()
→ 汇总后的全部 Chunks
```

今天完成：

- 实现 `split_documents()`；
- 复用已有的 `split_document()`；
- 使用 `extend()` 合并各文档的 Chunk；
- 保持返回结果为扁平列表；
- 验证每篇文档的 `chunk_index` 独立编号；
- 验证原始 Metadata 不会被修改；
- 增加空列表测试；
- 完成批量切分测试。

## Document 结构

一个 Document 的结构：

```python
document = {
    "content": "完整 Markdown 正文",
    "metadata": {
        "title": "文档标题",
        "project": "所属项目",
        "system_layer": "系统层级",
        "document_type": "文档类型",
        "status": "completed",
        "last_updated": "2026-07-18",
        "tags": ["Python", "RAG"],
        "source": "docs_raw/example.md",
        "file_type": "markdown",
    },
}
```

Document 最外层只有两个核心字段：

```text
content
metadata
```

其中：

```text
content
→ 字符串
→ 保存完整正文

metadata
→ 字典
→ 保存标题、来源、状态、标签等结构化信息
```

`source` 和 `file_type` 位于：

```python
document["metadata"]
```

而不是 Document 最外层。

## Chunk 结构

一个 Chunk 的结构：

```python
chunk = {
    "content": "切分后的正文片段",
    "metadata": {
        "title": "文档标题",
        "source": "docs_raw/example.md",
        "file_type": "markdown",
        "chunk_index": 0,
    },
}
```

Document 与 Chunk 都包含：

```text
content
metadata
```

区别是：

```text
Document content
→ 一篇文档的完整正文

Chunk content
→ 从完整正文中切分出的一个片段
```

每个 Chunk 的 Metadata 在继承原文 Metadata 的基础上新增：

```text
chunk_index
```

它表示当前 Chunk 在所属原文中的顺序。

## Day 8：split_document()

函数接口：

```python
def split_document(
    document: dict,
    chunk_size: int,
    chunk_overlap: int,
) -> list[dict]:
    ...
```

职责：

```text
接收一个已经加载完成的 Document
→ 切分 document["content"]
→ 为每个文本块复制 Metadata
→ 增加 chunk_index
→ 返回这篇文档的 Chunk 列表
```

`split_document()` 不负责读取 Markdown 文件。

Markdown 文件读取属于 Loader。

## 切分参数

### chunk_size

表示每个 Chunk 最多包含的字符数量。

### chunk_overlap

表示相邻两个 Chunk 之间重复的字符数量。

### step

步长计算：

```python
step = chunk_size - chunk_overlap
```

例如：

```text
chunk_size = 8
chunk_overlap = 2
step = 6
```

每次窗口向后移动 6 个字符，因此相邻 Chunk 会保留 2 个重叠字符。

必须满足：

```text
chunk_overlap < chunk_size
```

否则：

```text
step <= 0
```

窗口无法正常向后移动，可能造成死循环。

## start、end 和 chunk_index

```text
start
→ 当前 Chunk 在原文中的起始下标

end
→ 当前 Chunk 的结束边界

chunk_index
→ 当前 Chunk 在所属文档中的顺序编号
```

结束边界：

```python
end = min(
    start + chunk_size,
    len(content),
)
```

`min()` 的作用是：

- 将 `end` 限制在真实正文长度以内；
- 普通 Chunk 的 `end` 保持为 `start + chunk_size`；
- 最后一个 Chunk 的 `end` 被限制为 `len(content)`；
- 方便通过 `end == len(content)` 判断已经到达正文结尾。

它不是为了防止 Python 切片越界报错。

Python 字符串切片超过末尾通常不会抛出异常。

## Metadata 复制

每个 Chunk 使用：

```python
chunk_metadata = metadata.copy()
```

不能直接写：

```python
chunk_metadata = metadata
```

直接赋值只会让两个变量指向同一个字典对象。

如果所有 Chunk 共用同一个 Metadata：

```python
chunk_metadata["chunk_index"] = chunk_index
```

后一次修改可能覆盖前面 Chunk 的编号，还可能修改原始 Document。

使用 `copy()` 后，每个 Chunk 都获得独立的外层 Metadata 字典。

当前使用的是浅拷贝，但 Day 9 只修改顶层的 `chunk_index`，因此足够。

## 为什么最后需要 break

当：

```python
end == len(content)
```

说明当前 Chunk 已经覆盖正文末尾。

此时必须：

```python
break
```

由于存在 `chunk_overlap`，最后一个 Chunk 生成后，`start` 仍可能小于正文长度。

如果继续循环，可能产生一个很短、并且与上一块高度重复的无用尾部 Chunk。

## Day 9：split_documents()

函数接口：

```python
def split_documents(
    documents: list[dict],
    chunk_size: int,
    chunk_overlap: int,
) -> list[dict]:
    ...
```

职责：

```text
接收 Documents 列表
→ 遍历每一个 Document
→ 调用 split_document()
→ 得到当前文档的 Chunk 列表
→ 合并到总 Chunk 列表
→ 返回全部 Chunk
```

最终实现：

```python
def split_documents(
    documents: list[dict],
    chunk_size: int,
    chunk_overlap: int,
) -> list[dict]:
    all_chunks = []

    for document in documents:
        document_chunks = split_document(
            document,
            chunk_size,
            chunk_overlap,
        )
        all_chunks.extend(document_chunks)

    return all_chunks
```

## 变量职责

### documents

```text
类型：list[dict]
```

表示多个 Document 组成的列表：

```python
documents = [
    document_1,
    document_2,
    document_3,
]
```

### document

```text
类型：dict
```

表示当前循环正在处理的一篇 Document。

### document_chunks

```text
类型：list[dict]
```

表示当前一篇 Document 经过 `split_document()` 后产生的 Chunk 列表。

### all_chunks

```text
类型：list[dict]
```

表示所有文档产生的 Chunk 汇总后的扁平列表。

结构：

```python
all_chunks = [
    chunk_a_0,
    chunk_a_1,
    chunk_b_0,
]
```

不是：

```python
all_chunks = [
    [chunk_a_0, chunk_a_1],
    [chunk_b_0],
]
```

## 为什么复用 split_document()

`split_documents()` 不重新实现滑动窗口，而是复用：

```python
split_document()
```

原因：

- 避免重复代码；
- 单文档和批量切分保持相同规则；
- 参数校验只维护一份；
- 修复单文档切分逻辑后，批量函数自动继承修改；
- 更容易测试和维护。

职责划分：

```text
split_document()
→ 负责一篇 Document 的具体切分

split_documents()
→ 负责批量遍历和汇总
```

## append() 与 extend()

假设：

```python
document_chunks = [
    chunk_1,
    chunk_2,
]
```

### 使用 append()

```python
all_chunks.append(document_chunks)
```

结果：

```python
all_chunks = [
    [
        chunk_1,
        chunk_2,
    ],
]
```

此时：

```text
all_chunks[0]
→ list
```

返回结构为：

```text
list[list[dict]]
```

这是嵌套列表。

### 使用 extend()

```python
all_chunks.extend(document_chunks)
```

结果：

```python
all_chunks = [
    chunk_1,
    chunk_2,
]
```

此时：

```text
all_chunks[0]
→ dict
```

返回结构为：

```text
list[dict]
```

本项目需要扁平的 Chunk 列表，因此必须使用：

```python
extend()
```

## 空列表处理

函数不需要专门写：

```python
if documents == []:
    return []
```

因为当：

```python
documents = []
```

时：

```python
for document in documents:
```

循环执行 0 次。

`all_chunks` 初始值为：

```python
[]
```

因此函数最终自然返回：

```python
[]
```

这属于边界场景，而不是异常场景。

## chunk_index 的编号范围

假设文档 A 和文档 B 都切出两个 Chunk：

```text
文档 A：
chunk_index = 0
chunk_index = 1

文档 B：
chunk_index = 0
chunk_index = 1
```

`chunk_index` 不是整个知识库的全局编号。

它表示：

```text
当前 Chunk 在所属原文中的位置
```

每次调用：

```python
split_document()
```

函数内部都会重新执行：

```python
chunk_index = 0
```

所以每篇文档都会重新编号。

不同文档通过：

```python
chunk["metadata"]["source"]
```

区分。

唯一定位一个 Chunk 时，可以结合：

```text
source + chunk_index
```

例如：

```text
docs_raw/a.md + 0
docs_raw/a.md + 1
docs_raw/b.md + 0
```

## 顺序保证

`split_documents()` 按照 `documents` 的原始顺序遍历。

同时，`split_document()` 保持每篇文档内部的 Chunk 顺序。

因此：

```text
先处理文档 A
→ 输出文档 A 的全部 Chunk

再处理文档 B
→ 输出文档 B 的全部 Chunk
```

最终顺序：

```python
[
    chunk_a_0,
    chunk_a_1,
    chunk_b_0,
]
```

稳定顺序有利于：

- 测试；
- 调试；
- 来源追踪；
- 结果比较；
- 后续定位切分错误。

## 批量切分测试

测试数据：

```python
documents = [
    {
        "content": "abcdefghij",
        "metadata": {
            "title": "文档 A",
            "source": "a.md",
        },
    },
    {
        "content": "12345",
        "metadata": {
            "title": "文档 B",
            "source": "b.md",
        },
    },
]
```

调用：

```python
batch_chunks = split_documents(
    documents,
    chunk_size=6,
    chunk_overlap=2,
)
```

步长：

```text
step = 6 - 2 = 4
```

文档 A：

```text
正文：abcdefghij

Chunk 0：
abcdef

Chunk 1：
efghij
```

文档 B 长度小于 `chunk_size`，因此只生成一个 Chunk：

```text
Chunk 0：
12345
```

最终正文顺序：

```python
[
    "abcdef",
    "efghij",
    "12345",
]
```

来源顺序：

```python
[
    "a.md",
    "a.md",
    "b.md",
]
```

编号顺序：

```python
[
    0,
    1,
    0,
]
```

总 Chunk 数量：

```text
3
```

## 测试内容

### 总数量

```python
assert len(batch_chunks) == 3
```

验证所有文档产生的 Chunk 数量是否正确。

### 扁平列表

```python
assert isinstance(batch_chunks[0], dict)
```

如果错误使用 `append()`，`batch_chunks[0]` 会是列表。

这条测试可以帮助发现嵌套列表问题。

### 正文与顺序

```python
assert [
    chunk["content"]
    for chunk in batch_chunks
] == [
    "abcdef",
    "efghij",
    "12345",
]
```

不仅验证数量，也验证：

- 切分内容；
- overlap；
- 文档顺序；
- Chunk 顺序。

### source 继承

```python
assert [
    chunk["metadata"]["source"]
    for chunk in batch_chunks
] == [
    "a.md",
    "a.md",
    "b.md",
]
```

验证每个 Chunk 都保留所属原文来源。

### chunk_index

```python
assert [
    chunk["metadata"]["chunk_index"]
    for chunk in batch_chunks
] == [
    0,
    1,
    0,
]
```

验证每篇文档内部重新从 0 编号。

### 原始 Metadata 独立性

```python
assert "chunk_index" not in documents[0]["metadata"]
assert "chunk_index" not in documents[1]["metadata"]
```

验证 Chunker 没有修改原始 Document 的 Metadata。

如果测试失败，可能错误使用了：

```python
chunk_metadata = metadata
```

而不是：

```python
chunk_metadata = metadata.copy()
```

### 空列表

```python
empty_batch_chunks = split_documents(
    [],
    chunk_size=6,
    chunk_overlap=2,
)

assert empty_batch_chunks == []
```

验证空 Documents 列表能够自然返回空 Chunk 列表。

## 实际运行

运行命令：

```bash
python src/test_chunker.py
```

实际结果：

```text
所有文本切分测试通过
真实文档标题：LeetCode Day 5 两数之和
真实文档长度：656
真实 Chunk 数量：2
所有批量文本切分测试通过
```

程序没有出现：

```text
Traceback
AssertionError
```

说明：

- Day 8 单文档测试仍然通过；
- 真实 Markdown 集成测试仍然通过；
- Day 9 批量切分测试通过；
- 新功能没有破坏旧功能。

## 当前完整数据流

```text
docs_raw/*.md
→ load_markdown_directory()
→ Documents 列表
→ split_documents()
→ 遍历每个 Document
→ split_document()
→ 当前文档的 Chunks
→ extend()
→ 全部 Chunks
```

展开流程：

```text
Markdown 文件
→ 读取原始文本
→ 分离 YAML Front Matter 与正文
→ yaml.safe_load()
→ validate_metadata()
→ 添加 source 和 file_type
→ Document
→ 汇总为 Documents
→ split_documents()
→ split_document()
→ 切分 content
→ 复制 Metadata
→ 添加 chunk_index
→ Chunk
→ 汇总为全部 Chunks
```

## 模块职责

### Loader

负责读取 Markdown 文件，调用 Parser 分离 YAML 与正文，调用 Validator 校验 Metadata，补充 `source` 和 `file_type`，最终返回 Document。

### Parser

负责分离 YAML Front Matter 与 Markdown 正文，并使用 `yaml.safe_load()` 解析 YAML。

### Validator

负责检查 Metadata 是否为字典、必需字段是否存在，以及 `status`、`tags` 等字段是否合法。

### split_document()

负责将一篇 Document 的 `content` 切分为多个 Chunk，并让每个 Chunk 继承 Metadata、增加 `chunk_index`。

### split_documents()

负责遍历多个 Documents，复用 `split_document()`，并使用 `extend()` 汇总为一个扁平的 Chunk 列表。

## 测试设计思路

测试一个函数时，需要从多个角度检查。

### 正常场景

使用最普通的合法输入，验证：

- 数量；
- 内容；
- 顺序；
- Metadata；
- 返回结构。

### 边界场景

例如：

- 空 Documents 列表；
- 只有一个 Document；
- 正文小于 `chunk_size`；
- 正文刚好等于 `chunk_size`；
- 空正文。

### 异常场景

例如：

- `chunk_size <= 0`；
- `chunk_overlap < 0`；
- `chunk_overlap >= chunk_size`。

这些参数校验仍然由 `split_document()` 负责。

### 数据完整性

检查：

- 原始 Metadata 是否被修改；
- `source` 是否保留；
- `chunk_index` 是否正确；
- 输出顺序是否稳定。

### 输出结构

检查返回值是否为：

```text
list[dict]
```

而不是：

```text
list[list[dict]]
```

## 当前边界

Day 9 已经完成：

```text
多个 Documents
→ 全部 Chunks
```

但当前仍然只是字符级固定长度切分。

尚未实现：

- 对整个真实 `docs_raw/` 进行统一统计；
- Token 级切分；
- Markdown 标题感知；
- 代码块保护；
- 表格保护；
- Embedding；
- ChromaDB；
- 相似度检索；
- Prompt 构造；
- Ollama 问答；
- 来源返回。

## 面试时怎么讲

我先实现了单文档切分函数 `split_document()`，随后增加 `split_documents()` 支持批量处理多个 Document。

批量函数不重新实现滑动窗口，而是遍历 Documents 并复用 `split_document()`，这样参数校验和切分规则只需要维护一份。

每篇文档产生的 Chunk 使用 `extend()` 合并到总列表中，从而保证返回值是 `list[dict]`，而不是嵌套的 `list[list[dict]]`。

每次调用 `split_document()` 时，`chunk_index` 都从 0 开始，因此编号表示 Chunk 在所属原文中的位置。不同原文通过 Metadata 中的 `source` 区分。

我通过总数量、正文顺序、来源继承、编号重置、Metadata 独立性、空列表和输出结构等测试，验证了批量切分功能，并确认新增功能没有破坏原有单文档切分。

## 后续计划

- 加载整个 `docs_raw/`；
- 批量切分所有真实 Document；
- 输出 Document 总数和 Chunk 总数；
- 按 `source` 统计每篇文档的 Chunk 数量；
- 验证所有来源统计之和等于总 Chunk 数；
- 完成 Loader 到 Chunker 的真实知识库数据管线；
- 后续进入 Embedding 和 ChromaDB。
