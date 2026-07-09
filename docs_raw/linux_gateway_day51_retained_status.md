---
title: Linux-STM32 物联网边缘网关 Day 51 Retained Status 状态快照
project: Linux-STM32 物联网边缘网关
system_layer: 通信层 / 数据中枢
document_type: software_module_record
status: software_verified
last_updated: 2026-07-08
tags: [Linux, Python, MQTT, Retain, Status, online, offline]
---

# Linux-STM32 物联网边缘网关 Day 51 Retained Status 状态快照

## 今日目标

Retain 要解决什么问题？

解决新订阅者刚刚订阅 Status Topic 时，无法立即知道网关最近一次状态的问题。

如果状态消息没有使用 Retain，新订阅者只能等待网关下一次状态发生变化后才能收到消息。

使用 Retain 后，Broker 会保存该 Topic 最近一条 retained 消息，新订阅者订阅后可以立即收到。

为什么新订阅者不能只等待下一次状态变化？

因为网关状态可能很长时间都不会发生变化。

例如网关已经正常在线几个小时，新启动的 Web 页面如果只能等待下一次 online 或 offline 变化，就无法立即显示网关状态。

因此需要保存最近一次状态快照。

## 什么是 MQTT Retain

Retain 消息由谁保存？

由 MQTT Broker 保存。

同一个 Topic 后续发布新的 Retain 消息时，会发生什么？

新的 retained 消息会覆盖该 Topic 原来保存的 retained 消息。

Broker 对同一个 Topic 通常只保存最近一条 retained 消息。

新订阅者订阅后会立即收到什么？

立即收到该 Topic 最近一条 retained 状态快照。

需要注意：

> 收到的是最近一次状态，不一定能够单独证明当前时刻仍然在线。

## Status Topic 与 Heartbeat Topic 的区别

### Status Topic

表示什么？

表示网关最近一次明确的状态变化，例如：

- online；
- offline；
- connected；
- unexpected_disconnect；
- graceful_shutdown。

为什么适合使用 Retain？

因为新订阅者需要立即知道网关最近一次状态。

Status 消息属于状态快照，适合让 Broker 保存最近一条结果。

### Heartbeat Topic

表示什么？

表示网关进程周期性发送的存活心跳。

每一条 Heartbeat 都带有当时的时间戳，用来证明网关在该时刻仍然运行。

为什么不能使用 Retain？

因为旧心跳代表的是过去某个时刻的存活状态。

如果 Broker 保存旧心跳，新订阅者订阅后可能立即收到一条几分钟前甚至更早的心跳，并误以为网关当前仍然在线。

旧心跳被新订阅者收到会造成什么误判？

会把历史存活记录错误判断为当前实时在线证明。

因此：

```text
Status Topic 使用 Retain
Heartbeat Topic 不使用 Retain
```

## 在线状态流程

程序成功连接后：

→ 构造 online Payload：

```json
{
  "gateway": "linux_stm32_gateway_01",
  "device": "stm32_node_01",
  "status": "online",
  "reason": "connected"
}
```

→ 发布到：

```text
edgeaiot/gateway/linux_stm32_gateway_01/status
```

→ `retain` 设置为：

```text
true
```

→ Broker 保存最新的 online 状态快照。

新订阅者订阅 Status Topic 后，可以立即收到该 online 消息。

## 异常离线流程

进程异常退出后：

→ Broker 通过 TCP 连接断开或 Keepalive 超时检测 Client 异常离线
→ Broker 发布连接时保存的 LWT
→ LWT Payload 为 offline 和 `unexpected_disconnect`
→ LWT 使用 Retain
→ Broker 用 offline 状态覆盖之前保存的 online 状态
→ 新订阅者会立即收到最新的 offline 状态

异常离线 Payload：

```json
{
  "gateway": "linux_stm32_gateway_01",
  "device": "stm32_node_01",
  "status": "offline",
  "reason": "unexpected_disconnect"
}
```

## 正常退出流程

用户按下 `Ctrl+C` 后：

→ Python 程序捕获 `KeyboardInterrupt`
→ 主动构造 offline Payload
→ `reason` 设置为 `graceful_shutdown`
→ 使用 `retain=True` 发布到 Status Topic
→ 等待 publish 完成
→ 停止 MQTT 网络循环
→ 正常断开 MQTT 连接
→ 程序结束

正常退出时应先发布：

