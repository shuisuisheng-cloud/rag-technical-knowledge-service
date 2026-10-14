---
title: "RAG Day 22：ChromaDB 知识库结构一致性审计"
project: "RAG 知识库服务"
system_layer: "知识层 / RAG 应用服务层"
document_type: "learning_note"
status: "development_verified"
last_updated: "2026-10-14"
tags:
  - Python
  - RAG
  - ChromaDB
  - VectorDatabase
  - Pydantic
  - DataValidation
  - Debug
  - Persistence
---

# RAG Day 22：ChromaDB 知识库结构一致性审计

## 1. 今日目标与真实结果

开发文件：`src/audit_knowledge_base.py`

审计对象：ChromaDB Collection `technical_knowledge`

本次只读取数据库，不修改记录，不重新生成 Embedding。

**真实运行结果：**

| 指标 | 结果 |
|---|---:|
| total | 655 |
| checked | 655 |
| invalid_records | [] |
| duplicate_ids | [] |
| embedding_dimension_errors | [] |

**结论：Day 22 当前审计规则覆盖的 655 条 Record 结构检查 PASS。**

这是本人 WSL 本地执行的真实结果，不是 Mock 测试。

但不能因此认定整个 RAG V1 已经冻结，也不能证明所有 Embedding 都与当前 Markdown 正文一致。

历史验收边界：

- 首轮 47 份文档、610 条 Record 曾完成较完整读回验收。
- 随后补录至 632 条，但未执行同等级的完整读回。
- Day 22 实测当前 Collection 为 655 条，已完成本次结构规则的全量审计。
- 尚未验证当前源文件与 655 条索引的内容新鲜度。

## 2. 本次审计的数据结构

`collection.get()` 返回一个字典，其字段内包含按索引对应的列表或数组。

主要字段：

| 字段 | 作用 |
|---|---|
| `ids` | 每条 Chunk 的唯一标识 |
| `documents` | Chunk 正文 |
| `metadatas` | 来源、Chunk 编号等元数据 |
| `embeddings` | Embedding 向量 |

同一个索引位置对应同一条记录。

例如，索引 0 的 ID、document、metadata 和 embedding 属于同一条 Record。

遍历时使用 `enumerate(records["ids"])`，再通过 `index` 访问另外三个字段。

不能直接遍历 `records` 并将得到的字符串键名当成 Record。

## 3. 审计程序设计

函数接口：

`audit_collection(collection, batch_size=100) -> dict`

整体步骤：

1. 验证 `batch_size` 为正整数，并排除 bool。
2. 使用 `collection.count()` 获取数据库当前记录数量。
3. 使用 `range(0, total, batch_size)` 分批遍历。
4. 调用 `collection.get(limit=..., offset=..., include=...)` 读取数据。
5. 检查各字段是否存在、列表长度是否一致。
6. 使用 `enumerate()` 遍历每条 ID。
7. 检查 ID 合法性和重复情况。
8. 检查正文是否为空。
9. 通过 Pydantic 校验 metadata。
10. 验证 ID 与 metadata 的对应关系。
11. 检查 Embedding 是否为预期 1024 维。
12. 汇总错误列表并返回审计报告。

本次审计属于只读流程，禁止为了修复问题直接执行 `collection.add()`、`update()`、`delete()`。

## 4. 核心 Python 知识

### dict 与 list

`records` 是字典。

`records["ids"]` 是 ID 列表。

`records["ids"][index]` 才是对应索引的某一个 ID。

需要区分外层字典、内层列表以及单个元素。

### enumerate()

`enumerate()` 返回索引和元素。

例如，遍历 `["A", "B", "C"]`，索引从 0 开始，元素依次为 A、B、C。

使用同一索引可以访问其他对齐列表中的对应字段。

### set

`set()` 用于保存已经检查过的 ID。

- 首次出现：使用 `seen_id.add(record_id)`。
- 再次出现：记录重复 ID。

`set` 使用 `.add()`，`list` 使用 `.append()`。

### break 与 continue

- `break`：终止当前循环。
- `continue`：结束本次循环，继续下一条。

本项目希望尽量审计全部记录，发现重复 ID 后不能直接结束整个批次。

### 字典赋值和比较

- `report["duplicate_ids"] = duplicate_ids`：赋值。
- `report["duplicate_ids"] == duplicate_ids`：比较。

对不存在的键直接读取可能抛出 `KeyError`。

## 5. Pydantic metadata 校验

本次定义了 `MetadataItem(BaseModel)`。

主要字段：

- `source: str`：来源必须为合法的非空字符串。
- `chunk_index: int`：必须为非负整数。
- `Field`：提供类型、范围、长度等约束。
- `ConfigDict(str_strip_whitespace=True)`：处理字符串首尾空白。

