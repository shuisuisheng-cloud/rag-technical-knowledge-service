---
title: RAG Day 8 固定长度文本切分与 Chunk 数据结构
project: 基于 RAG 的个人技术知识库问答服务
system_layer: 知识层 / 文档检索服务
document_type: learning_note
status: completed
last_updated: 2026-07-13
tags: [Python, RAG, Chunking, TextSplit, Metadata, Testing]
---

# RAG Day 8 固定长度文本切分与 Chunk 数据结构

## 今日目标

实现文本切分函数：

```python
split_document(
    document,
    chunk_size,
    chunk_overlap,
)
```

将一篇完整的 Document 切分成多个带 Metadata 的 Chunk。

Day 8 使用字符级固定长度切分，暂时不实现 Token 切分、Markdown 标题切分和语义切分。

## 为什么需要文本切分

一篇 Markdown 文档可能包含大量内容。

如果直接对整篇文档进行向量化，会产生以下问题：

- 检索结果范围过大；
- 无关内容进入大模型上下文；
- 无法精确定位答案来源；
- 文档可能超过 Embedding 模型的输入限制；
- 一个向量无法准确表达整篇长文档的多个主题。

因此，在进行 Embedding 之前，需要先把 Document 切分成较小的 Chunk。

## 输入结构

`split_document()` 接收一个 Document：

```python
document = {
    "content": "完整正文",
    "metadata": {
        "title": "文档标题",
        "source": "文档路径",
        "status": "completed",
    },
}
```

同时接收两个切分参数：

```text
chunk_size
→ 每个 Chunk 最多包含的字符数量

chunk_overlap
→ 相邻两个 Chunk 之间重复的字符数量
```

## 输出结构

函数返回 Chunk 列表：

```python
[
    {
        "content": "第一个文本块",
        "metadata": {
            "title": "文档标题",
            "source": "文档路径",
            "status": "completed",
            "chunk_index": 0,
        },
    },
    {
        "content": "第二个文本块",
        "metadata": {
            "title": "文档标题",
            "source": "文档路径",
            "status": "completed",
            "chunk_index": 1,
        },
    },
]
```

每个 Chunk：

- 保存自己的正文；
- 继承原 Document 的 Metadata；
- 新增 `chunk_index`；
- 使用独立的外层 Metadata 字典。

## 参数校验

### chunk_size 必须大于 0

```python
if chunk_size <= 0:
    raise ValueError(...)
```

如果 `chunk_size` 小于等于 0，就无法形成有效文本块。

### chunk_overlap 不能小于 0

```python
if chunk_overlap < 0:
    raise ValueError(...)
```

重叠字符数量不能是负数。

### chunk_overlap 必须小于 chunk_size

```python
if chunk_overlap >= chunk_size:
    raise ValueError(...)
```

因为步长计算为：

```python
step = chunk_size - chunk_overlap
```

如果 `chunk_overlap >= chunk_size`，步长就会小于等于 0，循环无法正常向后移动，可能形成死循环。

## 空文本处理

如果正文为空字符串：

```python
if content == "":
    return []
```

空文档不需要生成 Chunk，因此直接返回空列表。

## 步长计算

步长为：

```python
step = chunk_size - chunk_overlap
```

例如：

```text
chunk_size = 8
chunk_overlap = 2
step = 6
```

每生成一个 Chunk 后，下一块的起点向后移动 6 个字符。

因为上一块长度为 8，所以相邻两块之间会保留 2 个重复字符。

## start 与 end

```text
start
→ 当前 Chunk 在原文中的起始位置

end
→ 当前 Chunk 的结束边界
```

结束边界计算：

```python
end = min(
    start + chunk_size,
    len(content),
)
```

`min()` 的作用不是防止 Python 切片越界异常。

Python 字符串切片超过长度通常不会报错。

它的主要作用是：

