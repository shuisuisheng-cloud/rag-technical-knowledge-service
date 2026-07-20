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

1. 如何加载 `docs_raw/` 中的全部真实 Markdown 文档？
2. 如何把全部 Documents 批量切分为 Chunks？
3. 如何统计 Document 总数和 Chunk 总数？
4. 如何统计每个 `source` 产生的 Chunk 数量？
5. 如何验证统计结果没有遗漏或重复？
6. 当前从原始文档到全部 Chunk 的完整数据流是什么？

## Day 9 回顾

### split_document()

回答：

1. `split_document()` 的输入是什么？
2. `split_document()` 的输出是什么？
3. 它是否负责读取 Markdown 文件？
4. 它真正切分的是 Document 中的哪个字段？
5. 每个 Chunk 如何继承原文 Metadata？
6. `chunk_index` 表示什么？

### split_documents()

回答：

1. `split_documents()` 的输入是什么？
2. 它为什么需要复用 `split_document()`？
3. `document_chunks` 表示什么？
4. `all_chunks` 表示什么？
5. 为什么使用 `extend()` 而不是 `append()`？
6. 最终返回的是扁平列表还是嵌套列表？

## 当前 Document 结构

请补全：

```python
document = {
    # 待填写
}
```

回答：

1. Document 最外层有哪些字段？
2. `content` 是什么类型？
3. `metadata` 是什么类型？
4. `source` 位于哪一层？
5. `file_type` 位于哪一层？

## 当前 Chunk 结构

请补全：

```python
chunk = {
    # 待填写
}
```

回答：

1. Chunk 与 Document 有哪些共同字段？
2. Chunk 正文与 Document 正文有什么区别？
3. Chunk Metadata 比原文 Metadata 多了哪个字段？
4. 如何唯一定位一篇文档中的某个 Chunk？

## main.py 的职责

Day 10 在 `src/main.py` 中完成真实知识库数据管线验证。

回答：

1. `main.py` 是否负责实现 Markdown 解析算法？
2. `main.py` 是否负责实现滑动窗口切分算法？
3. `main.py` 主要负责调用和组织哪些模块？
4. 为什么说 `main.py` 当前属于集成验证入口？

## 切分参数

当前参数：

```python
chunk_size = 500
chunk_overlap = 100
```

回答：

1. `chunk_size` 表示什么？
2. `chunk_overlap` 表示什么？
3. 当前步长是多少？
4. 相邻两个 Chunk 会重复多少个字符？
5. 当前按字符数量切分还是按 Token 数量切分？

## 目录路径

当前目录：

```python
directory_path = "docs_raw"
```

回答：

1. 这个路径传给哪个函数？
2. 这个函数返回什么数据结构？
3. 目录不存在时应该由哪个模块处理？
4. 路径存在但不是目录时应该如何处理？
5. 为什么这些检查不应该全部写在 `main.py` 中？

## 加载全部 Documents

调用：

```python
documents = load_markdown_directory(directory_path)
```

回答：

1. `documents` 的类型是什么？
2. 列表中每一个元素是什么？
3. `load_markdown_directory()` 内部会遍历什么？
4. 每个 Markdown 文件由哪个函数加载？
5. 每个 Document 在返回前经过哪些处理？

## 批量切分全部 Documents

调用：

```python
chunks = split_documents(
    documents,
    chunk_size,
    chunk_overlap,
)
```

回答：

1. `chunks` 的类型是什么？
2. 列表中的每个元素是什么？
3. `split_documents()` 内部调用哪个函数？
4. 不同文档的 Chunk 如何区分？
5. 同一篇文档内部如何表示 Chunk 顺序？

## 总数统计

程序输出：

```text
文档总数：________
Chunk 总数：________
```

请填写本次真实运行结果。

回答：

1. Document 总数如何计算？
2. Chunk 总数如何计算？
3. 为什么两个总数都应该大于 0？
4. Chunk 总数为什么通常大于 Document 总数？
5. 哪些因素会影响 Chunk 总数？

