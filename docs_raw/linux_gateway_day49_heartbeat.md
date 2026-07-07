---
title: Linux-STM32 物联网边缘网关 Day 49 应用层 Heartbeat
project: Linux-STM32 物联网边缘网关
system_layer: 通信层 / 数据中枢
document_type: software_module_record
status: software_verified
last_updated: 2026-07-03
tags: [Linux, Python, MQTT, Heartbeat, monotonic, JSON, gateway_status]
---

# Linux-STM32 物联网边缘网关 Day 49 应用层 Heartbeat

## 今日目标

为持续运行的 Linux 网关增加应用层 Heartbeat，使上层系统能够通过固定周期消息判断网关业务进程是否仍在运行。

本次实测中，网关约每 10 秒发布一次 Heartbeat。

## 新增文件与配置

新增文件：

`gateway_status.py`

职责：

构造 Linux 网关自身的状态消息。

`config.json` 新增：

`heartbeat_interval`

当前值为 10，表示约每 10 秒发布一次 Heartbeat。

## Heartbeat Topic

`edgeaiot/gateway/linux_stm32_gateway_01/heartbeat`

该 Topic 用于向 Orange Pi、Web 页面或监控程序发布网关在线状态。

它与以下 Topic 职责不同：

- Telemetry：上传 STM32 设备数据；
- Command：接收上层控制命令；
- ACK：返回命令执行结果；
- Heartbeat：定期证明网关业务进程仍在运行。

## Heartbeat Payload

当前心跳数据包含：

- `gateway`：Linux 网关身份；
- `device`：网关当前负责的 STM32 节点；
- `status`：当前业务状态；
- `timestamp`：心跳生成时间。

示例：

```json
{
  "gateway": "linux_stm32_gateway_01",
  "device": "stm32_node_01",
  "status": "online",
  "timestamp": "2026-07-03 21:55:46"
}