- 将 `end` 限制在真实正文长度以内；
- 明确当前块的真实结束边界；
- 让最后一块满足 `end == len(content)`；
- 方便判断是否已经切到正文末尾。

## Python 切片规则

切片写法：

```python
content[start:end]
```

采用左闭右开规则：

```text
包含 start
不包含 end
```

例如：

```python
content[0:8]
```

读取的是下标：

```text
0、1、2、3、4、5、6、7
```

共 8 个字符。

长度为 20 的字符串，有效字符下标为：

```text
0～19
```

但末尾边界可以写成：

```text
20
```

因为 `end` 表示最后一个字符之后的位置。

## 切分示例

正文：

```text
abcdefghijklmnopqrst
```

参数：

```text
chunk_size = 8
chunk_overlap = 2
step = 6
```

第一次：

```text
start = 0
end = 8
content[0:8] = abcdefgh
```

第二次：

```text
start = 6
end = 14
content[6:14] = ghijklmn
```

第三次：

```text
start = 12
end = 20
content[12:20] = mnopqrst
```

最终结果：

```text
Chunk 0：abcdefgh
Chunk 1：ghijklmn
Chunk 2：mnopqrst
```

相邻块的重叠内容：

```text
Chunk 0 与 Chunk 1
→ gh

Chunk 1 与 Chunk 2
→ mn
```

## Metadata 为什么需要 copy()

错误写法：

```python
chunk_metadata = metadata
```

这不会创建新的字典，只会让两个变量指向同一个字典对象。

如果多个 Chunk 共用同一个 Metadata：

```python
chunk_metadata["chunk_index"] = chunk_index
```

后生成的 `chunk_index` 会覆盖前面 Chunk 的编号，也可能修改原始 Document。

正确写法：

```python
chunk_metadata = metadata.copy()
```

这样每个 Chunk 都拥有独立的外层 Metadata 字典。

当前使用的是浅拷贝。

如果 Metadata 中包含 `tags` 列表等嵌套对象，这些内部对象仍可能共享。

但 Day 8 只新增和修改顶层的 `chunk_index`，所以浅拷贝已经足够。

## chunk_index 的作用

`chunk_index` 表示当前 Chunk 在原始文档中的顺序：

```text
第一个 Chunk
→ chunk_index = 0

第二个 Chunk
→ chunk_index = 1

第三个 Chunk
→ chunk_index = 2
```

它可以用于：

- 追踪 Chunk 在原文中的位置；
- 按顺序恢复相邻文本；
- 检索结果展示；
- 后续相邻 Chunk 扩展；
- 来源追溯和调试。

## 为什么最后一块需要 break

当：

```python
end == len(content)
```

说明当前 Chunk 已经覆盖到正文末尾。

此时必须执行：

```python
break
```

由于使用了 overlap，最后一块生成后，`start` 仍可能小于正文长度。

如果继续增加步长并再次循环，可能生成一个很短、并且与上一块高度重复的尾部 Chunk。

例如最后可能多出：

```text
st
```

因此切到正文末尾后应立即结束循环。

## 独立测试

测试文件：

```text
src/test_chunker.py
```

### 短文本测试

当正文长度小于 `chunk_size` 时：

```text
正文：abcdefghij
chunk_size：20
chunk_overlap：5
```

预期：

- 只生成一个 Chunk；
- Chunk 内容等于原文；
- `chunk_index` 等于 0。

### 多 Chunk 测试

正文：

```text
abcdefghijklmnopqrst
```

参数：

```text
chunk_size = 8
chunk_overlap = 2
```

预期内容：

```python
[
    "abcdefgh",
    "ghijklmn",
    "mnopqrst",
]
```

预期编号：

```python
[
    0,
    1,
    2,
]
```

测试中需要比较：

```text
Chunk 内容列表
与
预期内容列表
```

不能把一个列表直接与完整字符串比较。

### Metadata 独立性测试

验证不同 Chunk 的 Metadata 不是同一个对象：

