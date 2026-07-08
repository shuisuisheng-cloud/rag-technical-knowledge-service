---
title: RAG Day 6 YAML Metadata 解析
project: 基于 RAG 的个人技术知识库问答服务
system_layer: 知识层 / 文档检索服务
document_type: learning_note
status: completed
last_updated: 2026-07-07
tags: [Python, Markdown, YAML, PyYAML, Metadata, Parsing]
---

# RAG Day 6：YAML Metadata 解析

## 今天为什么需要解析 YAML Metadata
Metadata 需要用于后续按项目、文档类型和验证状态过滤资料；正文则用于文本切分、向量化和语义检索。将两者分开可以避免 YAML 字段污染正文向量，同时支持来源追溯和可信检索。
## YAML Front Matter 是什么
YAML Front Matter 是 Markdown 文件最顶部、由一对 --- 包围的结构化文档信息。它通常保存标题、所属项目、文档类型、验证状态、更新时间和标签，不属于真正的正文。
## parse_markdown_content() 的职责
函数load_markdown()读取的字符串切割成Metadata和正文内容，正文以字符串形式返回，Metadata以字典形式返回
## load_markdown() 的职责变化
接收 Markdown 文件路径，检查文件是否存在，按 UTF-8 读取完整文本，调用 parse_markdown_content() 分离正文和 YAML，再补充 source 与 file_type，最终返回一个统一的 document 字典。
## load_markdown_directory() 为什么不需要修改
因为这个函数只用负责调用load_markdown函数来将每个md文件单个处理就行
## 输入与输出

### parse_markdown_content()

输入：load_markdown将md文件处理后的字符串

输出：字符串正文和字典Metadata

### load_markdown()

输入：文件名称

输出：字典(包含正文和文件Metadata)

## 完整数据流
目录路径
→ load_markdown_directory() 找到多个 .md 路径
→ 循环调用 load_markdown()
→ read_text() 得到 raw_text
→ parse_markdown_content()
→ 得到 content 和 parsed_metadata
→ 补充 source 和 file_type
→ 组成 document 字典
→ append 到 documents 列表
→ 返回 documents
## raw_text、yaml_text、content 分别是什么
raw_text是md文件的所有文本的字符串，yaml_text是切割出的Metadata部分，content表示的是正文部分
## tuple[str, dict] 表示什么
表示分别返回字符串类型和字典类型的变量
## 元组拆包是什么
元组拆包是用多个变量分别接收函数返回的多个值。
## split("---", 2) 的作用
将文本以---来分割两次
## 为什么不能直接使用 split("---")
split("---") 会分割所有出现的 ---，可能破坏正文中合法的横线。split("---", 2) 表示最多分割两次，只分出开头、YAML 和其余全部正文。
## parts[0]、parts[1]、parts[2] 分别是什么
part[0]是空文本,part[1]是Metadata部分,part[2]是正文部分
## yaml.safe_load() 的作用
将这个文本转成字典
## 为什么使用 safe_load() 而不是 load()
yaml.safe_load() 只解析字符串、数字、列表、字典等普通数据类型。直接使用不受限制的 YAML 加载方式可能构造额外的 Python 对象，处理外部文档时风险更高，因此知识库使用 safe_load()。
## 为什么要写 yaml.safe_load(yaml_text) or {}
因为可能有的文件Metadata部分没有内容，所以要返回字典或者空字典
## 没有 YAML 时怎样处理
返回空字典
## YAML 缺少结束分隔符时怎样处理
如果文本以 --- 开头，但不能分成三部分，则主动抛出 ValueError，函数立即终止，不会再返回正文和空字典
## parsed_metadata 中新增了哪些字段
parse_markdown_content()
从 YAML 得到：
title、project、system_layer、document_type、status、last_updated、tags

load_markdown()
额外加入：
source、file_type
## source 和 file_type 来自哪里
source来自文件来源路径，file_type来自本身的md文件类型
## 为什么使用 metadata.get("title")
因为可能有的文件Metadata没有title
## 三种测试结果

### 正常 YAML
返回正文内容字符串和字典
### 没有 YAML
返回正文内容和空字典
### YAML 格式不完整
报错以及返回md文件全部文本内容和空字典
## 今日遇到的问题
1. 一开始把整个 raw_text 传给 yaml.safe_load()，正确做法是只解析 parts[1]。
2. 忘记从 parts[2] 中取得正文。
3. 没有 YAML 的分支错误使用了尚未创建的 yaml_text。
4. yaml.safe_load() 在空 YAML 时可能返回 None，因此增加 or {}。
5. 有 YAML 的分支最初忘记 return。
6. 将元组拆包误解成拆分 Metadata 内部字段。
## 当前还没有实现的功能
1. 尚未验证 YAML 解析结果是否一定为字典；
2. 尚未校验 title、project、status 等必需字段；
3. 尚未在批量加载时跳过单篇坏文档并继续处理；
4. 尚未递归加载子目录；
5. 尚未支持 TXT 和 PDF；
6. 尚未实现文本切分；
7. 尚未编写自动化测试。
## 如果从零重写，第一步做什么
先写数据流，然后构造 parse_markdown_content() 函数
## 我的理解与复述

### 1. 为什么要把 YAML 和正文分开？
方便之后单独处理正文和YAML
### 2. parse_markdown_content() 和 load_markdown() 的职责有什么区别？
一个是将字符串返回Metadata字典和正文字符串，一个是返回正文和Metadata组成的字典
### 3. 为什么批量加载函数不需要重新修改？
因为批量加载的内核就是单次单个处理每个md文件，应用的函数是一样的
### 4. yaml.safe_load(yaml_text) or {} 中的 or {} 有什么作用？
如果YAML没有内容则返回空字典
### 5. 为什么正文中不能继续保留 YAML Front Matter？
正文之后会被切分并生成向量。如果保留 YAML，标题、标签、状态等管理字段会重复进入文本块，干扰语义相似度并浪费向量空间。Metadata 应作为独立字段用于过滤和来源追溯，正文只保留真正需要检索和回答的技术内容