---
title: Linux-STM32 物联网边缘网关 Day 54 持续串口读取与 MQTT Telemetry 主循环
project: Linux-STM32 物联网边缘网关
system_layer: 通信层 / 数据中枢
document_type: software_module_record
status: software_verified
last_updated: 2026-07-18
tags: [Linux, Python, Serial, MQTT, Telemetry, MainLoop, MockData, FaultTolerance]
---

# Linux-STM32 物联网边缘网关 Day 54 持续串口读取与 MQTT Telemetry 主循环

## 今日目标

将原来只处理一次串口或 Mock 数据的流程，改造成持续运行的网关主循环：

```text
持续获取设备数据
→ 解析串口文本
→ 生成 Telemetry Payload
→ MQTT 在线时发布
→ 继续下一轮读取
```

同时保证：

- 非法串口数据不发布；
- MQTT 离线时主循环不退出；
- 串口只在启动时打开一次；
- 程序退出时统一关闭串口；
- 真实串口不可用时可以回退到 Mock 模式。

## 今日完成内容

完成了以下功能：

- 将数据读取放入持续主循环；
- 真实串口和 Mock 模式统一产出 `serial_data`；
- 使用 `process_serial_data()` 统一解析数据；
- 解析成功后生成 `payload`；
- 只有 `payload` 有效且 MQTT 已连接时才发布；
- 非法数据不会再被发布为 `(null)`；
- 串口在进入主循环前只打开一次；
- 程序退出时统一关闭串口；
- 真实串口打开失败时可以回退到 Mock 数据；
- MQTT 离线时仍可以继续本地读取和解析。

## 主循环数据流

当前主循环的核心流程：

```text
判断当前使用真实串口还是 Mock
→ 得到 serial_data
→ 调用 process_serial_data(serial_data)
→ 得到 payload
→ 判断 payload 是否有效
→ 判断 MQTT 是否已连接
→ 发布 Telemetry
→ sleep
→ 进入下一轮
```

伪代码结构：

```python
while True:
    serial_data = ...

    payload = process_serial_data(serial_data)

    if (
        payload is not None
        and mqtt_client is not None
        and mqtt_client.is_connected()
    ):
        publish_telemetry(payload)

    time.sleep(0.1)
```

## serial_data 的职责

`serial_data` 表示设备层产生的一行原始文本。

它可能来自：

```text
真实 STM32 USART2
或
Mock 数据生成器
```

例如：

```text
temperature:26.0
```

这一层只负责得到原始数据，不直接决定 MQTT Payload 结构。

## process_serial_data() 的职责

`process_serial_data()` 负责：

```text
接收原始串口文本
→ 判断格式是否合法
→ 提取字段和值
→ 转换数据类型
→ 生成统一 Payload
```

输入：

```text
temperature:26.0
```

输出示例：

```python
{
    "temperature": 26.0,
}
```

如果输入非法，则返回：

```python
None
```

因此主循环必须判断：

```python
payload is not None
```

之后才能发布。

## 修复非法数据发布问题

此前非法串口数据可能继续进入 MQTT 发布阶段，最终出现：

```text
(null)
```

或无效 Telemetry。

修复后的判断：

```text
解析成功
→ payload 为字典
→ 可以继续判断 MQTT 状态

解析失败
→ payload 为 None
→ 跳过本轮发布
```

这样可以保证只有有效设备数据进入 MQTT。

## 为什么串口只打开一次

错误方式是每轮循环都执行：

```text
打开串口
→ 读取一次
→ 关闭串口
```

这会造成：

- 重复创建文件描述符；
- 频繁打开和关闭设备；
- 增加延迟；
- 更容易发生资源异常；
- 不利于持续数据流。

当前方式：

```text
程序启动
→ open_ser_port()
→ 进入持续读取循环
→ 程序退出
→ close_ser_port()
```

串口生命周期与网关进程生命周期保持一致。

## 串口模块职责拆分

当前串口模块已经拆分为：

```text
open_ser_port()
→ 打开并配置串口

read_data_from_port()
→ 从已经打开的串口读取数据

close_ser_port()
→ 程序退出时关闭串口
```

