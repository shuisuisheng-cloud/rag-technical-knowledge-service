---
title: "RAG Day 20+21：FastAPI HTTP 知识问答接口与实际联调"
project: "RAG 知识库服务"
system_layer: "API 层 / RAG 应用服务层"
document_type: "learning_note"
status: "development_verified_not_v1_frozen"
last_updated: 2026-10-13
tags:
  - Python
  - FastAPI
  - Pydantic
  - Uvicorn
  - HTTP
  - RAG
  - ExceptionHandling
  - API
---

# RAG Day 20+21：FastAPI HTTP 知识问答接口与实际联调

## 0. 状态、版本与证据边界

- 日期：2026-10-13；本笔记记录 **Day 20+21 的本地开发与用户截图验证**，不是 V1 完整冻结证明。
- 最近已核实 GitHub `main`：`f3f6dab8c6744617c428d4373389feeb44ff8572`，对应已提交的 Day 18+19 RAG Answer；**本笔记撰写时 `src/api.py` 尚未出现在远端 main**。本地 `src/api.py` 的最终内容需以随后 Git 提交为准。
- 本地环境截图：WSL Ubuntu、项目 `~/projects/rag-technical-knowledge-service`、`.venv`（Python 3.14）；实际安装 `fastapi==0.143.0`、`uvicorn==0.54.0`、`pydantic==2.13.4`。
- 先前真实功能：Document Loading / Chunking → Embedding → ChromaDB → Top-K Retrieval → Context Assembly → Ollama Chat（`qwen3:4b`）→ `answer_question() -> dict`。
- Day 20+21 新能力：Uvicorn 启动 FastAPI，真实 HTTP `POST /query` 返回 `question`、`answer`、`sources` JSON；网页 Swagger UI 发起真实提问成功。仅代表 **Development Verification PASS（最小正常链路 + 已测试请求校验场景）**。
- 索引证据保留：首轮 47 文档 / 610 Record 完整读回验证；后续曾达 632 条、Pending=0，但未进行同等级完整读回。新增 Day 16+17、18+19 乃至本笔记后的 **Collection 当前实际数量 UNKNOWN**，不得据历史数值推算。
- R1 风险仍存在：`source::chunk_<index>` 的 existing-ID 跳过策略不会更新同 ID 的正文/metadata，也不能自动处理已删除的源文档；不得把 Pending=0 解释为内容已完全同步。

## 1. 架构与职责：HTTP 请求如何变成 RAG 回答

```text
浏览器 Swagger UI 或 curl（HTTP 客户端）
    │ POST /query + JSON
    ▼
Uvicorn (ASGI HTTP Server)       — 监听 127.0.0.1:8000
    ▼
FastAPI src/api.py              — 路由、请求校验、错误映射、响应序列化
    ▼
QueryRequestion (Pydantic)      — question: str，top_k: int
    ▼
answer_question(question, top_k) — src/rag_service.py
    ├─ retrieve()               — question embedding + ChromaDB Top-K
    ├─ build_context()          — 按序有限长度 Context、纳入的 sources
    └─ ollama.chat()            — 依据资料生成自然语言 answer
    ▼
QueryResponse (Pydantic)        — question + answer + list[SourceItem]
    ▼
HTTP 200 + application/json
```

### 1.1 模块分工

- **Uvicorn**：运行 ASGI 应用，处理网络连接与 HTTP 请求。
- **FastAPI**：在启动时注册路由；请求到达后调用合适的 Python 函数；把结果转换成 HTTP 响应。
- **Pydantic**：解析/校验客户端的 JSON，并验证与序列化响应结构。
- **rag_service.py**：既有知识问答业务逻辑，不因 HTTP 接入而重写。
- **ChromaDB**：存储和检索向量记录；本地持久化目录 `data/chroma`。
- **Ollama**：独立提供 Embedding 和聊天模型服务，通常监听 `127.0.0.1:11434`。
- **Swagger UI**：现成 API 文档/调试网页，不是本人自行开发的聊天前端。

### 1.2 三个地址不是一回事

| 地址或路径 | 方法 | 用途 |
| --- | --- | --- |
| `http://127.0.0.1:8000/docs` | GET | Swagger UI 交互文档，默认由 FastAPI 提供 |
| `http://127.0.0.1:8000/openapi.json` | GET | 根据路由与 Pydantic Schema 自动生成的 OpenAPI 描述 |
| `http://127.0.0.1:8000/query` | POST | 实际调用本项目 RAG 问答；浏览器直接输入 URL 是 GET，不能代替 POST |

