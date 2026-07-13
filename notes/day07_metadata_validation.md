---
title: RAG Day 7 Metadata 结构校验
project: 基于 RAG 的个人技术知识库问答服务
system_layer: 知识层 / 文档检索服务
document_type: learning_note
status: completed
last_updated: 2026-07-10
tags: [Python, Markdown, YAML, Metadata, Validation, Exception, Testing]
---

# RAG Day 7 Metadata 结构校验

## 今天为什么需要校验 Metadata

Day 6 已经能够通过 `yaml.safe_load()` 将 YAML 文本解析成 Python 对象，但能够解析不代表数据符合项目规范。

例如，下面的 YAML 都可能被成功解析：

```yaml
status: verify
tags: Python
```

但它们不符合本项目规定：

- `status` 必须属于允许状态集合；
- `tags` 必须是列表；
- Metadata 必须包含规定的必需字段；
- Metadata 根结构必须是字典。

如果不在 Loader 阶段进行校验，错误数据可能继续进入文本切分、向量化、向量数据库和检索流程，导致错误更难定位。

“YAML 能够解析”只表示语法可以被 PyYAML 读取。

“Metadata 符合项目规范”表示解析结果的类型、字段和值都满足当前知识库的数据规则。

## validate_metadata() 的职责

`validate_metadata()` 接收：

- YAML 解析后得到的 Python 对象；
- 当前文档的来源路径 `source`。

它负责：

- 检查 Metadata 是否为字典；
- 检查七个必需字段是否存在；
- 检查 `status` 是否合法；
- 检查 `tags` 是否为列表；
- 校验成功后返回 Metadata 字典。

它不负责：

- 读取 Markdown 文件；
- 分割 YAML 和正文；
- 调用 `yaml.safe_load()`；
- 自动修改错误字段；
- 添加 `source` 和 `file_type`；
- 文本切分和向量化。

## 完整数据流

```text
目录路径
→ load_markdown_directory() 查找并遍历多个 .md 文件
→ load_markdown() 读取单个文件
→ read_text() 得到 raw_text
→ parse_markdown_content() 分离 YAML 和正文
→ yaml.safe_load() 得到 Metadata Python 对象
→ validate_metadata() 校验类型、字段和值
→ load_markdown() 添加 source 和 file_type
→ 组成 document 字典
→ append 到 documents 列表
→ 返回 documents
```

## 为什么 metadata 参数标注为 object

`yaml.safe_load()` 不一定返回字典，还可能返回：

- `dict`
- `list`
- `str`
- `int`
- `float`
- `bool`
- `None`

因此校验前不能直接假设结果一定是字典，参数应标注为：

```python
metadata: object
```

经过：

```python
isinstance(metadata, dict)
```

校验后，程序已经确定 Metadata 是字典，因此函数返回类型可以写成：

```python
-> dict
```

## 第一层：字典类型检查

首先使用：

```python
isinstance(metadata, dict)
```

判断 Metadata 是否为字典。

如果 Metadata 是列表或字符串，则抛出：

```text
TypeError
```

这里使用 `TypeError`，因为传入对象的实际类型不符合函数要求。

例如：

```text
expected=dict
actual=list
```

## 第二层：必需字段检查

当前七个必需字段是：

```text
title
project
system_layer
document_type
status
last_updated
tags
```

`source` 和 `file_type` 不属于 YAML 必需字段，因为它们不是由文档作者在 YAML 中填写的。

它们由 `load_markdown()` 自动补充：

```python
parsed_metadata["source"] = str(file)
parsed_metadata["file_type"] = "markdown"
```

其中：

- `source` 来自当前文件路径；
- `file_type` 由 Markdown Loader 固定设置。

## field not in metadata 的含义

```python
field not in metadata
```

只检查某个字段名是否存在。

例如：

```python
"title" not in metadata
```

表示 Metadata 中完全没有 `title` 键。

而：

```python
metadata.get(field) is None
```

无法区分以下两种情况：

```python
{}
```

和：

```python
{"title": None}
```

前者是字段不存在，后者是字段存在但值为 `None`。

Day 7 当前只检查字段是否存在，因此选择：

```python
field not in metadata
```

字段存在但内容为空，属于后续更严格的值校验。

## 第三层：status 校验

当前允许的状态是：

```text
in_progress
completed
verified
software_verified
sample_verified
```

代码使用集合保存：

```python
allowed_status = {
    "in_progress",
    "completed",
    "verified",
    "software_verified",
    "sample_verified",
}
```

使用集合的原因：

- 状态值不允许重复；
- 不关心状态的排列顺序；
- 能清楚表达“允许值集合”；
- 判断成员是否存在比较直接。

校验方式：

```python
if metadata["status"] not in allowed_status:
```

校验器不能自动把：

```text
verify
```

改成：

```text
verified
```

因为校验器只负责发现错误，不负责猜测作者意图或偷偷修改原始数据。

自动修改可能隐藏源文件中的真实错误，使文档规范逐渐失控。

`status` 类型可能是字符串，但内容不在允许范围内，因此使用：

```text
ValueError
```

## 第四层：tags 类型校验

