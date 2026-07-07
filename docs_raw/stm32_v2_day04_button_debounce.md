---
title: STM32F407VET6 V2 Day 4 板载按键输入与软件消抖
project: STM32 环境感知与执行控制终端
system_layer: 设备层 / 终端节点
document_type: hardware_validation
status: verified
last_updated: 2026-07-03
tags: [STM32F407VET6, GPIO, PA0, S1, debounce, D2, button_event]
---

# STM32F407VET6 V2 Day 4 板载按键输入与软件消抖

## 今日目标

完成板载 S1 按键的 GPIO 输入读取、状态变化检测和基础软件消抖，并在确认按下事件后翻转板载 D2。

本次任务的重点不是单纯实现“按键控制 LED”，而是建立从物理电平到软件按键事件的基础数据链路。

## 硬件与 CubeMX 配置

板载按键 S1 连接到 PA0。

电路状态：

- 松开按键：PA0 由内部下拉保持为低电平；
- 按下按键：PA0 与 3.3V 接通，变为高电平。

CubeMX 配置：

- GPIO Mode：Input；
- Pull-up/Pull-down：Pull-down；
- User Label：KEY_S1。

因此 S1 属于高电平有效按键。

板级配置中使用：

- `BOARD_KEY_GPIO_PORT`
- `BOARD_KEY_GPIO_PIN`
- `BOARD_KEY_ACTIVE_LEVEL`
- `BOARD_KEY_INACTIVE_LEVEL`

将 CubeMX 生成的具体引脚名称映射为项目统一名称。

## 核心函数与变量

使用：

`HAL_GPIO_ReadPin(BOARD_KEY_GPIO_PORT, BOARD_KEY_GPIO_PIN)`

读取按键电平。

返回类型为 `GPIO_PinState`，可能的返回值为：

- `GPIO_PIN_SET`
- `GPIO_PIN_RESET`

关键变量：

`key_s1_status`

保存本次从 PA0 读取到的当前状态。

`last_key_s1_status`

保存上一次已经确认的稳定状态。

当前状态表示“现在读到了什么”，稳定状态表示“软件已经确认并处理过的状态”。

## 状态变化检测

如果程序只判断按键当前是否为高电平，那么在保持按住期间，循环会不断执行按下逻辑。

因此只有当：

`key_s1_status != last_key_s1_status`

时，才认为按键可能发生了状态变化。

可能的状态变化包括：

- 松开到按下；
- 按下到松开。

完成事件处理后，需要更新稳定状态。否则程序会持续认为状态尚未被记录，重复输出同一个事件。

## 软件消抖流程

机械按键在按下或松开的瞬间，触点可能出现短时间反复接通和断开的现象，例如：

`0 → 1 → 0 → 1 → 1`

这属于机械按键抖动。

当前基础消抖流程：

1. 第一次读取按键状态；
2. 将当前状态与稳定状态比较；
3. 如果两者不同，等待约 20 ms；
4. 第二次读取按键状态；
5. 如果第二次读取仍然与稳定状态不同，则确认状态真正改变；
6. 输出按下或释放事件；
7. 更新稳定状态。

状态变化检测解决“按住时重复执行”的问题。

软件消抖解决“一次物理操作被识别成多次变化”的问题。

## 输入与输出

输入：

- PA0 的实时 GPIO 电平；
- 板级配置中的按键有效电平和无效电平。

输出：

- `KEY PRESSED` 日志；
- `KEY RELEASED` 日志；
- 确认按下时翻转板载 D2。

## 验证结果

按下 S1：

- 输出 `KEY PRESSED`；
- 板载 D2 翻转一次。

保持按住：

- 不重复打印；
- D2 不重复翻转。

松开 S1：

- 输出 `KEY RELEASED`；
- D2 状态不改变。

编译结果：

- 0 Error；
- 0 Warning。

## 当前边界

当前消抖通过 `HAL_Delay(20)` 实现，属于阻塞式消抖。

在当前裸机基础验证中可以接受，但后续加入 OLED、传感器、ESP8266 和 FreeRTOS 后，不能让程序长时间停在按键处理函数中。

后续需要升级为：

- `HAL_GetTick()` 非阻塞计时；
- 按键状态机；
- 按下、释放、短按和长按事件输出。

## 在 EdgeAIoT 系统中的意义

本次任务建立了设备层输入事件的基础链路：

物理按键电平
→ GPIO 输入读取
→ 软件消抖
→ 按下与释放事件
→ LED、页面或模式控制

后续 OLED 页面切换、工作模式切换和本地设备控制都可以建立在统一按键事件之上。