```json
{
  "gateway": "linux_stm32_gateway_01",
  "device": "stm32_node_01",
  "status": "offline",
  "reason": "graceful_shutdown"
}
```

为什么不能先 disconnect 再发布？

因为调用 `disconnect()` 后，MQTT Client 已经与 Broker 断开连接，后续无法再通过该连接发布消息。

因此必须：

```text
先发布 offline
→ 确认消息发送
→ 再 disconnect
```

## 三种状态 Payload

### Connected

```json
{
  "gateway": "linux_stm32_gateway_01",
  "device": "stm32_node_01",
  "status": "online",
  "reason": "connected"
}
```

表示网关成功连接 Broker 并进入运行状态。

### Unexpected Disconnect

```json
{
  "gateway": "linux_stm32_gateway_01",
  "device": "stm32_node_01",
  "status": "offline",
  "reason": "unexpected_disconnect"
}
```

表示 Broker 判断 MQTT Client 发生异常断连。

该消息由 Broker 根据 LWT 发布。

### Graceful Shutdown

```json
{
  "gateway": "linux_stm32_gateway_01",
  "device": "stm32_node_01",
  "status": "offline",
  "reason": "graceful_shutdown"
}
```

表示网关程序捕获正常退出事件，并主动发布 offline。

三者的区别：

```text
connected
→ 网关正常建立连接

unexpected_disconnect
→ 网关异常掉线，由 Broker 发布 LWT

graceful_shutdown
→ 网关正常退出，由网关程序主动发布
```

## 核心函数

### 状态 Payload 构造函数

职责：

根据：

- gateway ID；
- device ID；
- status；
- reason；

构造统一的 Python 字典或 JSON Payload。

例如：

```json
{
  "gateway": "linux_stm32_gateway_01",
  "device": "stm32_node_01",
  "status": "online",
  "reason": "connected"
}
```

### 状态发布函数

职责：

将状态 Payload 发布到：

```text
edgeaiot/gateway/linux_stm32_gateway_01/status
```

并设置：

```python
retain=True
```

使 Broker 保存最新状态。

### 正常退出处理逻辑

职责：

- 捕获 `KeyboardInterrupt`；
- 主动发布 retained offline；
- 使用 `graceful_shutdown` 表示正常退出；
- 等待消息发送；
- 停止网络循环；
- 断开 Broker 连接。

### configure_mqtt_last_will()

职责：

在 `connect()` 前配置 retained offline LWT。

当 Client 异常断开时，由 Broker 发布：

```text
offline + unexpected_disconnect
```

## 输入与输出

输入：

- MQTT Client；
- Gateway ID；
- Device ID；
- Status Topic；
- `status`；
- `reason`；
- Retain 配置。

输出：

- retained online 状态；
- retained unexpected offline 状态；
- retained graceful offline 状态；
- 新订阅者立即获得的最近状态快照。

## 完整状态数据流

正常启动链路：

```text
程序启动
→ 配置 retained LWT
→ 连接 Broker
→ 主动发布 retained online
→ Broker 保存 online 快照
→ 新订阅者立即收到 online
```

异常退出链路：

```text
网关异常退出
→ Broker 检测连接异常断开
→ Broker 发布 retained LWT
→ offline 覆盖原来的 online
→ 新订阅者立即收到 unexpected_disconnect
```

正常退出链路：

```text
用户按下 Ctrl+C
→ 程序捕获 KeyboardInterrupt
→ 主动发布 retained offline
→ reason = graceful_shutdown
→ 等待消息发布完成
→ disconnect
→ Broker 保存 graceful_shutdown
```

## 验证方法

订阅 Status Topic：

```bash
mosquitto_sub \
  -h localhost \
  -t edgeaiot/gateway/linux_stm32_gateway_01/status \
  -v
```

### 验证 online

启动网关程序。

然后新开一个订阅终端。

新订阅者应立即收到：

```text
online + connected
```

### 验证 unexpected_disconnect

使用：

```bash
kill -9 <PID>
```

强制结束网关进程。

Broker 应发布并保存：

```text
offline + unexpected_disconnect
```

重新启动订阅者后，应立即收到该离线状态。

### 验证 graceful_shutdown

重新启动网关程序，然后按下：

```text
Ctrl+C
```

网关程序应主动发布：

```text
offline + graceful_shutdown
```

重新启动订阅者后，应立即收到该正常退出状态。