## 按来源统计 Chunk 数量

统计字典：

```python
chunk_count_by_source = {}
```

回答：

1. 字典的键是什么？
2. 字典的值是什么？
3. 为什么使用 `source` 作为键？
4. 一篇文档为什么可能对应多个 Chunk？
5. 这个字典最终表达什么信息？

## 遍历全部 Chunk

核心循环：

```python
for chunk in chunks:
    source = chunk["metadata"]["source"]
```

回答：

1. `chunk` 是什么类型？
2. 为什么需要从 Metadata 中读取 `source`？
3. 为什么不能只根据 `chunk_index` 区分所有 Chunk？
4. 如果某个 Chunk 没有 `source`，后续会出现什么问题？

## dict.get()

统计时使用：

```python
current_count = chunk_count_by_source.get(source, 0) + 1
```

回答：

1. `get(source, 0)` 的作用是什么？
2. 当 `source` 第一次出现时返回什么？
3. 当 `source` 已存在时返回什么？
4. 为什么需要在结果后加 1？
5. 为什么这种写法可以避免提前判断键是否存在？

## 写回统计结果

调用：

```python
chunk_count_by_source[source] = current_count
```

回答：

1. 当 `source` 第一次出现时，这句会做什么？
2. 当 `source` 已经存在时，这句会做什么？
3. 为什么必须把更新后的数量写回字典？

## 字典 items() 与元组拆包

调用：

```python
chunk_count_by_source.items()
```

回答：

1. `items()` 中的每一个元素是什么结构？
2. 为什么直接 `print(data)` 会出现括号？
3. 括号中的两个值分别是什么？
4. 如何使用元组拆包分别得到 `source` 和 `count`？

请补全：

```python
for ________, ________ in chunk_count_by_source.items():
    ...
```

## 排序输出

当前使用：

```python
sorted(chunk_count_by_source.items())
```

回答：

1. 为什么需要排序？
2. 如果不排序，统计结果是否一定错误？
3. 排序对测试和调试有什么帮助？
4. 当前默认按照元组中的哪个值排序？

## 输出格式

目标输出：

```text
docs_raw/example.md -> 3 chunks
```

回答：

1. 如何通过 f-string 输出这种格式？
2. 为什么这种格式比直接打印元组更容易阅读？
3. `source` 和 `count` 分别对应输出中的哪一部分？

## 统计一致性检查

断言：

```python
assert sum(chunk_count_by_source.values()) == len(chunks)
```

回答：

1. `chunk_count_by_source.values()` 返回什么？
2. `sum(...)` 计算的是什么？
3. `len(chunks)` 计算的是什么？
4. 两者相等能够证明什么？
5. 如果两者不相等，可能出现了哪些问题？

## Documents 非空检查

断言：

```python
assert len(documents) > 0
```

回答：

1. 这条断言验证什么？
2. 如果失败，可能是路径、文件还是 Loader 出现问题？
3. 它属于功能实现还是集成验证？

## Chunks 非空检查

断言：

```python
assert len(chunks) > 0
```

回答：

1. 这条断言验证什么？
2. Documents 不为空但 Chunks 为空，可能是什么原因？
3. 空正文是否可能影响结果？

## source 完整性检查

断言：

```python
assert all(
    "source" in chunk["metadata"]
    for chunk in chunks
)
```

回答：

1. `all()` 的作用是什么？
2. 生成式每次检查什么？
3. 只要一个 Chunk 缺少 `source`，最终结果是什么？
4. `source` 最初由哪个模块加入 Metadata？

## chunk_index 完整性检查

断言：

```python
assert all(
    "chunk_index" in chunk["metadata"]
    for chunk in chunks
)
```

回答：

1. 这条断言验证什么？
2. `chunk_index` 由哪个函数加入？
3. 每篇文档的 `chunk_index` 是否全局连续？
4. 不同文档中可以同时存在 `chunk_index = 0` 吗？

## 本次真实运行结果

请填写：