`MetadataItem.model_validate(metadata)` 可以将 ChromaDB 返回的 dict 交给 Pydantic 验证。

验证成功返回 `MetadataItem` 实例；验证失败抛出 `ValidationError`。

注意：

`isinstance(metadata, MetadataItem)` 与 `MetadataItem.model_validate(metadata)` 不相同。前者检查对象是否已经是模型实例，后者按照模型规则验证输入。

`strict=True` 会拒绝不符合声明类型的值。例如整数 `3` 可以作为 chunk_index，而字符串 `"3"` 和布尔值 `True` 不可以。

### ID 与 metadata 对应关系

本项目的 ID 规则为：

`source::chunk_<index>`

因此，metadata 验证通过后，还需要根据 source 和 chunk_index 重新构造预期 ID，并与实际 record_id 比较。

单独验证 ID 和 metadata 各自合法，不代表它们一定相互对应。

## 6. 今日真实 Debug 记录

### 问题 A：ChromaDB include 参数错误

实际错误：

`ValueError: Expected include item ... got documents  in get`

原因：源文件中的 `"documents "` 存在不易察觉的末尾空格。

使用 Python `ast`、`repr()`、`len()` 检查磁盘文件，确认字符串长度为 10，合法的 `"documents"` 应为 9。

解决：重新输入字段名，保存后运行成功。

### 问题 B：KeyError

实际错误：

`KeyError: 'duplicate_ids'`

原因：误将字典赋值写成 `==` 比较，导致尝试读取尚未存在的键。

解决：使用 `=` 完成报告字段赋值。

### 问题 C：VS Code 导入提示

Pylance 曾提示无法解析 `chromadb`，但 WSL `.venv` 中执行 import 成功。

排查方向：Python 解释器、WSL Remote 环境、Pylance 状态。

后续编辑器警告恢复正常，没有重新安装库。

### 问题 D：数据结构和校验顺序

开发过程中修正了：

- `set.append()` 与 `set.add()` 混淆。
- 遍历外层 dict 与遍历 ids 列表混淆。
- `break` 导致后续数据未经检查。
- 无效 ID 应先记录并跳过，不应加入 seen_id。
- `checked` 应统计实际检查到的记录。
- metadata 类型校验与 Pydantic 数据校验的区别。

## 7. 本次审计没有证明什么？

本次通过的是结构审计。

尚未完整验证：

- 数据库正文是否等于最新 Markdown 重新 Chunk 后的正文。
- metadata 是否与当前 Markdown 源文件的最新内容一致。
- 向量是否确实由当前正文及预期模型生成。
- 向量内部是否包含 NaN 或 Infinity 等无效数值。
- 修改或删除源文件后，旧索引能否同步更新。

因此 Day 23 需要进一步检查数据库索引与当前源文件的一致性。

## 8. 个人掌握程度（如实记录）

目前能够在实际工程中使用并理解：

- `range()` 分批遍历。
- `enumerate()` 对齐字段。
- `set` 记录已出现 ID。
- `dict` 汇总报告。
- 基本条件检查与异常记录。

但以下内容仍然参考 ChatGPT 示例，尚未证明可以闭卷独立手写：

- `BaseModel` 和 Pydantic 模型定义。
- `Field` 参数约束。
- `ConfigDict`。
- `model_validate()`。
- `ValidationError` 的捕获与处理。
- 数据审计边界条件的完整设计。

实际代码运行成功不等于个人已经独立掌握全部实现。

## 9. 企业面试复测范围

后续复习和正式面试重点包括：

- dict、list、set 的区别和操作方法。
- enumerate、zip、索引对齐。
- break、continue 对统计和遍历的影响。
- Python `=`、`==` 与 KeyError。
- Pydantic BaseModel、Field、ConfigDict、model_validate。
- 静态编译检查与运行时错误的区别。
- ChromaDB get、query、add 的职责区别。
- ID 唯一性、metadata 一致性、Embedding 维度。
- 为什么结构审计通过仍可能存在过期正文。
- 根据陌生 Traceback 独立定位错误。

面试采用企业技术面风格，不仅考定义，还包括闭卷解释、现场编写、代码阅读和 Debug。

## 10. 下一阶段

**Day 22：已完成结构审计。**

**Day 23：尚未开始实际代码实现。**

下一阶段计划复用 Markdown Loader、Chunker 与 `prepare_chunk_records()`，通过只读方式比较当前源文档和 ChromaDB 索引，区分缺失、正文变化、metadata 变化及历史遗留记录。

暂不修改当前入库程序，不重建正式 Collection。

RAG V1 仍处于冻结前工程验收阶段，后续按实际需求决定是否继续扩展。
