---

title: Linux-STM32 物联网边缘网关 Day 46 控制命令执行
project: Linux-STM32 物联网边缘网关
system_layer: 通信层 / 数据中枢
document_type: software_module_record
status: software_verified
last_updated: 2026-06-30
tags: [Linux, Python, MQTT, JSON, command_handler, command_execution]
---------------------------------------------------------------------

# Linux-STM32 物联网边缘网关 Day 46 控制命令执行

## 今日目标

在已经能够解析 MQTT 控制消息的基础上，增加命令执行模块，使网关能够根据解析结果执行对应的软件动作。

## 核心文件

`command_handler.py`

## 核心函数

`execute_command(command)`

函数接收已经解析完成的命令字符串，根据命令内容决定执行哪一种动作。

## 当前支持的命令

* `led_on`
* `led_off`

当命令无法识别时，函数返回 `False`。

## 输入与输出

输入：

* 已通过 JSON 解析和合法性检查的命令字符串。

输出：

* 已知命令：执行对应的模拟动作；
* 未知命令：返回 `False`；
* 当前动作结果通过终端日志进行观察。

## 当前控制流

`mosquitto_pub`
→ MQTT Broker
→ command Topic
→ `on_message()`
→ `parse_command_payload()`
→ `execute_command()`
→ 模拟 LED ON/OFF

## 模块关系

`parse_command_payload()` 负责把 MQTT 消息解析为合法命令。

`execute_command()` 只负责根据命令执行动作。

`on_message()` 负责连接 MQTT 消息接收、命令解析和命令执行三个步骤。

这样的拆分使解析逻辑和执行逻辑彼此独立，后续更容易进行测试和扩展。

## 当前验证状态

已经在 Linux 用户态程序中验证 `led_on`、`led_off` 和未知命令处理。

当前仍然是模拟 LED 动作，尚未通过 UART 把控制命令发送给真实 STM32 终端。

## 后续计划

* 将模拟执行替换为 UART 控制命令下发；
* 设计 STM32 可以识别的控制协议；
* 增加命令执行结果反馈；
* 增加非法命令日志；
* 后续支持更多执行器和场景命令。
