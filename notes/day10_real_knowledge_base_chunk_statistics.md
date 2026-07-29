---
title: RAG Day 10 真实知识库批量切分与来源统计
project: 基于 RAG 的个人技术知识库问答服务
system_layer: 知识层 / 文档检索服务
document_type: learning_note
status: completed
last_updated: 2026-07-20
tags: [Python, RAG, MarkdownLoader, Chunking, BatchProcessing, Statistics, Metadata]
---

# RAG Day 10 真实知识库批量切分与来源统计

## 今日目标

将 `docs_raw/` 中的全部真实 Markdown 文档加载并批量切分，完成：

```text
docs_raw/*.md
→ Documents
→ Chunks
→ 按 source 统计每篇文档的 Chunk 数量
```

同时验证：

- Documents 不为空；
- Chunks 不为空；
- 所有 Chunk 都包含 `source`；
- 所有 Chunk 都包含 `chunk_index`；
- 各来源的 Chunk 数量之和等于 Chunk 总数。

## 当前 Document 结构

```python
document = {
    "content": "完整 Markdown 正文",
    "metadata": {
        "title": "文档标题",
        "project": "所属项目",
        "system_layer": "系统层级",
        "document_type": "文档类型",
        "status": "completed",
        "last_updated": "2026-07-20",
        "tags": ["Python", "RAG"],
        "source": "docs_raw/example.md",
        "file_type": "markdown",
    },
}
```

Document 最外层包含：

```text
content
metadata
```

其中：

```text
content
→ str
→ 保存完整正文

metadata
→ dict
→ 保存标题、项目、状态、标签和来源等结构化信息
```

`source` 和 `file_type` 位于：

```python
document["metadata"]
```

## 当前 Chunk 结构

```python
chunk = {
    "content": "切分后的正文片段",
    "metadata": {
        "title": "原文标题",
        "source": "docs_raw/example.md",
        "file_type": "markdown",
        "chunk_index": 0,
    },
}
```

Document 和 Chunk 都有：

```text
content
metadata
```

区别是：

```text
Document content
→ 一篇文档的完整正文

Chunk content
→ 从完整正文中切分出的局部片段
```

Chunk Metadata 在继承原文 Metadata 的基础上新增：

```text
chunk_index
```

一个 Chunk 可以通过下面的组合定位：

```text
source + chunk_index
```

## main.py 的职责

`main.py` 当前是项目的数据管线集成验证入口。

它不负责重新实现：

- Markdown 解析；
- Metadata 校验；
- 滑动窗口切分。

它负责组织已有模块：

```text
load_markdown_directory()
→ split_documents()
→ 统计和验证
```

## 切分参数

当前参数：

```python
chunk_size = 500
chunk_overlap = 100
```

步长：

```text
step = chunk_size - chunk_overlap
     = 500 - 100
     = 400
```

含义：

```text
每个 Chunk 最多 500 个字符
下一块向后移动 400 个字符
相邻 Chunk 重叠 100 个字符
```

当前是字符级切分，不是 Token 级切分。

## 加载真实知识库

目录路径：

```python
directory_path = "docs_raw"
```

调用：

```python
documents = load_markdown_directory(directory_path)
```

返回类型：

```text
list[dict]
```

其中每个元素都是一个 Document。

完整加载流程：

```text
docs_raw/
→ 检查目录是否存在
→ 检查路径是否为目录
→ 查找所有 *.md
→ 按文件名排序
→ 逐个调用 load_markdown()
→ 返回 Documents 列表
```

## 单文件加载流程

```text
Markdown 文件路径
→ 检查文件是否存在
→ 检查路径是否为文件
→ 以 UTF-8 读取原始文本
→ parse_markdown_content()
→ 分离 YAML Front Matter 和正文
→ yaml.safe_load()
→ validate_metadata()
→ 添加 source 和 file_type
→ 返回 Document
```

## Parser 与 Validator

### parse_markdown_content()

负责：

```text
接收完整 Markdown 原始文本
→ 分离 YAML Front Matter 和正文
→ 使用 yaml.safe_load() 解析 YAML
→ 返回 content 和 parsed_metadata
```

### validate_metadata()

负责：

```text
检查 YAML 解析结果是不是 dict
→ 检查必需字段是否存在
→ 检查 status 是否在允许范围内
→ 检查 tags 是否为 list
→ 返回合法 Metadata
```

Parser 负责解析。

Validator 负责校验。

## 批量切分

调用：

```python
chunks = split_documents(
    documents,
    chunk_size,
    chunk_overlap,
)
```

`split_documents()` 的流程：

