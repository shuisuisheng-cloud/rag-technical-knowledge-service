---
title: RAG Day 4 Markdown 文档批量加载
project: 基于 RAG 的个人技术知识库问答服务
system_layer: 知识层 / 文档检索服务
document_type: learning_note
status: completed
last_updated: 2026-07-02
tags: [Python, Markdown, Directory Loader, Path, List, glob]
---

# RAG Day 4：Markdown 文档批量加载

## 今天为什么需要批量加载
因为第三天只能读取单个文件，但是文件很多，不可能一次一次调用load_markdown文件，所以需要写一个批量调用的函数，通过批量读取之后调用load_markdown
## load_markdown() 的职责
负责读取单个 Markdown 文件，检查路径是否存在，并将正文与来源信息组织成一个 document 字典后返回
## load_markdown_directory() 的职责
负责读取文件夹，之后把文件夹里面的md文件遍历之后，通过调用load_markdown函数把每个文件内容放到整体列表里
## 输入与输出
输入是字符串形式的目录路径；输出是一个 list[dict]，列表中的每个字典代表一篇 Markdown 文档，包含正文和 metadata。
## 完整数据流
 load_markdown_directory() ->调用load_markdown()->将文件添加到list中->返回documents列表
## 为什么要复用单文件加载函数
避免在批量函数中重复编写路径检查、文件读取和字典构造；
单文件读取逻辑只维护一份；
以后 load_markdown() 增加 YAML 解析时，批量函数不用重写。
## list[dict] 表示什么
期望返回值是一个以字典为值的列表
## glob("*.md") 的作用
检索所有以.md结尾的文件，当前只查找指定目录的直接子文件，不会递归查找更深层子目录；返回的是多个 Path 对象。
## append() 的作用
将这个文件添加到列表中，append() 直接修改原来的列表，并返回 None。
## sorted() 的作用
将文件排序
## 三种路径测试结果
docs_not_exist
→ 路径不存在
→ FileNotFoundError

README.md
→ 路径存在，但不是目录
→ NotADirectoryError

docs_raw
→ 是有效目录
→ 成功读取 11 篇 Markdown
## 今日遇到的问题

## 当前还没有实现的功能
还没有递归读取子目录；
还没有解析 YAML Metadata；
还没有支持 TXT 和 PDF；
还没有实现文本切分；
某一篇文件读取失败时，还不能跳过该文件继续处理；
还没有自动化测试。
## 如果从零重写，第一步做什么
先确定
输入是什么？
输出是什么？
单文件函数和批量函数分别负责什么？
目录路径 → Path 对象 → 异常检查 → glob → 循环加载 → append → return

## 我的理解与复述

### 1. 为什么批量加载函数要复用单文件加载函数？
批量函数负责找文件和组织列表，单文件函数负责读取一篇文件。复用可以避免重复代码，并保证单文件逻辑只维护一份。
### 2. documents、document、content 分别是什么？
documents：列表，保存多篇文档；
document：字典，表示一篇文档；
content：字符串，保存某一篇文档的完整正文。
### 3. 为什么不能写 documents = documents.append(document)？
因为append这个返回值是None，这样相当于documents是None
### 4. FileNotFoundError 和 NotADirectoryError 有什么区别？
FileNotFoundError：
传入的路径根本不存在，例如 docs_not_exist。

NotADirectoryError：
传入的路径存在，但不是目录，例如 README.md。