这样避免把打开、读取和关闭全部混在一个函数中。

## 串口超时与主循环间隔

当前串口读取超时：

```text
timeout = 0.2 秒
```

主循环每轮休眠：

```text
sleep = 0.1 秒
```

串口超时用于避免：

```text
设备没有发送数据
→ read 永久阻塞
→ 网关无法继续执行其他逻辑
```

主循环休眠用于避免：

```text
无数据时持续高速空转
→ CPU 占用过高
```

## MQTT 发布条件

当前只有同时满足以下条件时才发布：

```text
payload 不为 None
MQTT Client 已创建
MQTT Client 当前已连接
```

对应判断：

```python
payload is not None
and mqtt_client is not None
and mqtt_client.is_connected()
```

三层判断分别解决：

```text
payload is not None
→ 数据解析有效

mqtt_client is not None
→ MQTT 功能已经初始化

mqtt_client.is_connected()
→ 当前 Broker 连接可用
```

## MQTT 离线时的行为

MQTT 离线时：

```text
串口读取仍然继续
process_serial_data() 仍然继续
本地 Payload 生成仍然继续
仅跳过 MQTT publish
```

这说明：

```text
设备数据接入
与
MQTT 网络发布
```

已经具备一定程度的解耦。

当前还没有实现离线缓存，因此 MQTT 离线期间的数据不会在恢复后自动补发。

## 真实串口失败时回退 Mock

如果配置使用真实串口，但串口打开失败，程序可以回退到 Mock 模式。

流程：

```text
尝试打开真实串口
→ 打开失败
→ 输出错误日志
→ 切换或回退到 Mock 数据
→ 主程序继续运行
```

这样可以在没有连接 STM32 时继续验证：

- 数据解析；
- Payload 构造；
- MQTT 发布；
- Heartbeat；
- Command 与 ACK。

## 软件验证结果

当前使用：

```text
use_real_serial = false
mqtt_enabled = true
```

验证了：

```text
Mock 数据持续产生
→ process_serial_data() 解析
→ 生成 Telemetry Payload
→ MQTT 连续发布多轮
```

至少完成了两轮持续发布验证，说明主循环不再只执行一次。

## 当前完整数据流

Mock 模式：

```text
Mock 数据
→ serial_data
→ process_serial_data()
→ payload
→ MQTT Telemetry
```

真实模式目标：

```text
STM32 USART2
→ Linux 串口设备
→ read_data_from_port()
→ serial_data
→ process_serial_data()
→ payload
→ MQTT Telemetry
```

## 当前边界

Day 54 已经完成软件主循环和 Mock 验证，但尚未完成：

- STM32 与 Linux 的真实 USB 串口持续联调；
- 波特率、端口名和权限验证；
- 串口拔出后的自动恢复；
- 串口数据粘包与半包处理；
- MQTT 离线数据缓存；
- 多字段正式串口协议；
- 串口读取与 MQTT 发布的线程化解耦。

## 面试时怎么讲

我将网关的数据接入逻辑改造成了持续运行的主循环。

真实串口和 Mock 模式都先产生统一的 `serial_data`，再交给 `process_serial_data()` 完成格式校验、字段解析和 Payload 构造。

只有在 Payload 有效、MQTT Client 已创建且 Broker 当前已连接时，才会发布 Telemetry，从而避免非法数据被发布成 `(null)`。

串口在程序启动时只打开一次，主循环中持续读取，退出时统一关闭。真实串口打开失败时可以回退到 Mock 模式，保证其他软件链路仍然能够验证。

目前已经完成 Mock 数据的多轮持续发布，下一步是接入 STM32 的真实 USART2 数据。

## 后续计划

- 将 STM32 通过 USB 转串口连接到 Linux；
- 确认 `/dev/ttyUSB0` 或实际串口设备；
- 将波特率与 STM32 USART2 对齐；
- 持续读取 `temperature:<value>`；
- 验证真实 Telemetry 发布；
- 测试非法串口数据；
- 测试串口拔出和重新连接。
