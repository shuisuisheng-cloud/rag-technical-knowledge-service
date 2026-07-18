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

1. Day 8 的 `split_document()` 一次能处理什么数据？
2. 目录加载器返回的数据结构是什么？
3. 为什么还需要新增 `split_documents()`？
4. Day 9 最终希望得到什么结果？

## Day 8 回顾

### Document 结构

请写出一个完整 Document 的结构：

```python
document = {
    # 待填写
}
```

回答：

1. Document 最外层有哪些字段？
2. `source` 和 `file_type` 位于哪一层？
3. `content` 的类型是什么？
4. `metadata` 的类型是什么？

### Chunk 结构

请写出一个完整 Chunk 的结构：

```python
chunk = {
    # 待填写
}
```

回答：

1. Chunk 与 Document 的共同字段有哪些？
2. Chunk 的正文和原始 Document 正文有什么区别？
3. Chunk Metadata 中新增了哪个字段？
4. 这个字段表达什么含义？

## split_document() 回顾

函数接口：

```python
def split_document(
    document: dict,
    chunk_size: int,
    chunk_overlap: int,
) -> list[dict]:
    ...
```

回答：

1. `chunk_size` 表示什么？
2. `chunk_overlap` 表示什么？
3. 为什么必须满足：

```text
chunk_overlap < chunk_size
```

4. 为什么步长为：

```python
step = chunk_size - chunk_overlap
```

5. `start` 表示什么？
6. `end` 表示什么？
7. `chunk_index` 表示什么？
8. 为什么需要：

```python
end = min(start + chunk_size, len(content))
```

9. Python 字符串切片的左闭右开规则是什么？
10. 为什么每个 Chunk 要使用：

```python
chunk_metadata = metadata.copy()
```

11. 不使用 `copy()` 会出现什么问题？
12. 当：

```python
end == len(content)
```

时，为什么要执行 `break`？

## Day 9 核心函数

函数接口：

```python
def split_documents(
    documents: list[dict],
    chunk_size: int,
    chunk_overlap: int,
) -> list[dict]:
    ...
```

## 输入结构

请写出 `documents` 的结构：

```python
documents = [
    # 待填写第一个 Document

    # 待填写第二个 Document
]
```

回答：

1. `documents` 本身是什么类型？
2. `documents` 中每个元素是什么类型？
3. 每个元素内部包含哪些核心字段？

## 输出结构

请写出 `split_documents()` 的返回结构：

```python
all_chunks = [
    # 待填写
]
```

回答：

1. 返回值为什么必须是扁平列表？
2. 返回值中的每个元素是什么类型？
3. 不同原文产生的 Chunk 如何区分？
4. 同一原文内部的 Chunk 如何表示顺序？

## split_documents() 数据流

补全下面的数据流：

```text
Documents 列表
→ 遍历 __________________
→ 调用 __________________
→ 得到当前文档的 __________________
→ 合并到 __________________
→ 返回 __________________
```

## 函数职责

### all_chunks

回答：

1. `all_chunks` 的初始值是什么？
2. 它保存什么数据？
3. 为什么要在循环外创建？
4. 最终返回的对象是不是它？

### document

回答：

1. `for document in documents` 中的 `document` 表示什么？
2. 每轮循环处理几篇原文？
3. 循环顺序是否会影响最终 Chunk 顺序？

### document_chunks

回答：

1. `document_chunks` 保存什么？
2. 它由哪个函数返回？
3. 它的类型是什么？
4. 每次循环的 `document_chunks` 是否属于同一篇原文？

## 为什么必须复用 split_document()

回答：

1. `split_documents()` 是否应该重新实现滑动窗口？
2. 如果复制一遍切分逻辑，会带来哪些维护问题？
3. 参数校验应该继续由哪个函数负责？
4. 单文档切分规则修改后，批量函数是否应该自动继承修改？

## append() 与 extend()

假设：

```python
document_chunks = [
    chunk_1,
    chunk_2,
]
```

分别写出以下操作的结果结构。

### append()

```python
all_chunks.append(document_chunks)
```

结果：

```python
all_chunks = [
    # 待填写
]
```

回答：

1. 使用 `append()` 后会不会出现嵌套列表？
2. 此时 `all_chunks[0]` 是字典还是列表？
3. 返回类型更接近 `list[dict]` 还是 `list[list[dict]]`？

### extend()

```python
all_chunks.extend(document_chunks)
```

结果：

```python
all_chunks = [
    # 待填写
]
```

回答：

1. `extend()` 会把什么内容逐个加入总列表？
2. 此时 `all_chunks[0]` 是什么类型？
3. 为什么本项目应该使用 `extend()`？

## 空列表处理

当前函数没有专门写：

```python
if documents == []:
    return []
```

回答：

1. 当 `documents` 为空列表时，`for` 循环执行几次？
2. `all_chunks` 最终保持什么值？
3. 函数会自然返回什么？
4. 为什么不一定需要额外的 `if/else`？

## chunk_index 的范围

假设：

```text
文档 A 切出 2 个 Chunk
文档 B 切出 2 个 Chunk
```

请填写最终编号：

```text
文档 A：
chunk_index = ______
chunk_index = ______

文档 B：
chunk_index = ______
chunk_index = ______
```

回答：

