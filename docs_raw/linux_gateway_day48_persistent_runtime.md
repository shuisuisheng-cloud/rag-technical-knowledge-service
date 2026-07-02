---

title: Linux-STM32 物联网边缘网关 Day 48 持续运行与安全退出
project: Linux-STM32 物联网边缘网关
system_layer: 通信层 / 数据中枢
document_type: software_module_record
status: software_verified
last_updated: 2026-07-02
tags: [Linux, Python, MQTT, disconnect, main.py, EdgeAIoT, KeyboardInterrupt]
---
# Linux-STM32 物联网边缘网关 Day 48 持续运行与安全退出
## 目标
通过 while True 保持主程序运行，循环内部使用 time.sleep(1) 避免空转占满 CPU。，并且新增disconnect_mqtt_client(client)函数，作为退出函数，用ctrl+c来退出终端MQTT等待
## 核心文件或数据结构
disconnect_mqtt_client(client)函数
## 输入输出
输入CTRL+c，输出断开 MQTT 连接并停止网络循环。
## 数据流或控制流
连接 MQTT
→ 进入 while True 常驻循环
→ 用户按 Ctrl+C
→ 触发 KeyboardInterrupt
→ 进入 finally
→ disconnect()
→ loop_stop()
→ 程序安全退出
## 验证结果
网关运行超过 15 秒后仍保持在线；
led_on、led_off 和 ACK 链路仍正常；
按 Ctrl+C 后能够清理 MQTT 连接并退出；
当前仍是 Linux 用户态软件闭环，没有通过 UART 控制真实 STM32
## 当前边界
目前验证的是 Linux 用户态网关常驻运行和 MQTT 安全退出，
尚未接入真实 STM32 UART 数据链路，也不是后台系统服务。