```text
Document 总数：

Chunk 总数：

最长或 Chunk 数量最多的文档：

每个来源统计之和是否等于 Chunk 总数：

程序是否出现 Traceback：

程序是否出现 AssertionError：
```

## 当前真实数据流

请补全：

```text
docs_raw/*.md
→ ______________________________
→ Documents
→ ______________________________
→ Chunks
→ 按 ___________________________ 统计
→ 输出每篇文档的 Chunk 数量
```

## 展开的完整调用流程

请补全：

```text
docs_raw/
→ load_markdown_directory()
→ 遍历 Markdown 文件
→ ______________________________
→ 读取 UTF-8 原始文本
→ ______________________________
→ 分离 YAML Front Matter 和正文
→ yaml.safe_load()
→ ______________________________
→ 校验 Metadata
→ 添加 source 和 file_type
→ Document
→ 汇总为 Documents
→ ______________________________
→ 遍历 Documents
→ ______________________________
→ 切分 content
→ 复制 Metadata
→ 添加 chunk_index
→ Chunk
→ extend()
→ 全部 Chunks
```

## 模块职责复习

请分别用一句话说明。

```text
load_markdown_directory()：

load_markdown()：

parse_markdown_content()：

validate_metadata()：

split_document()：

split_documents()：

main()：
```

## 为什么需要检查路径和文件

回答：

1. 为什么读取文件前需要检查路径是否存在？
2. 为什么还需要检查路径是文件还是目录？
3. 文件不存在时应该抛出什么类型的异常？
4. 目录路径实际是普通文件时应该如何处理？
5. 这些检查应该由调用者重复完成，还是由 Loader 统一完成？
6. 检查的目的只是避免程序崩溃吗？
7. 明确异常信息对调试有什么作用？

## 当前阶段的测试层次

回答：

1. `test_chunker.py` 主要属于单元测试还是集成测试？
2. 使用真实 Markdown 的测试属于什么类型？
3. `main.py` 当前更接近单元测试还是集成冒烟测试？
4. 为什么不能只运行 `main.py` 而完全不写独立测试？
5. 为什么新增功能后还要重新运行旧测试？

## 当前已完成能力

请勾选实际完成的部分：

```text
[ ] 单个 Markdown 文件读取
[ ] YAML Front Matter 分离
[ ] Metadata 校验
[ ] 目录批量加载
[ ] 单个 Document 切分
[ ] 多个 Documents 批量切分
[ ] 真实知识库整体切分
[ ] 按 source 统计 Chunk 数量
[ ] Embedding
[ ] ChromaDB
[ ] 相似度检索
[ ] Ollama 问答
[ ] 来源追溯回答
```

## 当前边界

回答：

1. 当前是否已经生成向量？
2. 当前是否已经将 Chunk 存入数据库？
3. 当前是否能接收用户问题？
4. 当前是否能检索相关 Chunk？
5. 当前是否能调用 Ollama 生成答案？
6. 当前统计结果是否代表检索质量？
7. 字符级切分有哪些局限？

## 面试复述

尝试不看代码回答：

1. 你如何把 25 篇 Markdown 文档转换成 183 个 Chunk？
2. Loader、Validator 和 Chunker 分别负责什么？
3. 为什么要按 `source` 统计 Chunk 数？
4. 如何验证统计没有遗漏？
5. 为什么每个 Chunk 必须保留 `source` 和 `chunk_index`？
6. 当前数据管线距离真正的 RAG 问答还缺什么？

## 下次开始前复习问题

1. 从 `docs_raw/` 到全部 Chunks 的完整调用链是什么？
2. `documents` 和 `chunks` 分别是什么结构？
3. `chunk_count_by_source` 的键和值分别是什么？
4. `dict.get(source, 0)` 的作用是什么？
5. `items()` 为什么可以拆包为 `source, count`？
6. 为什么需要 `sorted()`？
7. 统计数量之和为什么必须等于 `len(chunks)`？
8. `all()` 的两个完整性断言分别验证什么？
9. 当前已经完成 RAG 流程的哪一段？
10. 下一阶段可能进入哪个模块？