规范中的 `tags` 应写成列表：

```yaml
tags: [Python, MQTT, Linux]
```

下面的写法：

```yaml
tags: Python
```

会被解析成字符串：

```python
str
```

`tags` 必须是列表，因为一篇文档可能有多个标签，并且后续需要：

- 遍历标签；
- 按标签过滤文档；
- 将多个标签保存到向量数据库 Metadata；
- 判断某个标签是否存在；
- 保持统一的数据结构。

Day 7 只检查 `tags` 是否为列表，还没有检查列表中的每一个元素是否都是字符串。

## 为什么 status 和 tags 校验必须放在 for 循环外

必需字段循环只负责确认七个字段全部存在：

```python
for field in required_fields:
    if field not in metadata:
        raise ValueError(...)
```

只有循环全部执行完，程序才能确定：

```python
metadata["status"]
metadata["tags"]
```

一定存在。

如果把 `status` 和 `tags` 校验放在循环内部：

- 每遍历一个字段都会重复校验；
- 会产生没有意义的重复操作；
- 可能在还没有确认 `status` 或 `tags` 存在时直接访问；
- 可能触发没有经过设计的 `KeyError`；
- 校验顺序会变得混乱。

因此正确顺序是：

```text
先检查全部必需字段
→ 再检查 status
→ 再检查 tags
```

## TypeError 与 ValueError 的区别

### TypeError

表示对象或字段的类型不符合要求。

本项目中的例子：

- Metadata 根结构不是字典；
- `tags` 不是列表。

例如：

```text
expected=dict, actual=list
```

或：

```text
field=tags, expected=list, actual=str
```

### ValueError

表示对象类型基本正确，但内容或值不符合规则。

本项目中的例子：

- 字典缺少必需字段；
- `status` 不属于允许值集合。

例如：

```text
field=title
```

或：

```text
status=verify
```

## source 字段在错误定位中的作用

错误信息必须包含 `source`，用于确定是哪一篇文档校验失败。

如果同时加载 100 篇文档，但报错信息只显示：

```text
缺少 title
```

开发者还需要逐篇打开文件检查。

如果错误信息包含：

```text
source=docs_raw/linux_gateway_day52.md
```

就可以立刻定位并修改对应文件。

因此错误信息不仅要说明“错了什么”，还要说明“哪一个输入出错”。

## 独立测试结果

### 完整字典

输入特点：

- Metadata 是字典；
- 七个必需字段完整；
- `status` 合法；
- `tags` 是列表。

预期结果：

```text
正常返回原 Metadata
```

实际结果：

```text
校验通过
```

### 缺少 title

预期异常：

```text
ValueError
```

实际结果：

```text
Metadata缺少必需字段: source=缺少title.md, field=title
```

### 缺少 tags

预期异常：

```text
ValueError
```

实际结果：

```text
Metadata缺少必需字段: source=缺少tags.md, field=tags
```

### Metadata 是列表

预期异常：

```text
TypeError
```

实际结果：

```text
Metadata不是字典，实际类型为 list
```

### Metadata 是字符串

预期异常：

```text
TypeError
```

实际结果：

```text
Metadata不是字典，实际类型为 str
```

### status 非法

测试值：

```text
verify
```

预期异常：

```text
ValueError
```

实际结果：

```text
Metadata状态非法: status=verify
```

### tags 是字符串

测试值：

```python
"tags": "Python"
```

预期异常：

```text
TypeError
```

实际结果：

```text
field=tags, expected=list, actual=str
```

## 为什么测试代码需要 try/except

如果异常用例没有使用 `try/except`，程序遇到第一条异常后会立即终止。

后面的测试用例不会继续运行。

使用：

```python
try:
    ...
except (TypeError, ValueError) as error:
    ...
```

可以捕获当前测试用例的预期异常，打印结果，然后继续测试剩余用例。

这样一次运行可以检查：

- 正常输入；
- 多种类型错误；
- 多种值错误；
- 不同错误信息。

## 真实批量加载验证

本次真实批量加载了：

```text
18 篇 Markdown
```

运行命令：

```bash
python src/main.py
```

真实文档能够全部通过，说明当前 `docs_raw` 中的文档：

- Metadata 根结构都是字典；
- 七个必需字段完整；
- `status` 都属于允许集合；
- `tags` 都是列表。

独立测试只验证：

```text
validate_metadata() 函数本身
```

真实批量加载验证的是完整集成链路：

```text
目录扫描
→ 文件读取
→ YAML 解析
→ Metadata 校验
→ Document 构造
→ Documents 列表
```

因此独立测试通过后，仍然必须运行真实批量加载。

## 当前 validate_metadata() 的校验顺序

```text
检查 Metadata 根类型是否为 dict
→ 检查七个必需字段是否全部存在
→ 检查 status 是否属于允许集合
→ 检查 tags 是否为 list
→ 返回 Metadata
```

这个顺序不能随意交换。

例如，在没有确认 `status` 和 `tags` 存在前直接访问：

```python
metadata["status"]
metadata["tags"]
```

可能产生 `KeyError`。

先检查类型，也可以防止对列表或字符串执行字典字段操作。

