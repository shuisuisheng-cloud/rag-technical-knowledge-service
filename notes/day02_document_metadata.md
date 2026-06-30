---

title: RAG Day 2 文档粒度与 Metadata 学习记录
project: 基于 RAG 的个人技术知识库问答服务
system_layer: 知识层 / 文档检索服务
document_type: learning_note
status: completed
last_updated: 2026-06-30
tags: [RAG, Metadata, Markdown, Knowledge_Source, EdgeAIoT]
-----------------------------------------------------------

# RAG Day 2：文档粒度与 Metadata

## 今日核心概念

RAG 知识库中的文档不能只保存正文，还需要保存能够描述文档身份、所属项目、验证状态和更新时间的 Metadata。

文档需要根据用途划分粒度，不能把所有项目内容全部写进一篇很长的文件。

## 文档类型

### Project Overview

用于记录项目定位、系统层级、当前能力、输入输出和整体开发状态。

例如：

* STM32 环境感知与执行控制终端项目概览；
* Linux-STM32 物联网边缘网关项目概览。

### Daily Development Record

用于记录某一天完成的具体功能、修改模块、输入输出、验证结果和遗留问题。

例如：

* STM32F407VET6 Day 1 核心硬件验证；
* Linux 网关 Day 46 控制命令执行。

### Algorithm Learning Note

用于记录算法题型、核心思路、数据流、控制流、复杂度和常见错误。

例如：

* LeetCode Day 5 两数之和。

### Troubleshooting Record

用于记录问题现象、排查过程、根本原因、解决方法和验证结果。

## 当前已有知识资料

本地 Windows 目录：

`E:\笔记`

当前包含：

* `stm32`：STM32 每日开发、硬件验证、代码理解和问题记录；
* `mqtt-iot-gateway`：Linux 网关每日开发、命令、模块与异常记录；
* `leetcode`：算法题目、解题过程、错误和总结；
* `rag`：RAG 项目每日开发与学习记录；
* `codex`：AI/Codex 辅助开发记录，需要经过验证和筛选后再接入。

在 WSL 中，后续可以通过 `/mnt/e/笔记` 访问这些资料。

## 知识资料使用原则

1. 原始资料保留在本地，不直接全部上传到公开 GitHub 仓库。
2. GitHub 的 `docs_raw` 只保存经过脱敏和检查的示例文档。
3. 不将密码、API Key、Token 或私人信息写入公开仓库。
4. AI/Codex 生成的内容必须经过真实验证，不能直接标记为已完成。
5. 知识内容需要区分已验证、软件验证、学习记录、未验证和已过期状态。
6. 如果旧结论被后续开发推翻，需要更新 Metadata 或标记为 deprecated。
7. 每天开始 RAG 项目前，需要检查 STM32、Linux 网关和 LeetCode 的最新进展，并提醒同步对应知识文档。

## 当前 Metadata 字段

* `title`：文档标题；
* `project`：所属项目；
* `system_layer`：在 EdgeAIoT 系统中的层级；
* `document_type`：文档类型；
* `status`：验证或开发状态；
* `last_updated`：最后更新时间；
* `tags`：关键词标签。

## Metadata 的作用

Metadata 可以帮助系统：

* 判断文档属于哪个项目；
* 按系统层级进行分类；
* 区分概览、每日记录和故障记录；
* 追溯答案来源；
* 过滤未经验证或已经过期的内容；
* 提高后续向量检索结果的准确性。

## 今日结论

个人每天的开发笔记和错误记录是高价值的 RAG 知识源。

但原始资料不能不加筛选地全部公开或直接向量化。需要通过文档分类、Metadata、验证状态和隐私过滤，把原始笔记整理成准确、可检索和可追溯的技术知识。
