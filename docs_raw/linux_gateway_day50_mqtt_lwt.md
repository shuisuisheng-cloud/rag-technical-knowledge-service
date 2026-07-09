---
title: Linux-STM32 物联网边缘网关 Day 50 MQTT LWT 异常离线检测
project: Linux-STM32 物联网边缘网关
system_layer: 通信层 / 数据中枢
document_type: software_module_record
status: software_verified
last_updated: 2026-07-04
tags: [Linux, Python, MQTT, LWT, Last Will, offline, Broker]
---

# Linux-STM32 物联网边缘网关 Day 50 MQTT LWT 异常离线检测

## 今日目标

为什么网关只有 Heartbeat 还不够？

Heartbeat 只能证明网关在某个时刻仍然正常运行。

当网关进程崩溃、网络突然断开或者被 `kill -9` 强制终止时，网关程序自身已经无法继续发送消息，也无法主动发布 offline 状态。

订阅者虽然可以通过长时间没有收到心跳推测网关离线，但不能立即收到明确的异常离线事件和离线原因。

Day 50 要解决什么异常场景？

解决网关无法正常执行退出代码时，仍然能够由 MQTT Broker 自动发布异常离线消息的问题。

主要场景包括：

- 网关进程崩溃；
- `kill -9` 强制终止；
- 网络连接突然中断；
- 设备掉电；
- MQTT 连接异常丢失。

## 什么是 MQTT LWT

LWT 的完整含义是：

```text
Last Will and Testament
```

中文通常称为：

```text
遗嘱消息
```

遗嘱消息由谁提前配置？

由 MQTT Client 在建立连接之前，通过：

```python
client.will_set()
```

提前配置。

异常断连后由谁真正发布？

由 MQTT Broker 发布。

不是已经异常退出的网关程序自己发布，因为异常退出后，网关程序通常已经无法继续运行代码。

完整流程是：

```text
Client 配置遗嘱
→ Client 连接 Broker
→ Broker 保存遗嘱
→ Client 异常断开
→ Broker 检测连接丢失
→ Broker 发布遗嘱消息
```

## 为什么 will_set() 必须在 connect() 之前调用

`will_set()` 必须在：

```python
client.connect()
```

之前调用。

原因是遗嘱配置会在 MQTT Client 建立连接时，作为 CONNECT 报文的一部分发送给 Broker。

Broker 只有在建立连接时，才能保存该 Client 对应的遗嘱 Topic、Payload、QoS 和 Retain 配置。

如果已经连接 Broker 后再调用 `will_set()`，当前连接的遗嘱信息不会被重新发送给 Broker，因此本次连接无法正确注册 LWT。

LWT 不是单纯保存在本地的临时判断逻辑。

它是：

```text
客户端在建立连接时发送给 Broker 的连接级配置
```

## Status Topic

实际 Status Topic：

```text
edgeaiot/gateway/linux_stm32_gateway_01/status
```

为什么 LWT 不发布到 Heartbeat Topic？

Heartbeat Topic 表示周期性心跳，用于证明网关进程仍然持续运行。

Status Topic 表示网关的在线、离线和退出原因。

LWT 发布的是状态变化事件，因此应该发布到 Status Topic，而不是 Heartbeat Topic。

## Offline Payload

异常断连时的 Payload：

```json
{
  "gateway": "linux_stm32_gateway_01",
  "device": "stm32_node_01",
  "status": "offline",
  "reason": "unexpected_disconnect"
}
```

各字段含义：

- `gateway`：网关标识。
- `device`：当前网关负责连接的 STM32 节点标识。
- `status`：网关当前状态，此处为 `offline`。
- `reason`：离线原因，此处为异常断连 `unexpected_disconnect`。

## 核心函数

### configure_mqtt_last_will()

输入是什么？

输入 MQTT Client 对象，以及配置中使用的网关 ID、设备 ID和 Status Topic。

内部调用了什么 Paho API？

