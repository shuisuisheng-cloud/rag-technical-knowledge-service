---
title: RAG Day 3 Markdown 文档加载器
project: 基于 RAG 的个人技术知识库问答服务
system_layer: 知识层 / 文档检索服务
document_type: learning_note
status: completed
last_updated: 2026-07-01
tags: [Python, Markdown, Document Loader, Path, Dictionary]
---

# RAG Day 3：Markdown 文档加载器

## 今天为什么需要 Document Loader
为了将文件内容读取出来，以方便后续进行处理
## document_loader.py 的职责
接收 Markdown 文件路径，检查文件是否存在，读取正文，并把正文和来源信息组织成统一的 document 字典后返回。
## main.py 的职责
作为程序入口，指定待读取文件，调用 load_markdown()，接收返回结果并打印部分内容进行验证。
## 输入与输出
输入文件路径，输出文件内容 路径 类型
## 数据流

## document 字典的结构
document = {
    "content": text,
    "metadata": {
        "source": str(file),
        "file_type": "markdown"
        }
    }
## content、metadata、source、file_type 分别是什么
content是文件里面的具体内容，metadata 是文档的附加信息，当前保存来源路径 source 和文件类型 file_type。
## print 和 return 的区别
print() 只把内容显示在终端，主要用于观察和调试；return 会把结果交还给调用函数的代码，使 main.py 或后续模块能够继续使用这个数据。
## Path 类和具体 Path 对象的区别
Path类是指将文件路径字符串提取成Path类型,Path对象是指该文件
## 正常路径测试结果
打印文件内容前200个字符,同时成功打印文档来源和文件类型，说明 main.py 能正确访问嵌套字典中的 metadata。
## 文件不存在时发生了什么
当路径不存在时，load_markdown() 主动抛出 FileNotFoundError，程序停止继续读取，并在报错信息中显示不存在的路径。
## 今日遇到的问题
错误：调用 Path.exists() 时缺少 self
原因：对 Path 类调用方法，没有对具体的 file 对象调用
修正：使用 file.exists()
## 当前还没有实现的功能
尚未把 Markdown 顶部的 YAML Metadata 与正文分离；
尚未批量读取 docs_raw 目录中的多个文件；
尚未支持 TXT 和 PDF；
尚未实现文本切分；
main.py 还没有使用 try/except 友好处理异常；
尚未编写自动化测试。
## 如果从零重写，第一步做什么
1. 先确定函数的输入和输出；
2. 把字符串路径转成 Path 对象；
3. 检查文件是否存在；
4. 按 UTF-8 读取正文；
5. 组织 content 和 metadata；
6. return document。

load_markdown() 的输入和输出分别是什么？
输入是字符串形式的 Markdown 文件路径，输出是包含 content 和 metadata 的字典。

为什么要 return document，而不是只在函数里 print(text)？
因为加载器需要把读取结果交给调用者继续处理。如果只在函数里 print(text)，main.py 就无法获得文档对象，也无法把它继续交给文本切分或向量化模块。

document["metadata"]["source"] 是怎样一层层访问到路径的？
先是键"metadata"之后是这个字典里面的"source"

Path.exists() 和 file.exists() 为什么一个报错、一个正确？
Path 是类，相当于创建路径对象的模板；file = Path(file_path) 得到具体的 Path 对象。Path.exists() 没有具体对象，因此缺少 self；调用 file.exists() 时，Python 会自动把 file 作为 self 传入。