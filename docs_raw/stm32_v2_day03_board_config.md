---

title: STM32F407VET6 V2 Day 3 板级配置层
project: STM32 环境感知与执行控制终端
system_layer: 设备层 / 终端节点
document_type: software_module_record
status: software_verified
last_updated: 2026-07-02
tags: [STM32F407VET6, board_config.h, GPIO, UART, hardware_mapping]
---
# STM32F407VET6 V2 Day 3 cfg硬件板层映射
## 目标
将核心代码与配置管脚设置解耦，以便于后续代码迁移以及代码配置，并且增加代码可读性
## 核心文件或数据结构
User/Board/board_config.h
## 输入输出
输入：
CubeMX 生成的具体硬件符号，例如 LED_D2_GPIO_Port、
LED_D2_Pin 和 huart2

输出：
项目统一使用的板级名称，例如 BOARD_LED_GPIO_PORT、
BOARD_LED_GPIO_PIN 和 BOARD_DEBUG_UART_HANDLE
## 数据流或控制流
HAL库原映射 → 头文件建立映射 → main.c文件引用
## 验证结果
HAL_LED_GPIOA可映射为BOARD_LED_PORT
## 当前边界
board_config.h 只负责硬件名称映射，不负责 GPIO、USART 初始化，
也不负责 LED 闪烁和串口打印等业务逻辑。