FastAPI 自带 `/docs` 页面，Swagger UI 读取 OpenAPI Schema（通常引用前端资源）生成 Try it out/Execute/请求体面板。**写了 API 不等于自行开发了前端产品页面**。

## 2. Python / FastAPI API 契约

### 2.1 当前约定的请求和响应

请求示例：

```http
POST /query
Content-Type: application/json
```

```json
{"question": "MQTT 的 LWT 有什么作用？", "top_k": 3}
```

响应示例（结构示例，非某次真实原始输出）：

```json
{
  "question": "MQTT 的 LWT 有什么作用？",
  "answer": "根据检索资料生成的自然语言回答",
  "sources": [
    {"id": "example::chunk_0", "source": "docs_raw/example.md"}
  ]
}
```

- `answer_question()` 返回类型为 **`dict`**，最外层只有一份问答记录；其中 `sources` 为 **`list[dict]`**。
- `retrieve()` 返回 **`list[dict]`**（多条候选 Chunk）。
- `build_context()` 返回 **`tuple[str, list[dict]]`**（Context 文本 + 实际纳入的来源）。
- `QueryRequestion` 是本地实现中使用的模型类名；日后可统一命名，但本阶段勿未经确认批量改动。

### 2.2 Field() 约束

```python
top_k: int = Field(default=3, ge=1, le=5, strict=True)
```

- `default=3`：客户端省略 `top_k` 时采用 3。
- `ge=1`：Greater than or Equal，至少为 1。
- `le=5`：Less than or Equal，最多为 5（V1 自主约定，不是 ChromaDB API 的固有限制）。
- `strict=True`：严格整数；拒绝 JSON `true`、`"3"` 等类型不符的值。
- Python 中 `bool` 是 `int` 的子类，`isinstance(True, int)` 为 True；Pydantic 严格整数校验可以拒绝布尔值。

### 2.3 `field_validator` 和空白问题

用户从示例修改并看懂了校验器，但 **尚未证明能独立从零编写**。

```python
@field_validator("question")
@classmethod
def check_question(cls, value: str) -> str:
    cleaned = value.strip()
    if cleaned == "":
        raise ValueError("question 不能为空")
    return cleaned
```

- `@field_validator("question")` 注册对 question 字段的附加校验。
- `@classmethod` 将方法绑定到类；对这种 Pydantic V2 写法是清晰做法，不等于所有验证器都必须有它。
- `value` 是待校验字符串，`cls` 是类。
- `strip()` 删除首尾空白；若清理后为空抛出 `ValueError`，Pydantic 会把它汇总为请求校验错误。
- **请求验证发生在路由函数执行前**；无效请求通常由 FastAPI 返回 HTTP 422，`query()` 不执行，也不调用 Ollama。

### 2.4 类 / 实例 / 字典不能混淆

```python
class QueryRequestion(BaseModel):
    question: str
    top_k: int = 3

# QueryRequestion 是类；req 是实例；req.question 是属性。
req = QueryRequestion(question="什么是 LWT？")
print(req.top_k)  # 3
```

`result = answer_question(req.question, req.top_k)` 得到的是普通 `dict`。`return result` 可以直接交给声明了 `response_model=QueryResponse` 的 FastAPI 路由校验和序列化，而不是把同一问题送到模型三次。

### 2.5 装饰器和导入时机

```python
@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequestion):
    ...
```

- `app = FastAPI()` 创建应用实例。
- `@app.post("/query")` **模块导入时注册规则**：有匹配的 POST 请求后调用 `query()`；注册不等于立即执行问答。
- `response_model=QueryResponse` 指明输出的数据契约（字段和类型）。若业务返回缺少必需的 `sources`，属于**响应端**校验失败，通常为 HTTP 500，不是请求 422。
- `if __name__ == "__main__":` 保护脚本内测试调用，以免 Uvicorn 导入模块时触发测试问答。

## 3. 异常传播与 HTTP 状态码

### 3.1 业务层到 HTTP 层

`rag_service.py` 在已识别的 Ollama 错误下使用 `raise RuntimeError(...) from e`：

```text
ollama.embed()/ollama.chat() 原始异常
    ↓
rag_service.answer_question() 抛 RuntimeError from e
    ↓
api.py 捕获 RuntimeError
    ├─ 若 e.__cause__ 是 Ollama ResponseError / ConnectionError / httpx.TimeoutException
    │    └─ raise HTTPException(status_code=503, ...) from e
    └─ 其他 RuntimeError → 裸 raise，继续传播（通常 HTTP 500）
```