## 当前边界

Retain 保存的是实时在线检测还是最近状态快照？

Retain 保存的是：

```text
最近一次状态快照
```

它不是实时存活检测机制。

为什么一个 retained online 不能单独证明网关此刻仍在线？

因为 retained online 可能是在过去某个时刻发布的。

如果后续出现特殊故障，Broker 没有及时获得新的 offline 状态，旧 online 仍有可能被保留。

因此 retained online 只能表示：

```text
Broker 最近一次记录的状态是 online
```

不能单独证明当前时刻仍然在线。

怎样结合 Heartbeat 避免误判？

可以同时使用：

```text
Retained Status
+
非 Retained Heartbeat
```

Status 用于快速获得最近状态。

Heartbeat 用于确认网关近期仍持续发送存活消息。

例如：

- retained status 为 online；
- 最近心跳时间没有超时；

两者同时满足时，才能更可靠地判断网关当前在线。

## 今日遇到的问题

主要理解难点包括：

- 容易把 Retain 当成实时在线检测；
- 容易认为 Broker 会保存某个 Topic 的所有历史消息；
- 容易错误地给 Heartbeat 使用 Retain；
- 容易在正常退出时先断开连接再发布 offline；
- 容易忽略异常退出和正常退出的 reason 应不同；
- 容易认为收到 retained online 就能百分之百证明网关当前在线。

正确理解是：

```text
Retain 保存最近状态
Heartbeat 证明近期存活
LWT 处理异常断连
正常退出由程序主动发布
```

## 常见错误

- 对 Heartbeat Topic 使用 Retain；
- 正常退出前没有主动发布 offline；
- 先调用 `disconnect()` 再发布 offline；
- online 和 offline 使用不同的 Status Topic；
- 没有区分 `unexpected_disconnect` 和 `graceful_shutdown`；
- 把 retained online 当成实时在线证明；
- 误认为 Broker 保存同一个 Topic 的全部 retained 历史消息；
- LWT 没有设置 Retain，导致异常 offline 不能覆盖原 online 状态。

## 在 EdgeAIoT 系统中的意义

Orange Pi、Web 页面或者 Agent 新启动后，可以立即订阅 Status Topic。

Broker 会立即返回网关最近一次状态：

- online；
- unexpected offline；
- graceful offline。

因此上层系统不需要等待下一次状态变化，就能快速显示设备状态。

Retain 和 Heartbeat 的职责分别是：

```text
Retain
→ 提供最近一次状态快照

Heartbeat
→ 提供持续存活证明

LWT
→ 提供异常断连通知
```

三者结合后，可以建立更完整的网关在线状态判断机制。

## 面试时怎么讲

MQTT Retain 用来让 Broker 保存某个 Topic 最近一条状态消息。

网关连接成功后会向 Status Topic 发布 retained online，新订阅者订阅后可以立即收到最近状态。

异常断连时，Broker 会发布 retained LWT，用 offline 和 `unexpected_disconnect` 覆盖之前保存的 online。

正常退出时，网关程序会主动发布 retained offline，并将 reason 设置为 `graceful_shutdown`，然后再断开连接。

Status Topic 适合使用 Retain，因为它表示状态快照。

Heartbeat Topic 不能使用 Retain，因为旧心跳可能被误认为当前实时存活证明。

Retain 只能表示最近一次状态，必须结合 Heartbeat 才能更可靠地判断网关当前是否在线。

## 如果从零重写，第一步做什么

第一步先统一设计 Status Topic：

```text
edgeaiot/gateway/linux_stm32_gateway_01/status
```

然后设计三种状态：

```text
online + connected
offline + unexpected_disconnect
offline + graceful_shutdown
```

接着按以下顺序实现：

```text
编写统一状态 Payload
→ 配置 retained LWT
→ connect()
→ 发布 retained online
→ 测试新订阅者立即收到状态
→ 测试 kill -9 异常退出
→ 测试 Ctrl+C 正常退出
→ 最后加入 Heartbeat 超时判断
```

## 后续计划

- 将 Retained Status 与 Heartbeat 联合判断；
- 增加最后心跳时间和超时逻辑；
- 增加 Broker 断线重连；
- 增加连接恢复后的 online 状态更新；
- 接入真实 STM32 UART；
- 区分 Linux 网关在线和 STM32 设备在线；
- 为 Orange Pi Agent 提供统一设备状态。