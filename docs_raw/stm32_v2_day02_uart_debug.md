---

title: STM32F407VET6 V2 Day 2 UART2调试串口
project: STM32 环境感知与执行控制终端
system_layer: 设备层 / 终端节点
document_type: hardware_validation
status: verified
last_updated: 2026-07-01
tags: [STM32F407VET6, UART, PA2, PA3, ST-LINK, SWD, USB-TTL]
---
# STM32F407VET6 V2 Day 2 USART2 调试串口

## 今日目标
为什么要单独配置一个调试串口？
为了通信解耦，UART1之后用来ESP8266调试和通信，UART2用来串口通信和调试
## 硬件连接
PA2、PA3、USB-TTL 分别怎样连接？为什么需要共地？
USB-TTL RX → STM32 PA2（TX）
USB-TTL TX → STM32 PA3（RX）
GND → GND
## 串口参数
115200 和 8N1 分别是什么意思？
115200 表示每秒传输约 115200 bit。8N1 下一个字节通常包含 1 位起始位、8 位数据位和 1 位停止位，共 10 bit，理论上约为 11520 字节/秒。
## 核心函数
HAL_UART_Transmit(&huart2，message，size，timeout) 的几个参数分别代表什么？
&huart2 是 UART_HandleTypeDef 句柄变量的地址，不只是“USART2 的标识”；size 表示发送字节数，timeout 通常以毫秒为单位。
## printf 重定向
printf 最终怎样经过 fputc() 发送到 USART2？
先把所要发送的字符转化为字符序列，每个字符序列单独通过一次fputc（），通过HAL_UART_Transmit()函数发送到USART2
## 验证结果
电脑串口终端看到了什么？
看到了发送的结果
## 当前掌握情况
哪些内容已经理解，哪些函数名称还记不牢？
HAL库函数未记牢
## 在 EdgeAIoT 系统中的意义
调试串口对后续传感器、网关通信和异常排查有什么帮助？
为后面程序的每一步可打印，排查有哪一步没有执行成功