- `except` 捕获指定类型；`raise HTTPException(...)` 新建并抛出 HTTP 错误；`raise`（不带参数）重新抛出正在处理的异常。
- `from e` 把原始异常显式记录为新异常的 `__cause__`，便于定位故障根因。
- 不要将所有 `RuntimeError` 都翻译成 Ollama 503，否则会掩盖真正的内部程序错误。
- Ollama **自己**对不存在模型返回 404，与 FastAPI **对上游依赖故障**映射为 503 是两个服务层次，不矛盾。
- 用户说明首次 POST 503 当时 Ollama 尚未启动，重启依赖服务后同类请求返回 200；目前只验证代表性恢复，尚不属于多轮稳定性指标。

### 3.2 HTTP 状态码面试速查

| 状态 | 意义 | 本项目例子 |
| --- | --- | --- |
| 200 OK | 请求成功 | POST /query 成功问答 |
| 201 Created | 创建成功 | 本项目暂未使用 |
| 204 No Content | 成功但无正文 | 本项目暂未使用 |
| 301/302 | 重定向 | 非本项目关键路径 |
| 400 Bad Request | 请求不符合要求 | 可用于某些业务请求错误，当前主要由 Pydantic 处理为 422 |
| 401 Unauthorized | 未完成有效认证 | 目前未实现鉴权 |
| 403 Forbidden | 拒绝访问 | 目前未实现权限控制 |
| 404 Not Found | 路由/资源不存在 | 请求不存在的 API 路径；或 Ollama 自身缺失模型的上游 404 |
| 405 Method Not Allowed | 路径存在，HTTP 方法不允许 | GET /query，因仅注册 POST |
| 409 Conflict | 与当前资源状态冲突 | 本项目暂未使用 |
| 422 Unprocessable Content | 请求体可解析但验证失败 | 空白 question、top_k=0、top_k=true |
| 429 Too Many Requests | 限流 | 未实现 |
| 500 Internal Server Error | 未处理的服务端错误 | 未捕获异常、无效的 QueryResponse |
| 502 Bad Gateway | 代理收到无效上游响应 | 无代理架构时不宜套用 |
| 503 Service Unavailable | 服务暂不可用 | 本项目 Ollama 未启动/缺失模型等已识别依赖故障 |
| 504 Gateway Timeout | 网关等待上游超时 | 与“未捕获的异常”不同；当前 `httpx.TimeoutException` 实现映射为 503，**没有实测 504** |

### 3.3 故障定位：从外到内

1. 浏览器打不开 `/docs` / TCP 连接失败：先查 Uvicorn 是否监听 `127.0.0.1:8000`，再看监听端口/WSL 网络；还没到业务/模型层。
2. `/docs` 能打开但 GET `/query` 是 405：请求方法错误，不代表服务器故障。
3. POST `/query` 返回 422：优先读 `detail` 内的 `loc`、`type` 和 `msg`，检查 Pydantic 的字段与范围。
4. POST `/query` 返回 503：查看异常链和 Ollama 服务/模型状态；Uvicorn/FastAPI 至少已经处理了请求。
5. POST `/query` 返回 500：检查服务器 Traceback、错误返回结构、键访问、响应模型/路径配置。
6. 模型正常但答案差：检查检索到的 Chunk、Context 中的正文和来源、回答是否有证据；HTTP 200 只证明请求处理成功，不代表事实回答准确。

## 4. 运行与停止（PC/WSL）

### 4.1 两个服务

终端 A：检查 Ollama 服务是否已存在；如果没启动才运行：

```bash
ollama list
# 若报服务无法连接，再在单独终端运行：
ollama serve
```

Ollama 独立于 FastAPI。已确认安装 `qwen3-embedding:0.6b` 与 `qwen3:4b`；前者用于 embedding，后者用于 answer。重复启动已监听的 Ollama 会报端口冲突。

终端 B：切换到项目根目录，激活 venv，启动 HTTP API：

```bash
cd ~/projects/rag-technical-knowledge-service
source .venv/bin/activate
PYTHONPATH=src python -m uvicorn api:app \
  --host 127.0.0.1 --port 8000 --reload
```