```text
接收 Documents
→ 遍历每个 Document
→ 调用 split_document()
→ 得到当前文档的 document_chunks
→ 使用 extend() 合并
→ 返回扁平的 Chunks 列表
```

`split_document()` 的流程：

```text
接收一个 Document
→ 校验 chunk_size 和 chunk_overlap
→ 读取 content 和 metadata
→ 使用滑动窗口切分 content
→ 为每块复制 Metadata
→ 添加 chunk_index
→ 返回当前文档的 Chunk 列表
```

## append() 与 extend()

假设：

```python
document_chunks = [
    chunk_1,
    chunk_2,
]
```

使用：

```python
all_chunks.append(document_chunks)
```

会得到：

```python
[
    [chunk_1, chunk_2],
]
```

返回结构是：

```text
list[list[dict]]
```

使用：

```python
all_chunks.extend(document_chunks)
```

会得到：

```python
[
    chunk_1,
    chunk_2,
]
```

返回结构是：

```text
list[dict]
```

项目后续需要直接遍历每个 Chunk，因此使用 `extend()`。

## 总数统计

```python
print("Chunk总数：", len(chunks))
print("文档总数：", len(documents))
```

本次真实运行结果：

```text
文档总数：25
Chunk 总数：183
```

说明：

```text
25 篇真实 Markdown 文档
→ 经过字符级重叠切分
→ 生成 183 个 Chunk
```

Chunk 数量受以下因素影响：

- 文档正文长度；
- `chunk_size`；
- `chunk_overlap`；
- 文档是否为空；
- 切分结束条件。

## 按来源统计 Chunk 数量

统计字典：

```python
chunk_count_by_source = {}
```

结构：

```text
key
→ source
→ 原始 Markdown 文件路径

value
→ count
→ 当前来源生成的 Chunk 数量
```

示例：

```python
{
    "docs_raw/a.md": 2,
    "docs_raw/b.md": 5,
}
```

## dict.get()

遍历每个 Chunk：

```python
for chunk in chunks:
    source = chunk["metadata"]["source"]

    current_count = (
        chunk_count_by_source.get(source, 0) + 1
    )

    chunk_count_by_source[source] = current_count
```

`get(source, 0)` 的含义：

```text
source 已存在
→ 返回当前数量

source 不存在
→ 返回默认值 0
```

再加 1，表示发现一个属于该来源的新 Chunk。

这种写法不需要提前写：

```python
if source in chunk_count_by_source:
```

## items() 与元组拆包

```python
chunk_count_by_source.items()
```

每次产生一个二元组：

```python
(source, count)
```

如果直接：

```python
for data in chunk_count_by_source.items():
    print(data)
```

会输出：

```text
('docs_raw/example.md', 3)
```

因为 `data` 是一个元组。

使用元组拆包：

```python
for source, count in chunk_count_by_source.items():
    print(source, count)
```

可以分别取得来源和数量。

## 排序输出

最终代码：

```python
for source, count in sorted(
    chunk_count_by_source.items()
):
    print(f"{source} -> {count} chunks")
```

`sorted()` 让输出顺序稳定，便于：

- 阅读；
- 调试；
- 对比前后运行结果；
- 发现新增或遗漏文件。

当前默认根据元组的第一个元素 `source` 排序。

## 统计一致性验证

```python
assert (
    sum(chunk_count_by_source.values())
    == len(chunks)
)
```

其中：

```text
chunk_count_by_source.values()
→ 每篇文档的 Chunk 数量

sum(...)
→ 所有来源数量之和

len(chunks)
→ 实际全部 Chunk 数量
```

两者相等说明：

```text
每个 Chunk 都被统计一次
没有遗漏
没有重复统计
```

本次运行没有出现 `AssertionError`，因此统计一致。

## 非空验证

```python
assert len(documents) > 0
assert len(chunks) > 0
```

分别验证：

```text
Loader 确实加载到了真实文档
Chunker 确实产生了文本块
```

如果 Documents 不为空但 Chunks 为空，可能包括：

- 所有文档正文为空；
- `split_documents()` 没有正确汇总；
- `split_document()` 的结束逻辑错误。

## source 完整性验证

```python
assert all(
    "source" in chunk["metadata"]
    for chunk in chunks
)
```

`all()` 会检查所有 Chunk。

只要有一个 Chunk 缺少 `source`，结果就是 `False`，断言失败。

`source` 由 Loader 根据真实文件路径添加。

它用于：

- 来源追踪；
- 按文档筛选；
- 显示回答引用；
- 定位错误文档；
- 与 `chunk_index` 组合定位 Chunk。

## chunk_index 完整性验证

```python
assert all(
    "chunk_index" in chunk["metadata"]
    for chunk in chunks
)
```