正确顺序能够保证：

- 每一步的前置条件已经满足；
- 抛出的异常更准确；
- 错误信息更容易理解；
- 不会出现意外异常。

## 今日遇到的问题

### 1. 终端 python -c 测试失败

一开始在终端中使用了复杂的：

```bash
python -c "..."
```

但多条 Python 语句之间缺少正确分隔，同时还出现了引号和模块路径问题，因此产生：

```text
SyntaxError
```

以及 shell 将 `from` 误认为文件名的问题。

### 2. 为什么改为独立测试文件

后来创建：

```text
src/test_metadata.py
```

独立文件更适合：

- 编写多个测试用例；
- 使用 `try/except`；
- 重复运行；
- 保留测试代码；
- 避免 shell 引号问题；
- 后续迁移到 `tests/` 目录。

### 3. parse_markdown_content() 参数问题

函数定义只接收：

```python
raw_text
```

但调用时曾多传入：

```python
file_path
```

导致参数数量不匹配。

最终修改为：

```python
content, parsed_metadata = parse_markdown_content(text)
```

文件来源单独传给：

```python
validate_metadata(parsed_metadata, str(file))
```

### 4. status 和 tags 缩进问题

最初 `status` 和 `tags` 校验写在必需字段 `for` 循环内部。

这样会重复执行，并可能在字段还未确认存在时直接访问。

最终将两项校验移到循环外。

### 5. 错误信息缺少定位信息

最初错误信息只说明缺少字段或类型错误，没有统一包含当前文件路径。

最终增加：

```text
source
```

使批量加载出错时能够定位具体文件。

## 当前还没有实现的校验

当前尚未实现：

- `title` 等字符串字段是否为空；
- `tags` 中每个元素是否都是字符串；
- `tags` 是否为空列表；
- `last_updated` 是否符合日期格式；
- `document_type` 是否属于允许集合；
- `system_layer` 是否属于允许集合；
- `status` 与文档验证程度是否一致；
- 是否禁止未知额外字段；
- 单篇错误文档是否跳过并继续加载；
- 多篇错误文档汇总报告；
- 使用 `pytest` 的自动化测试；
- 使用 Pydantic 或数据模型统一校验。

## 如果没有 YAML Front Matter 会怎样

如果 Markdown 没有 YAML Front Matter，`parse_markdown_content()` 当前返回：

```python
raw_text, {}
```

随后空字典进入：

```python
validate_metadata()
```

字典类型检查可以通过，但必需字段检查会发现缺少：

```text
title
```

并抛出 `ValueError`。

这符合当前 `docs_raw` 的规则：

> 所有进入正式知识库的 Markdown 文档都必须具有完整 YAML Metadata。

## 如果从零重写，第一步做什么

第一步应先设计 Metadata 数据规范，而不是直接编写多个 `if`。

先确定：

```text
Metadata 根结构
→ 必需字段
→ 每个字段的类型
→ 字段允许值
→ 缺失字段策略
→ 错误类型
→ 错误信息格式
→ 测试样例
```

规则明确后，再按照依赖顺序编写校验代码。

这样可以避免边写代码边临时决定规则，导致不同文档使用不同标准。

## 我的理解与复述

### 1. 为什么外部 YAML 数据不能直接信任？

因为 YAML 来自文档内容，可能存在语法虽然正确但结构和字段不符合项目规范的情况。

因此解析后的数据必须经过类型、必需字段和字段值校验，才能进入后续文本切分和向量化流程。

### 2. 为什么先检查类型，再检查字段？

只有确认 Metadata 是字典，才能安全地使用字段查找和下标访问。

如果 Metadata 是列表或字符串，直接检查字典字段可能产生错误或错误的判断。

### 3. 为什么字段存在不代表字段值一定合法？

例如：

```yaml
status: verify
tags: Python
```

`status` 和 `tags` 字段都存在，但：

- `verify` 不属于允许状态；
- `Python` 是字符串，不是标签列表。

因此字段存在性和字段值合法性必须分层检查。

### 4. TypeError 和 ValueError 在本功能中怎样区分？

`TypeError` 表示对象类型不符合要求，例如 Metadata 不是字典、`tags` 不是列表。

`ValueError` 表示类型基本正确，但内容不符合项目规则，例如缺少必需字段或 `status` 非法。

### 5. 为什么独立测试通过后还必须测试真实批量加载？

独立测试只能证明校验函数在构造样例下工作正常。

真实批量加载还能验证：

- 文件扫描；
- 文件读取；
- YAML 分离；
- YAML 解析；
- 校验器接入位置；
- Metadata 补充；
- Document 构造；
- 多文档循环。

两种测试结合，才能证明 Day 7 功能真正接入了当前 Loader。

## 后续计划

- 开始文本切分；
- 设计 Chunk 数据结构；
- 为每个 Chunk 继承 Metadata；
- 增加 `chunk_index`；
- 校验 `chunk_size` 和 `chunk_overlap`；
- 编写文本切分测试；
- 后续将测试文件统一迁移到 `tests/`；
- 文本切分稳定后再进入 Embedding 和 ChromaDB。
