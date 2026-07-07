---
title: RAG Day 6 YAML Metadata 解析
project: 基于 RAG 的个人技术知识库问答服务
system_layer: 知识层 / 文档检索服务
document_type: learning_note
status: in_progress
last_updated: 2026-07-07
tags: [Python, Markdown, YAML, PyYAML, Metadata, Parsing]
---

# RAG Day 6：YAML Metadata 解析

## 今天为什么需要解析 YAML Metadata

## YAML Front Matter 是什么

## parse_markdown_content() 的职责

## load_markdown() 的职责变化

## load_markdown_directory() 为什么不需要修改

## 输入与输出

### parse_markdown_content()

输入：

输出：

### load_markdown()

输入：

输出：

## 完整数据流

## raw_text、yaml_text、content 分别是什么

## tuple[str, dict] 表示什么

## 元组拆包是什么

## split("---", 2) 的作用

## 为什么不能直接使用 split("---")

## parts[0]、parts[1]、parts[2] 分别是什么

## yaml.safe_load() 的作用

## 为什么使用 safe_load() 而不是 load()

## 为什么要写 yaml.safe_load(yaml_text) or {}

## 没有 YAML 时怎样处理

## YAML 缺少结束分隔符时怎样处理

## parsed_metadata 中新增了哪些字段

## source 和 file_type 来自哪里

## 为什么使用 metadata.get("title")

## 三种测试结果

### 正常 YAML

### 没有 YAML

### YAML 格式不完整

## 今日遇到的问题

## 当前还没有实现的功能

## 如果从零重写，第一步做什么

## 我的理解与复述

### 1. 为什么要把 YAML 和正文分开？

### 2. parse_markdown_content() 和 load_markdown() 的职责有什么区别？

### 3. 为什么批量加载函数不需要重新修改？

### 4. yaml.safe_load(yaml_text) or {} 中的 or {} 有什么作用？

### 5. 为什么正文中不能继续保留 YAML Front Matter？