- `PYTHONPATH=src`：将 `src` 放入当前进程的模块搜索路径；否则找不到顶层 `api` 模块。
- `python -m uvicorn`：通过当前虚拟环境 Python 执行 Uvicorn。
- `api:app`：导入 `src/api.py` 中名为 `app` 的应用实例；不是调用 `api()`。
- `--host 127.0.0.1`：仅本机可访问；未来局域网 Orange Pi 调用另需监听/防火墙/访问控制等明确配置。
- `--port 8000`：HTTP API 监听端口，与 Ollama 默认 11434 不同。
- `--reload`：开发模式源文件变更时自动重启；生产部署不应照搬。
- 启动后的检查：看到 `Application startup complete`，打开 `http://127.0.0.1:8000/docs`。
- 在对应终端 `Ctrl+C` 停止服务；当前 API 不包含自己的启动脚本/系统服务配置。
- 运行目录重要：当前 ChromaDB 使用相对路径 `data/chroma`，需要在 RAG 项目根目录运行，避免加载错误数据库。

### 4.2 从 Python 到 HTTP 的区别

Python 直接调用 `answer_question("问题")` 时，不需要启动 Uvicorn，但仍需要模型服务；外部浏览器/curl HTTP 调用 `/query` 时，**Uvicorn 与 Ollama 必须分别可用**。浏览器里 `/docs` 是工具页面，`/query` 才是真实 POST 接口。

## 5. Day 20+21 真实测试矩阵（仅用户提供的截图证据）

| 项目 | 实际证据 | 结论 |
| --- | --- | --- |
| `python -m py_compile src/api.py` | 用户终端无编译报错；之后修正过参数拼写 | 历史语法测试 PASS；不代表运行时参数合法 |
| Uvicorn 导入 | 最初 `respense_model` 拼写错误，FastAPI.post 提示 unexpected keyword；修正后 `Application startup complete` | 启动 PASS，已修复一处运行时 API 参数错误 |
| GET `/docs`、`/openapi.json` | Uvicorn 日志 200 | PASS |
| Swagger UI POST `/query`（STM32 ACK） | 页面显示 200，回答与 3 条 sources | 正常路径 PASS |
| curl POST `/query`（MQTT LWT） | HTTP 200，JSON 包含 `question/answer/sources` | 正常路径 PASS |
| 第一次 POST `/query` | HTTP 503 / detail Ollama 服务暂时不可用；用户说明当时 Ollama 未启动 | 已观察预期 503，故障来自依赖未启动（用户说明），不能当作稳定性长期验证 |
| POST `question="   "` | HTTP 422，detail `Value error, question 不能为空` | PASS |
| POST `top_k=0` | HTTP 422，`greater_than_equal` | PASS |
| POST `top_k=true` | HTTP 422，`int_type` | PASS |
| GET `/query` | HTTP 405、`allow: POST` | PASS |
| `top_k=6` / `"3"` / 缺失 question / 无效响应内容 | 暂无独立 HTTP 截图 | NOT TESTED（可在 V1 代表性回归中按需验证） |
| 未知运行时 500 与 timeout/504 | 暂无代表性真实测试 | NOT TESTED |
| 当前 Collection count / 632 后完整回归 | 本阶段未重新实测 | UNKNOWN |

注意：HTTP 200 是接口工作，不等于模型回答无幻觉或检索效果经系统性评估。课程表反例证明 LLM 可以拒绝无依据问题，但当前返回 sources 仍可能是无关的候选资料。

## 6. 已知缺陷、冻结前最小工作与边界

- `sources` 的业务含义：**被纳入 LLM Context 的候选资料来源**，不是经过逐句验证的 Supporting Sources；不应向其他项目宣传为“答案每句都有证据”。需要在 API 文档/README 说清楚，必要时对无相关证据的场景采取有界处理。
- V1 R1 语料变更风险：existing-ID 过滤是增量**追加**优化，不是修改/删除同步系统。冻结前选一个明确的固定语料版本或显式重建策略，避免无限扩张为同步平台。
- 当前 `data/chroma` Record count 为 UNKNOWN；冻结前需读回数量、ID/正文/metadata/vector 一致性、持久化、来源可用性。
- `retrieve()` 通过 zip 合并结果，仍需确定多字段等长/类型边界；本阶段未做全部边界测试。
- `httpx.TimeoutException` 转换代码已存在，但未做独立超时路径验收；高并发、认证、限流、分布式部署均不属于此次最小开发结果。
- requirements.txt 在本阶段源码提交前需根据真实安装版本补充 `fastapi==0.143.0`，保持依赖可复现；不能将本地已安装等同于 GitHub 已提交。
- 需完善 README：项目架构、Ollama 双模型、安装/启动命令、端口、示例 curl、403/404/405/422/500/503 等常见状态、已知限制、证据级别及 PC/WSL 部署边界。
- V1 不是 Orange Pi 5 Plus 的 NPU 推理前置；后续 Orange Pi V2 仅通过 HTTP 调用知识服务即可，无需在 RK3588 上重复整个 RAG。