```python
client.will_set()
```

输出或副作用是什么？

该函数通常没有业务返回值。

它的副作用是：

```text
为 MQTT Client 配置本次连接使用的遗嘱消息
```

配置完成后，后续调用 `connect()` 时，遗嘱信息会发送给 Broker。

### client.will_set()

主要参数包括：

- `topic`：异常断连后 Broker 发布消息的 Topic。
- `payload`：异常断连消息内容。
- `qos`：遗嘱消息的服务质量等级。
- `retain`：Broker 是否保存这条状态消息。

Topic 决定消息发到哪里。

Payload 决定消息携带什么状态和原因。

QoS 决定消息传输保证等级。

Retain 决定新订阅者能否立即收到最近一次状态快照。

## 完整控制流

程序启动
→ 创建 MQTT Client
→ 构造 offline 遗嘱 Payload
→ 调用 `configure_mqtt_last_will()`
→ 内部调用 `client.will_set()`
→ 调用 `client.connect()` 连接 Broker
→ Broker 保存该 Client 的遗嘱配置
→ 网关正常运行
→ 发生异常退出或连接意外丢失
→ Broker 检测 Client 非正常断开
→ Broker 向 Status Topic 发布 LWT
→ 订阅者收到 offline 和异常断开原因

## 异常退出与正常退出的区别

### kill -9 或进程崩溃

进程被 `kill -9` 终止后，Python 程序没有机会执行异常处理和退出清理代码。

Broker 会通过 TCP 连接中断、Keepalive 超时等方式发现 Client 已经异常离线。

随后 Broker 发布该 Client 在连接时注册的 LWT。

### Ctrl+C 正常退出

用户按下 `Ctrl+C` 时，Python 程序通常可以捕获：

```python
KeyboardInterrupt
```

因此程序有机会主动执行退出流程。

正常退出时不能依赖 LWT，因为正常调用 `disconnect()` 后，Broker 会认为 Client 是正常断开，不应发布异常遗嘱。

正常退出应该由网关程序主动发布：

```text
status = offline
reason = graceful_shutdown
```

然后再断开 MQTT 连接。

## 输入与输出

输入：

- MQTT Client 对象；
- Status Topic；
- 网关 ID；
- STM32 设备 ID；
- abnormal offline Payload；
- QoS 和 Retain 配置。

输出：

- Broker 保存的 LWT 配置；
- 网关异常断连后，由 Broker 发布的 offline 状态消息；
- 订阅者接收到的异常离线通知。

## 测试方法

首先订阅 Status Topic：

```bash
mosquitto_sub \
  -h localhost \
  -t edgeaiot/gateway/linux_stm32_gateway_01/status \
  -v
```

启动网关程序并确认其成功连接 Broker。

然后查找网关进程 PID，并使用：

```bash
kill -9 <PID>
```

模拟异常退出。

预期结果：

Broker 自动向 Status Topic 发布：

```json
{
  "gateway": "linux_stm32_gateway_01",
  "device": "stm32_node_01",
  "status": "offline",
  "reason": "unexpected_disconnect"
}
```

## 验证结果

已经验证：

- MQTT Client 可以在连接前配置 LWT；
- Broker 可以保存遗嘱配置；
- 网关进程异常退出后 Broker 会发布 offline；
- 订阅者可以收到异常离线状态和原因；
- Status Topic 与 Heartbeat Topic 已进行职责区分。

当前状态为：

```text
software_verified
```

目前只完成 Linux 和 MQTT 软件链路验证。

尚未完成：

- 真实 STM32 UART 断线检测；
- STM32 设备真实离线判断；
- 网关异常时对硬件执行器的联动处理。

## 当前边界

LWT 能证明什么？

LWT 能证明 MQTT Broker 判断该 MQTT Client 发生了非正常断开。

LWT 不能证明什么？

LWT 不能直接证明：