`chunk_index` 由 `split_document()` 添加。

它表示：

```text
当前 Chunk 在所属原文中的顺序
```

每篇文档都重新从 0 编号，因此不同文档可以同时存在：

```text
chunk_index = 0
```

不同文档依靠 `source` 区分。

## 当前完整数据流

```text
docs_raw/*.md
→ load_markdown_directory()
→ Documents
→ split_documents()
→ Chunks
→ 按 source 统计
→ 输出每篇文档的 Chunk 数量
```

展开后：

```text
Markdown 文件
→ UTF-8 读取
→ parse_markdown_content()
→ YAML Front Matter 与正文分离
→ yaml.safe_load()
→ validate_metadata()
→ 添加 source 和 file_type
→ Document
→ 汇总为 Documents
→ split_documents()
→ 遍历每个 Document
→ split_document()
→ 切分 content
→ 复制 Metadata
→ 添加 chunk_index
→ Chunk
→ extend()
→ 全部 Chunks
→ 按 source 统计
```

## 模块职责

### load_markdown_directory()

负责发现目录中的 Markdown 文件，逐个调用 `load_markdown()`，返回 Documents 列表。

### load_markdown()

负责读取一个 Markdown 文件，组织 Parser、Validator 和 Loader Metadata，最终返回 Document。

### parse_markdown_content()

负责分离 YAML Front Matter 和正文，并解析 YAML。

### validate_metadata()

负责检查 Metadata 类型、必需字段及字段内容是否合法。

### split_document()

负责将一篇 Document 切分成多个 Chunk。

### split_documents()

负责遍历多个 Documents，复用 `split_document()` 并汇总全部 Chunks。

### main()

负责组织真实知识库加载、批量切分、统计和集成验证。

## 为什么要检查文件和目录

读取路径前需要检查：

```text
路径是否存在
路径是文件还是目录
```

原因是：

- 尽早发现配置或输入错误；
- 避免在错误位置继续执行；
- 给出明确、可定位的异常信息；
- 防止把目录当文件读取；
- 防止把普通文件当目录遍历。

常见方法：

```python
path.exists()
path.is_file()
path.is_dir()
```

这些检查由 Loader 统一负责，而不是由每个调用者重复实现。

忘记具体 API 不严重，重要的是理解：

```text
谁负责检查
为什么检查
失败后应该如何处理
```

## 当前测试层次

```text
test_metadata.py
→ Metadata Validator 单元测试

test_chunker.py
→ 单文档和批量切分单元测试

真实 Markdown 切分
→ 小型集成测试

main.py
→ 整体数据管线冒烟测试
```

新增功能后仍需重新运行旧测试，防止新代码破坏已经完成的功能。

## 当前已完成能力

```text
[x] 单个 Markdown 文件读取
[x] YAML Front Matter 分离
[x] Metadata 校验
[x] 目录批量加载
[x] 单个 Document 切分
[x] 多个 Documents 批量切分
[x] 真实知识库整体切分
[x] 按 source 统计 Chunk 数量
[ ] Embedding
[ ] ChromaDB
[ ] 相似度检索
[ ] Ollama 问答
[ ] 来源追溯回答
```

## 当前边界

目前已经完成：

```text
文件
→ Document
→ Chunk
```

尚未完成：

```text
Chunk
→ Embedding 向量
→ ChromaDB
→ 相似度检索
→ Prompt
→ Ollama
→ Answer + Sources
```

当前 Chunk 数量统计只能证明数据管线正常，不能证明：

- 切分质量足够好；
- 检索结果准确；
- 回答质量优秀；
- Embedding 模型适合技术文档。

## 面试时怎么讲

我首先通过目录 Loader 读取 `docs_raw/` 中的全部 Markdown 文件，解析 YAML Front Matter，校验 Metadata，并生成统一的 Document 结构。

随后调用 `split_documents()`，逐个复用 `split_document()`，将 25 篇真实文档切分为 183 个 Chunk。

每个 Chunk 都继承原文 Metadata，并包含 `source` 和 `chunk_index`。

我使用字典按照 `source` 统计每篇文档产生的 Chunk 数量，并通过总数一致性、非空、来源完整性和编号完整性断言完成集成验证。

当前已经完成从原始知识文档到结构化 Chunk 的数据管线，下一步是生成 Embedding 并写入向量数据库。

## 后续计划

- 了解 Embedding 的输入与输出；
- 选择适合中文技术文档的 Embedding 模型；
- 将 Chunk 正文转换为向量；
- 将正文、向量和 Metadata 写入 ChromaDB；
- 实现相似度检索；
- 返回相关 Chunk 及原始来源。