## 7. 本次反复错误与独立掌握程度（不得虚报）

用户明确声明：开发中 Field、field_validator、异常映射大量参考 AI 示例，当前**看着能解释，但过一天或更久后未必能独立从零编写**。启动命令也依赖提示，独立关机/重启后的启动尚未严格复测。因此按照学习事实记录：

- 已观察到：能在讲解后修改 Pydantic/路由、看懂异常映射、通过真实 HTTP 校验、解释 GET 405/POST 200 的区别。
- 有证据的薄弱点：`dict` / `list[dict]` / Pydantic 实例混淆；`enumerate()` 解包顺序；循环中重复使用 mutable dict；将一个请求重复调用三次 RAG；`@app.post` 的注册与运行时机；`@field_validator` 独立实现；`Field(default/ge/le/strict)`；`except` 捕获类型 vs `raise HTTPException`；`raise`/`raise ... from e`；HTTP 500/503/504 混淆；模块导入、`PYTHONPATH`、`api:app` 以及从全停状态恢复。
- 显著真实 Debug：`response_model` 拼写为 `respense_model`（`py_compile` 不会查出调用时无效关键字，导入注册路由时才报错）；`SourceItem.source` 与 `sources` 名称不一致；返回类型 `QueryResponse` 与原业务 dict 的关系；服务器和 Ollama 是分离服务。
- 之后**逐层验收**：L1 读懂 → L2 不看源码解释 → L3 独立实现（允许官方文档、禁止复制现成项目答案）→ L4 现场 Debug / 变更需求。实际演示通过≠闭卷独立掌握。

## 8. V1 候选冻结与三轮正式技术面（用户最新规则）

流程：**完成必要工程回归 → V1 冻结候选版本 → Round 1 技术一面 → Round 2 技术二面 → Round 3 综合压力面 → 统一评分与错误分析/补强复测 → 正式冻结或针对问题继续修复**。

- **Round 1 基础**：Python 对象、函数、列表/字典/元组、导入、装饰器、异常、HTTP 方法/状态码、Pydantic Field/field_validator、Embedding、Chunking、向量查询 API 与检索结果结构；穿插短手写和反例。
- **Round 2 深度**：RAG 全链路、存储与来源一致性、ChromaDB 持久化、更新/删除风险、候选来源与证据区别、同步阻塞与并发、错误传播、API Schema、性能/超时、真实故障追踪、代码阅读、现场实现和 Debug。
- **Round 3 广度压力**：Linux 用户态、网络、UART/MQTT/LWT/ACK、STM32 设备闭环、Python/Agent、C/C++、Edge AI/RK3588 NPU 等跨领域推理及超纲追问；大厂强度，不设固定时长，以独立推理和验证能力评估。
- 三轮结束后集中评分、面试结论、详细解答和推荐补强，**开发日跟随示例写对不算独立掌握**；面试中闭卷与可查官方文档题分开评分。
- V1 冻结后默认按需求维护，也允许针对 Orange Pi 实际调用或确定的可靠性需求继续规划升级，不是永久停止开发。

## 9. 本阶段提交前 checklist

- [ ] 确认 WSL 项目根目录 `git status --short`，确保不覆盖未提交更改。
- [ ] 保留本地 `src/api.py` 的最新正确代码，并确认 `/query` 接口正常。
- [ ] `requirements.txt` 与本地 FastAPI 版本对应，避免一次性重新 `pip freeze` 覆盖历史不相关版本。
- [ ] 将此笔记保存到 `notes/day20_day21_fastapi_http_api.md`。
- [ ] `python -m py_compile src/api.py`、`python -m pip show fastapi`、`git diff --check`；必要时重试一组 POST 200。
- [ ] 只暂存预期三个文件、检查 staged diff，commit 和 push，确认远端 HEAD、工作区干净。
- [ ] 再将 Day 20+21 新提交的准确 HEAD、HTTP 测试证据与剩余边界同步 AI_Projects/RAG_Service 以及 PROJECT_INDEX 中必要摘要；不改写 610/632 历史。

**结论**：Day 20+21 的 FastAPI `/query` 最小 HTTP 服务和代表性 HTTP 请求已由用户本地截图验证，但截至本笔记撰写时远端代码提交尚未完成，V1 内容一致性、运行可复现性、证据语义和最终技术面仍待验收。