- STM32 硬件已经损坏；
- UART 已经断开；
- STM32 已经掉电；
- 传感器已经故障；
- 网关操作系统已经完全停止。

为什么收到 offline 不一定代表 STM32 硬件损坏？

因为 offline 表示的是 Linux 网关 MQTT Client 与 Broker 之间的连接状态。

可能原因包括：

- Python 进程崩溃；
- 网络断开；
- Broker 连接丢失；
- Linux 设备掉电；
- 程序被强制结束。

STM32 可能仍然正常运行，只是 Linux 网关已经无法继续向 Broker 转发数据。

## 今日遇到的问题

主要理解难点包括：

- 一开始容易误认为 LWT 由网关程序异常退出后主动发布；
- 容易忽略 `will_set()` 必须在 `connect()` 之前调用；
- 容易混淆 Heartbeat Topic 和 Status Topic；
- 容易把 MQTT Client offline 直接理解为 STM32 硬件 offline；
- 容易把正常退出和异常退出混为同一种状态。

正确理解是：

```text
Client 只负责提前配置遗嘱
Broker 负责在异常断连后发布遗嘱
```

## 常见错误

- 将 `will_set()` 放在 `connect()` 之后；
- 把 LWT 发布到 Heartbeat Topic；
- Payload 不是合法 JSON；
- 网关 ID 和设备 ID 混淆；
- 把正常退出写成 `unexpected_disconnect`；
- 误认为 LWT 由异常退出后的客户端自己发布；
- 把 MQTT 网关离线等同于 STM32 硬件离线；
- 忘记考虑 Retain 对新订阅者状态判断的影响。

## 在 EdgeAIoT 系统中的意义

Orange Pi、Web 页面或者上层 Agent 可以订阅网关 Status Topic。

收到：

```text
offline + unexpected_disconnect
```

后，可以进行：

- 网关离线告警；
- 停止继续下发控制指令；
- 将设备状态标记为不可用；
- 记录异常退出日志；
- 提醒用户检查 Linux 网关、网络或 Broker；
- 启动重连或故障恢复逻辑。

LWT 为上层系统提供了异常断连后的自动状态通知能力。

## 面试时怎么讲

Heartbeat 只能周期性证明网关仍在运行，但网关进程异常退出后，程序自身已经无法主动发送 offline 消息。

因此我使用 MQTT LWT 解决异常断连检测问题。

网关在调用 `connect()` 之前，通过 `client.will_set()` 把 offline Payload、Status Topic、QoS 和 Retain 配置发送给 Broker。

当 Broker 检测到网关 Client 非正常断开时，会代替客户端发布遗嘱消息。

正常按下 `Ctrl+C` 退出时，程序应主动发布 `graceful_shutdown`，而不是依赖 LWT。

当前该功能已完成 MQTT 软件链路验证，但 LWT 只表示网关 MQTT Client 异常离线，不能直接证明 STM32 硬件故障。

## 如果从零重写，第一步做什么

第一步先设计统一的 Status Topic：

```text
edgeaiot/gateway/linux_stm32_gateway_01/status
```

然后设计异常离线 Payload：

```json
{
  "gateway": "linux_stm32_gateway_01",
  "device": "stm32_node_01",
  "status": "offline",
  "reason": "unexpected_disconnect"
}
```

之后按以下顺序实现：

```text
构造 offline Payload
→ 编写 LWT 配置函数
→ 在 connect() 前调用 will_set()
→ 连接 Broker
→ 订阅 Status Topic
→ 使用 kill -9 模拟异常退出
→ 验证 Broker 自动发布遗嘱
→ 再补充正常退出流程
```

## 后续计划

- 为 Status Topic 增加 Retain；
- 在成功连接后主动发布 retained online；
- 在正常退出前主动发布 retained offline；
- 区分 `connected`、`unexpected_disconnect` 和 `graceful_shutdown`；
- 将 Retained Status 与 Heartbeat 结合；
- 后续增加真实串口和 STM32 状态检测。