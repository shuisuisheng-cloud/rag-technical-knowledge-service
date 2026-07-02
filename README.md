# 基于 RAG 的个人技术知识库问答服务

> 面向 EdgeAIoT 边缘智能系统的技术文档检索与知识问答服务。

## 项目定位

本项目是 EdgeAIoT 边缘智能系统系列项目中的知识层 / 文档检索服务。

项目计划使用 Python、Ollama、ChromaDB 和 FastAPI，对 STM32 终端文档、Linux 网关开发记录、算法笔记、实验记录和故障排查资料进行统一接入、解析、切分、向量化与检索。

本项目不是孤立的 ChatPDF，而是为 Orange Pi + STM32 边缘 AIoT 管控系统中的 Agent 提供设备说明、项目文档、调试记录和故障排查知识。

## 在 EdgeAIoT 系统中的位置

EdgeAIoT 系列项目由四个层级组成：

1. 总控层 / Agent 控制层
   Orange Pi + STM32 边缘 AIoT 管控系统

2. 通信层 / 数据中枢
   Linux-STM32 物联网边缘网关

3. 设备层 / 终端节点
   STM32 环境感知与执行控制终端

4. 知识层 / 文档检索服务
   基于 RAG 的个人技术知识库问答服务

本项目通过 REST API 为 Orange Pi Agent 提供知识检索能力，不直接负责传感器采集、MQTT 数据转发或执行器控制。

## V1 目标

V1 计划实现：

* Markdown、TXT 和 PDF 技术文档接入；
* 文档内容解析与统一数据结构；
* 长文本切分与来源 Metadata 保留；
* Ollama Embedding 向量化；
* ChromaDB 向量存储与相似度检索；
* 基于检索结果的 RAG 问答；
* 回答来源追溯；
* FastAPI REST API；
* 为后续 Orange Pi Agent 提供知识查询接口。

## 计划接入的知识资料

* STM32 环境感知与执行控制终端项目文档；
* Linux-STM32 物联网边缘网关开发与调试记录；
* LeetCode 与算法理解笔记；
* 科研项目和 MATLAB 实验记录；
* 课程笔记与代码说明；
* EdgeAIoT 系统故障排查记录。

## 计划技术栈

* Python
* Ollama
* ChromaDB
* FastAPI
* Markdown / TXT / PDF
* REST API
* Git / GitHub

## 计划数据流程

原始技术文档
→ 文档解析
→ 统一 Document 数据结构
→ 文本切分
→ Embedding 向量化
→ ChromaDB 存储
→ 相似度检索
→ RAG 回答
→ FastAPI 对外提供服务

## 当前进度

* [x] 明确项目定位和 V1 功能边界
* [x] 初始化 GitHub 仓库
* [x] 建立原始知识文档目录
* [x] 编写首批 EdgeAIoT 项目概览文档
* [x] 建立 Overview 与每日详细记录两类文档
* [x] 为知识文档增加 Metadata
* [x] 建立基础 Document 数据结构
* [x] 实现单个 Markdown 文档读取
* [x] 实现目录内 Markdown 文档批量读取
* [x] 完成目录不存在和路径非目录的异常检查
* [ ] 实现文本切分
* [ ] 实现 Embedding 向量化
* [ ] 接入 ChromaDB
* [ ] 实现相似度检索
* [ ] 实现 RAG 问答
* [ ] 封装 FastAPI 接口
* [ ] 接入 Orange Pi Agent

## 当前仓库结构

```text
rag-technical-knowledge-service/
├── README.md
├── .gitignore
├── docs_raw/
│   ├── stm32_terminal_overview.md
│   ├── stm32_v2_day01_hardware_validation.md
│   ├── linux_gateway_overview.md
│   ├── linux_gateway_day46_command_execution.md
│   └── leetcode_day05_two_sum.md
└── notes/
```

## 当前开发原则

项目的每个版本需要同时满足：

1. 功能能够运行；
2. 能够讲清楚、修改并复现核心逻辑。

知识文档必须区分已实现、软件验证、模拟验证和规划中的内容，避免将未经验证的功能写成完成状态。
