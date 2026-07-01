---

title: Linux-STM32 物联网边缘网关 Day 47 控制命令 ACK
project: Linux-STM32 物联网边缘网关
system_layer: 通信层 / 数据中枢
document_type: software_module_record
status: software_verified
last_updated: 2026-07-01
tags: [Linux, Python, MQTT, JSON, ACK, command_handler, EdgeAIoT]
-----------------------------------------------------------------

# Linux-STM32 物联网边缘网关 Day 47 控制命令 ACK

## 今日目标

在 Day 46 已经完成 MQTT 控制命令解析与软件命令执行的基础上，增加 ACK 确认消息。

网关接收到控制命令后，不仅要执行命令，还要向上层返回命令执行是否成功，使 Orange Pi 总控层能够知道指令是否被正确处理。

## 为什么需要 ACK

如果系统只负责下发命令而不返回结果，上层只能知道命令已经发布到 MQTT Broker，不能确定网关是否收到、命令是否合法以及执行是否成功。

ACK 用于反馈命令处理结果，为后续设备状态同步、异常告警和重试机制提供依据。

## 新增 MQTT Topic

ACK Topic：

`edgeaiot/stm32_node_01/ack`

网关在完成命令处理后，将执行结果发布到该 Topic。

## 核心函数

### `build_command_ack(command, success)`

作用：

根据原始命令和执行结果构造 ACK 数据。

输入：

* `command`：已经解析出的控制命令；
* `success`：命令执行结果，类型为布尔值。

输出：

* 成功时生成 `success` 状态；
* 失败时生成 `failed` 状态；
* 返回可用于 MQTT 发布的 ACK 数据。

### `publish_command_ack(...)`

作用：

将构造完成的 ACK 消息发布到 MQTT ACK Topic。

### `execute_command(command)`

作用：

根据命令内容执行对应的软件动作，并返回命令是否执行成功。

当前支持：

* `led_on`：返回成功；
* `led_off`：返回成功；
* 未知命令，例如 `fan_start`：返回失败。

## 输入与输出

输入：

* MQTT command Topic 中的 JSON 控制消息；
* 解析后得到的命令字符串；
* `execute_command()` 返回的布尔执行结果。

输出：

* Linux 终端中的模拟执行日志；
* 发布到 ACK Topic 的命令执行结果。

## 完整控制流

1. 测试终端通过 `mosquitto_pub` 发布控制消息；
2. MQTT Broker 接收消息；
3. 网关订阅 command Topic，并触发 `on_message()`；
4. `parse_command_payload()` 解析 JSON 并提取命令；
5. `execute_command()` 判断并执行命令；
6. `build_command_ack()` 根据执行结果生成 ACK；
7. `publish_command_ack()` 将结果发布到 ACK Topic；
8. 上层订阅者接收并查看执行结果。

控制链可以表示为：

`mosquitto_pub`
→ MQTT Broker
→ command Topic
→ `on_message()`
→ `parse_command_payload()`
→ `execute_command()`
→ `build_command_ack()`
→ `publish_command_ack()`
→ ACK Topic

## 测试结果

当前已完成以下软件测试：

* 下发 `led_on`，命令执行成功并返回成功 ACK；
* 下发 `led_off`，命令执行成功并返回成功 ACK；
* 下发尚未支持的 `fan_start`，返回失败 ACK；
* 输入非法 JSON 时，解析失败，不执行命令，也不发布 ACK。

## 当前边界

目前只完成了 Linux 用户态程序中的软件控制闭环。

`led_on` 和 `led_off` 现在只是模拟执行结果，还没有通过 UART 将控制命令发送给真实的 STM32 环境感知与执行控制终端。

因此当前可以表述为：

“MQTT 控制命令和 ACK 软件闭环已经验证。”

不能表述为：

“已经通过网关控制真实 STM32 LED。”

## 在 EdgeAIoT 系统中的意义

ACK 机制使通信层不再只是单向转发消息，而是能够向 Orange Pi 总控层反馈命令执行状态。

后续 Orange Pi Agent 可以根据 ACK 判断控制是否成功，并决定是否重试、提示用户或记录异常日志。

## 当前掌握情况

目前能够理解 command Topic 和 ACK Topic 的作用，也能够理解命令解析、命令执行和 ACK 发布之间的调用关系。

仍需继续巩固：

* MQTT 回调函数中的完整控制流；
* Python 字典与 JSON 数据之间的转换；
* 布尔值和 ACK 状态字符串之间的对应关系；
* 非法消息为什么不应该发布成功 ACK。

## 后续计划

* 设计网关与 STM32 之间的 UART 控制协议；
* 将模拟命令执行替换为真实串口发送；
* 接收 STM32 返回的执行结果；
* 根据真实执行结果生成 ACK；
* 增加超时、失败重试和异常日志；
* 支持更多设备命令和场景控制。
