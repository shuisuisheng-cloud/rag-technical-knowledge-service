---
title: RAG Day 7 Metadata 结构校验
project: 基于 RAG 的个人技术知识库问答服务
system_layer: 知识层 / 文档检索服务
document_type: learning_note
status: in_progress
last_updated: 2026-07-10
tags: [Python, Markdown, YAML, Metadata, Validation, Exception, Testing]
---

# RAG Day 7 Metadata 结构校验

## 今天为什么需要校验 Metadata

Day 6 已经能够解析 YAML，为什么 Day 7 还要继续校验？

“YAML 能够解析”与“Metadata 符合项目规范”有什么区别？

## validate_metadata() 的职责

这个函数接收什么？

返回什么？

它不应该负责哪些事情？

## 完整数据流

从目录路径开始，写出完整流程：

目录路径
→
→
→
→
→ documents 列表

## 为什么 metadata 参数标注为 object

`yaml.safe_load()` 可能返回哪些类型？

为什么不能在校验前直接假设它一定是字典？

校验通过后，为什么返回类型可以写成 `dict`？

## 第一层：字典类型检查

为什么先使用：

```python
isinstance(metadata, dict)
```

如果 Metadata 是列表或字符串，会抛出什么异常？

为什么这里使用 `TypeError`？

## 第二层：必需字段检查

当前七个必需字段是什么？

```text
title
project
system_layer
document_type
status
last_updated
tags
```

为什么 `source` 和 `file_type` 不属于 YAML 必需字段？

## field not in metadata 的含义

下面两种写法有什么区别？

```python
field not in metadata
```

```python
metadata.get(field) is None
```

当前阶段为什么选择第一种？

## 第三层：status 校验

当前允许哪些 status？

为什么使用集合保存允许状态？

为什么校验器不能自动把 `verify` 修改为 `verified`？

不合法时为什么使用 `ValueError`？

## 第四层：tags 类型校验

规范中的 tags 应写成什么形式？

```yaml
tags: [Python, MQTT, Linux]
```

下面这种写法解析后是什么类型？

```yaml
tags: Python
```

为什么 tags 必须是列表？

## 为什么 status 和 tags 校验必须放在 for 循环外

如果把它们放进必需字段循环中，会出现哪些问题？

为什么必须先确认七个字段全部存在，再访问：

```python
metadata["status"]
metadata["tags"]
```

## TypeError 与 ValueError 的区别

结合今天的代码解释：

### TypeError

适用于哪些情况？

### ValueError

适用于哪些情况？

## source 字段在错误定位中的作用

为什么错误信息必须包含 source？

如果同时加载 100 篇文档，但错误信息只写“缺少 title”，会有什么问题？

## 独立测试结果

### 完整字典

输入特点：

预期结果：

实际结果：

### 缺少 title

预期异常：

实际结果：

### 缺少 tags

预期异常：

实际结果：

### Metadata 是列表

预期异常：

实际结果：

### Metadata 是字符串

预期异常：

实际结果：

### status 非法

预期异常：

实际结果：

### tags 是字符串

预期异常：

实际结果：

## 为什么测试代码需要 try/except

如果第一组异常用例抛错后没有捕获，会发生什么？

为什么测试脚本需要继续运行剩余用例？

## 真实批量加载验证

本次共加载多少篇 Markdown？

运行的命令是什么？

真实文档为什么能够全部通过？

这一步与单独测试 `validate_metadata()` 有什么区别？

## 当前 validate_metadata() 的校验顺序

写出完整顺序：

Metadata 类型
→
→
→
→ 返回 Metadata

为什么这个顺序不能随意交换？

## 今日遇到的问题

记录今天实际出现的错误：

1. 终端 `python -c` 测试命令为什么失败？
2. 为什么后来改为独立测试文件？
3. `parse_markdown_content()` 调用参数出现了什么问题？
4. status 和 tags 的缩进最初有什么问题？
5. 错误信息最初缺少了什么定位信息？

## 当前还没有实现的校验

至少写出四项，例如：

- 字符串字段是否为空；
- tags 中每个元素是否都是字符串；
- last_updated 是否符合日期格式；
- status 与 document_type 是否存在组合约束；
- 是否允许未知的额外字段；
- 单篇坏文档是否跳过并继续批量加载；
- 自动化测试框架；
- 错误汇总报告。

## 如果没有 YAML Front Matter 会怎样

`parse_markdown_content()` 会返回什么？

进入 `validate_metadata()` 后会发生什么？

这是否符合当前 `docs_raw` 的管理规则？

## 如果从零重写，第一步做什么

应该先设计哪些规则？

为什么应该先确定数据规范，再写 `if` 判断？

## 我的理解与复述

### 1. 为什么外部 YAML 数据不能直接信任？

### 2. 为什么先检查类型，再检查字段？

### 3. 为什么字段存在不代表字段值一定合法？

### 4. TypeError 和 ValueError 在本功能中怎样区分？

### 5. 为什么独立测试通过后还必须测试真实批量加载？

## 后续计划