1. `chunk_index` 是整个知识库的全局编号吗？
2. 为什么每篇文档都应该重新从 0 开始？
3. 不同文档之间依靠哪个 Metadata 字段区分？

## 顺序保证

回答：

1. `split_documents()` 是否保持 `documents` 的原始顺序？
2. 是否保持每篇文档内部 Chunk 的顺序？
3. 如果先遍历文档 A，再遍历文档 B，最终列表中谁的 Chunk 在前？
4. 这种顺序为什么有助于调试和来源追踪？

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

调用参数：

```python
batch_chunks = split_documents(
    documents,
    chunk_size=6,
    chunk_overlap=2,
)
```

请自行计算：

1. `step` 等于多少？
2. 文档 A 会产生几个 Chunk？
3. 文档 A 每个 Chunk 的正文是什么？
4. 文档 B 会产生几个 Chunk？
5. `batch_chunks` 总长度是多少？
6. 所有 Chunk 的正文顺序是什么？
7. 所有 Chunk 的 `source` 顺序是什么？
8. 所有 Chunk 的 `chunk_index` 顺序是什么？

## 测试覆盖内容

### 总数量测试

回答：

1. 为什么要检查 `len(batch_chunks)`？
2. 数量不正确可能说明哪些逻辑有问题？

### 扁平列表测试

测试：

```python
assert isinstance(batch_chunks[0], dict)
```

回答：

1. 这条测试主要检查什么？
2. 如果错误使用 `append()`，`batch_chunks[0]` 会是什么类型？

### 正文和顺序测试

回答：

1. 为什么不能只检查总数量？
2. 为什么还需要检查每个 Chunk 的正文？
3. 为什么正文顺序也必须验证？

### source 继承测试

回答：

1. 为什么每个 Chunk 都需要保留 `source`？
2. `source` 对后续检索和来源追踪有什么作用？

### chunk_index 测试

回答：

1. 为什么第二篇文档的编号不能接着第一篇继续？
2. 测试如何证明每篇文档内部重新编号？

### 原始 Metadata 独立性测试

测试目标：

```python
"chunk_index" not in documents[0]["metadata"]
"chunk_index" not in documents[1]["metadata"]
```

回答：

1. 这两条测试在验证什么？
2. 如果原始 Metadata 被修改，可能是哪一行代码写错了？

### 空列表测试

回答：

1. 为什么要测试空 `documents`？
2. 预期返回值是什么？
3. 这属于正常场景、边界场景还是异常场景？

## 今天实际验证结果

请填写终端运行命令：

```bash
# 待填写
```

请记录运行结果：

```text
# 待填写
```

回答：

1. 原有单文档切分测试是否通过？
2. 真实 Markdown 集成测试是否通过？
3. 新增批量切分测试是否通过？
4. 是否出现 Traceback 或 AssertionError？

## 当前完整数据流

补全：

```text
docs_raw/*.md
→ __________________
→ Documents 列表
→ __________________
→ 全部 Chunks
```

展开补全：

```text
Markdown 文件
→ 读取原始文本
→ __________________
→ YAML 解析
→ __________________
→ 添加 source 和 file_type
→ Document
→ __________________
→ Chunk
→ 汇总为全部 Chunks
```

## 模块职责

请分别用一句话回答。

```text
Loader：

Parser：

Validator：

split_document()：

split_documents()：
```

## 当前边界

回答：

1. 当前切分依据是字符数还是 Token 数？
2. 当前是否能保护 Markdown 标题？
3. 当前是否能避免切断代码块？
4. 当前是否已经生成 Embedding？
5. 当前是否已经接入 ChromaDB？
6. 当前是否已经实现相似度检索？
7. 下一阶段最可能连接哪个模块？

## 测试设计方法

针对一个新函数，尝试从以下方向设计测试。

### 正常场景

1. 最普通的合法输入是什么？
2. 预期输出的数量、内容和顺序是什么？

### 边界场景

1. 空列表应该怎样处理？
2. 单元素列表应该怎样处理？
3. 正文刚好等于 `chunk_size` 时会怎样？
4. 正文小于 `chunk_size` 时会怎样？

### 异常场景

1. 哪些参数应该被拒绝？
2. 预期抛出什么异常？
3. 异常由批量函数处理，还是由单文档函数处理？

### 数据完整性

1. 原始输入有没有被意外修改？
2. Metadata 是否被正确继承？
3. 来源和编号是否正确？

### 输出结构

1. 返回的是字典、列表还是嵌套列表？
2. 是否符合函数类型标注？
3. 后续模块能否直接使用？

## 下次开始前复习问题

1. `split_document()` 与 `split_documents()` 的职责有什么区别？
2. `documents`、`document`、`document_chunks`、`all_chunks` 分别是什么？
3. 为什么使用 `extend()` 而不是 `append()`？
4. 空 `documents` 为什么可以自然返回 `[]`？
5. 为什么每篇文档的 `chunk_index` 都重新从 0 开始？
6. 不同文档的 Chunk 通过什么字段区分？
7. 批量切分测试验证了哪几个方面？
8. 当前从 Markdown 到全部 Chunks 的完整数据流是什么？
9. Loader、Validator、Chunker 分别负责什么？
10. 下一阶段为什么还不能直接回答用户问题？
