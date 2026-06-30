---

title: STM32F407VET6 V2 Day 1 核心硬件验证
project: STM32 环境感知与执行控制终端
system_layer: 设备层 / 终端节点
document_type: hardware_validation
status: verified
last_updated: 2026-06-30
tags: [STM32F407VET6, GPIO, PA1, D2, ST-LINK, SWD]
--------------------------------------------------

# STM32F407VET6 V2 Day 1 核心硬件验证

## 今日目标

验证 STM32F407VET6 核心板能够正常供电、下载程序并控制板载 LED，为后续从零重构各个外设模块建立最小可运行基础。

## 硬件与连接

* 目标板：STM32F407VET6 核心板
* 供电方式：Type-C
* 下载器：独立 ST-LINK V2
* 调试连接：SWDIO、SWCLK、GND
* 验证外设：板载 D2 LED
* D2 对应引脚：PA1
* LED 特性：低电平点亮

## 软件配置

使用 STM32CubeMX 配置 PA1 为 GPIO 输出，由生成的 `MX_GPIO_Init()` 完成 GPIO 时钟、初始电平和输出模式配置。

应用逻辑通过 HAL GPIO 控制函数改变 PA1 输出状态，实现板载 D2 周期闪烁。

## 验证结果

程序能够通过 ST-LINK SWD 接口正常下载到目标板。

使用 Type-C 为核心板供电后，板载 D2 能够按照程序设定周期闪烁，说明核心板供电、下载链路、GPIO 初始化和基础程序执行均正常。

## 当前理解

目前能够理解：

* PA1 是 STM32 芯片的 GPIO 引脚；
* D2 是连接到 PA1 的板载 LED；
* `LED_D2_GPIO_Port` 和 `LED_D2_Pin` 是 CubeMX 生成的引脚宏；
* `MX_GPIO_Init()` 负责硬件初始化；
* GPIO 控制函数负责运行期间改变引脚状态。

仍需要继续学习：

* SWDIO 和 SWCLK 的具体通信作用；
* GPIO 时钟、初始化层与业务控制层之间的关系；
* CubeMX 生成代码和用户代码区的边界。

## 在 EdgeAIoT 系统中的意义

本次验证建立了设备层终端的最小可运行基础。

后续传感器采集、OLED 显示、执行器控制和 UART 网关通信，都需要建立在核心板能够稳定供电、下载和运行程序的基础上。