```python
chunks[0]["metadata"] is not chunks[1]["metadata"]
```

验证 Chunk Metadata 与原 Document Metadata 不是同一个对象：

```python
chunks[0]["metadata"] is not document["metadata"]
```

验证原 Document 没有被写入：

```python
"chunk_index" not in document["metadata"]
```

### 空文本测试

空正文预期返回：

```python
[]
```

### 非法参数测试

以下参数应抛出 `ValueError`：

```text
chunk_size = 0
chunk_overlap = -1
chunk_overlap = chunk_size
```

测试使用 `try/except`。

如果函数没有抛出预期异常，就主动抛出 `AssertionError`，表示测试失败。

## 真实 Markdown 集成测试

测试文件：

```text
docs_raw/leetcode_day05_two_sum.md
```

完整数据流：

```text
真实 Markdown 文件
→ load_markdown()
→ YAML Front Matter 解析
→ Metadata 校验
→ Document
→ split_document()
→ Chunk 列表
```

切分参数：

```text
chunk_size = 500
chunk_overlap = 100
```

实际结果：

```text
真实文档标题：LeetCode Day 5 两数之和
真实文档长度：656
真实 Chunk 数量：2
```

集成测试验证：

- 至少生成一个 Chunk；
- 每个 Chunk 长度不超过 500；
- 每个 Chunk 都继承原文 `source`；
- `chunk_index` 从 0 连续递增。

## 当前完整数据流

```text
Markdown 文件
→ load_markdown()
→ parse_markdown_content()
→ validate_metadata()
→ Document
→ split_document()
→ Chunk 列表
→ 后续 Embedding
→ Vector Store
→ Retrieval
→ Answer
```

Day 8 已经完成从 Document 到 Chunk 的转换。

## 当前方案的优点

字符级固定长度切分的优点：

- 实现简单；
- 容易理解；
- 容易测试；
- 切分长度可控；
- 不依赖额外模型；
- 适合作为第一版 Chunking 基线。

## 当前方案的局限

当前方案只按照字符位置切分，可能切断：

- 一个完整句子；
- Markdown 标题和正文；
- Python 或 C 代码块；
- 表格；
- 列表；
- 一个完整知识点。

`chunk_size` 统计的是字符数量，不是模型 Token 数量。

不同字符对应的 Token 数量并不完全相同，所以字符长度不能精确代表 Embedding 模型的输入长度。

## 当前边界

Day 8 尚未实现：

- 批量切分全部 Document；
- Token 级切分；
- Markdown 标题切分；
- 段落切分；
- 句子切分；
- 代码块保护；
- 表格保护；
- 语义切分；
- Chunk 总数量记录；
- Embedding；
- ChromaDB；
- 相似度检索。

## 面试时怎么讲

我实现了一个固定字符长度的文本切分器。

函数输入是包含 `content` 和 `metadata` 的 Document，输出是多个包含正文和 Metadata 的 Chunk。

我使用 `chunk_size` 控制每个块的最大字符数量，使用 `chunk_overlap` 保留相邻块之间的上下文，实际步长为：

```text
chunk_size - chunk_overlap
```

切分时使用 `start` 和 `end` 维护滑动窗口，并使用左闭右开的 Python 字符串切片。

每个 Chunk 通过 `metadata.copy()` 获取独立的外层 Metadata，并新增连续的 `chunk_index`。

函数还处理了空文本和非法参数，并通过短文本、多块文本、Metadata 独立性、异常参数以及真实 Markdown 集成测试完成验证。

当前方案简单可靠，但可能切断句子、标题和代码块，后续需要升级为更适合 Markdown 技术文档的切分策略。

## 后续计划

- 批量切分目录中的所有 Document；
- 统计 Document 数量和 Chunk 数量；
- 补充批量切分测试；
- 研究 Token 与字符数量的区别；
- 设计适合 Markdown 技术文档的切分策略；
- 进入 Embedding 与 ChromaDB。
