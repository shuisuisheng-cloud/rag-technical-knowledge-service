---
title: STM32 环境感知与执行控制终端 V2 Day 12 USART2 硬件错误识别与中断接收恢复
project: STM32 环境感知与执行控制终端
system_layer: 设备层 / 终端节点
document_type: daily_dev_record
status: verified
last_updated: 2026-08-11
tags: [STM32F407, USART2, UART, HAL, Interrupt, ORE, FE, NE, ErrorRecovery]
---

# STM32 环境感知与执行控制终端 V2 — Day 12

## 一、今日主题

USART2 硬件错误识别与中断接收恢复。

Day 11 解决的是：

```text
字节已经进入 USART2 接收回调
→ 判断这一行的数据是否可信
→ 非法字节或软件缓冲区溢出
→ 整行丢弃到 \n
```

Day 12 解决的是：

```text
USART2 本身发生硬件错误
→ HAL 当前接收任务可能受到影响
→ 当前命令作废
→ 判断接收链是否需要重新建立
→ 必要时重新调用 HAL_UART_Receive_IT()
```

两天的职责边界：

```text
Day 11
→ 协议层坏行处理

Day 12
→ UART 硬件错误与 HAL 接收链恢复
```

---

## 二、为什么还需要 Day 12

Day 11 已经能够处理：

```text
非法字节
超长命令
损坏行
空行
```

但这些逻辑成立的前提是：

```text
USART2 接收中断仍然正常工作
→ 字节还能进入 HAL_UART_RxCpltCallback()
```

如果 UART 发生：

```text
ORE
FE
NE
PE
```

等硬件错误，问题已经不只是：

```text
这一行内容是否合法
```

而是：

```text
HAL 当前 UART 接收任务
是否还能继续工作
```

特别是 ORE 可能导致 HAL 结束当前接收任务。

因此必须增加：

```c
HAL_UART_ErrorCallback()
```

处理硬件错误。

---

## 三、UART 硬件错误类型

STM32F4 HAL UART 主要识别：

```text
PE
NE
FE
ORE
```

---

### 1. PE — Parity Error

```text
奇偶校验错误
```

当前 USART2 配置：

```text
115200
8N1
无奇偶校验
```

因此 PE 在当前配置下通常不会出现。

---

### 2. NE — Noise Error

```text
Noise Error
噪声错误
```

表示 UART 采样过程中检测到电平不稳定。

可能与：

```text
线路干扰
USB-TTL 插拔瞬间
接触不稳定
电气噪声
```

有关。

---

### 3. FE — Frame Error

```text
Frame Error
帧错误
```

UART 应该检测停止位时没有得到正确高电平。

可能原因：

```text
波特率不匹配
数据帧被中途截断
USB-TTL 插拔期间线路异常
信号质量问题
```

---

### 4. ORE — Overrun Error

```text
Overrun Error
硬件接收溢出
```

含义：

```text
UART 数据寄存器中的旧数据
还没有及时被软件读取
→ 新字节已经到来
→ 数据发生丢失
```

ORE 与 Day 11 的软件 buffer overflow 不同。

### 软件缓冲区溢出

```text
uart2_rx_buffer[64]
→ 软件数组空间不足
```

属于：

```text
协议 / 软件层
```

Day 11 处理。

### ORE

```text
UART 硬件寄存器中的数据
没有及时被取走
```

属于：

```text
UART 硬件层
```

Day 12 处理。

---

## 四、HAL UART 错误处理调用链

通过本地 HAL 源码确认：

```text
USART2 出现硬件错误
↓
USART2_IRQHandler()
↓
HAL_UART_IRQHandler(&huart2)
↓
检查 PE / NE / FE / ORE
↓
错误位写入 huart2.ErrorCode
↓
HAL_UART_ErrorCallback(&huart2)
```

因此用户代码不需要自己重新实现一套：

```text
读取 UART 状态寄存器
→ 判断具体错误位
```

HAL 已经把底层硬件错误整理到：

```c
huart->ErrorCode
```

用户代码主要负责：

```text
读取 ErrorCode
→ 根据错误类型恢复自己的软件状态
```

---

## 五、ErrorCode 是位标志

UART 错误可能不是一次只出现一个。

可能存在：

```text
FE | ORE
```

或者：

```text
NE | ORE
```

因此不能只判断：

```c
current_error == HAL_UART_ERROR_ORE
```

更合理的是：

```c
(current_error & HAL_UART_ERROR_ORE) != 0U
```

含义：

```text
不管 ErrorCode 中还有没有其他错误
只要 ORE 这一位存在
→ 就执行 ORE 对应处理
```

这属于典型的：

```text
位掩码判断
```

---

## 六、阻塞性错误的含义

这里所说的：

```text
blocking error
```

不是：

```text
程序进入 while 或 HAL_Delay
```

而是：

```text
HAL 是否会终止当前 UART 接收任务
```

---

## 七、FE / NE / PE

在当前普通中断接收模式下：

```text
FE
NE
PE
```

通常属于非阻塞错误。

HAL 大致处理：

```text
记录 ErrorCode
→ 调用 HAL_UART_ErrorCallback()
→ 原 RX 接收任务仍可能继续
```

此时：

```text
huart2.RxState
```

可能仍然是：

```text
HAL_UART_STATE_BUSY_RX
```

如果用户在 ErrorCallback 中无条件再次：

```c
HAL_UART_Receive_IT()
```

就可能得到：

```text
HAL_BUSY
```

因此：

```text
发生任何 UART 错误
→ 无条件重新 Receive_IT
```

不是正确策略。

---

## 八、ORE 为什么特殊

ORE 在当前 HAL 中属于需要特别处理的错误。

大致过程：

```text
检测到 ORE
→ UART_EndRxTransfer()
→ 关闭当前接收相关中断
→ RxState 变为 READY
→ 调用 HAL_UART_ErrorCallback()
```

这意味着：

```text
旧 HAL_UART_Receive_IT() 接收任务
已经结束
```

如果用户什么都不做：

```text
后续 UART 字节
可能无法继续进入 RxCpltCallback
```

因此：

```text
ErrorCode 中包含 ORE
→ 重新调用 HAL_UART_Receive_IT()
```

重新建立：

```text
单字节中断接收链
```

---

## 九、为什么不能所有错误都重新 Receive_IT

错误做法：

```text
进入 ErrorCallback
→ 不看错误类型
→ 永远 HAL_UART_Receive_IT()
```

问题：

```text
FE / NE 发生时
→ HAL 原接收任务可能仍然处于 BUSY_RX
→ 再次 Receive_IT
→ HAL_BUSY
```

因此正确判断：

```text
ErrorCode 不包含 ORE
→ 不重复启动 RX

ErrorCode 包含 ORE
→ HAL 已结束旧 RX
→ 重新启动 Receive_IT
```

---

## 十、DMA 分支为什么可以暂时不管

HAL UART 源码同时支持：

```text
Interrupt Receive
DMA Receive
ReceiveToIdle
注册式 Callback
传统 weak Callback
```

所以源码中会看到：

```text
dmarequest
```

等逻辑。

当前工程使用的是：

```c
HAL_UART_Receive_IT()
```

不是：

```text
UART DMA
```

因此正常情况下：

```text
dmarequest = 0
```

当前工程主要关注：

```text
普通中断接收路径
+
是否包含 ORE
```

不用把 HAL 中所有 DMA 分支全部实现一遍。

---

## 十一、新增 UART 错误诊断变量

新增：

```c
static volatile uint32_t uart2_error_code =
    HAL_UART_ERROR_NONE;

static volatile uint8_t uart2_error_pending = 0U;

static volatile uint8_t uart2_rx_restart_failed = 0U;
```

---

## 十二、uart2_error_code

职责：

```text
保存发生过的 UART 错误位
```

采用：

```c
uart2_error_code =
    uart2_error_code | current_error;
```

而不是简单：

```c
uart2_error_code = current_error;
```

原因：

第一次：

```text
NE
```

第二次：

```text
FE | ORE
```

如果直接赋值：

```text
第一次 NE 会被覆盖
```

使用按位 OR 累积：

```text
NE
|
FE
|
ORE
```

最终可以知道曾发生过哪些类型错误。

---

## 十三、uart2_error_pending

```c
uart2_error_pending = 1U;
```

表示：

```text
已经发生过新的 UART 错误事件
但主循环还没有专门消费该诊断状态
```

当前阶段主要完成：

```text
错误记录
+
接收恢复
```

没有直接在 USART2 中断里打印错误信息。

---

## 十四、为什么 ErrorCallback 里不 printf

`HAL_UART_ErrorCallback()` 仍然运行在 UART 中断上下文。

中断中应该尽量只做：

```text
读取错误码
修改少量状态
清理当前接收状态
必要时重新预约接收
```

不应该执行：

```text
printf
HAL_Delay
复杂字符串处理
长循环
大量日志
```

原因：

```text
延长中断执行时间
→ 增加实时性问题
→ 可能产生新的 UART 接收问题
```

另外当前 USART2 本身就是：

```text
STM32 ↔ Linux Gateway
```

通信链路。

如果直接向 USART2 打印错误日志，还可能：

```text
把诊断文本混入正式通信协议
```

---

## 十五、uart2_rx_restart_failed

当 ORE 后执行：

```c
HAL_UART_Receive_IT()
```

如果返回值不是：

```text
HAL_OK
```

则：

```c
uart2_rx_restart_failed = 1U;
```

它可以记录：

```text
HAL_BUSY
HAL_ERROR
或其他非 HAL_OK 状态
```

说明：

```text
接收链恢复尝试没有成功
```

---

## 十六、ErrorCallback 的完整职责

核心流程：

```text
HAL_UART_ErrorCallback()
↓
确认 huart 对应 USART2
↓
立即保存 huart->ErrorCode
↓
累计到 uart2_error_code
↓
uart2_error_pending = 1
↓
作废当前正在组装的命令
↓
判断 current_error 是否包含 ORE
```

不包含 ORE：

```text
原中断 RX 通常仍继续
→ 不重新调用 Receive_IT
```

包含 ORE：

```text
HAL 已结束旧 RX
→ HAL_UART_Receive_IT()
→ 重新建立单字节接收
```

如果 restart 失败：

```text
uart2_rx_restart_failed = 1
```

---

## 十七、UART 硬件错误后为什么必须作废当前命令

假设正在接收：

```text
led_
```

随后出现：

```text
FE / ORE
```

之后又收到：

```text
on\r\n
```

此时无法保证：

```text
led_
+
on
```

之间是否已经发生字节丢失或数据损坏。

因此 UART 硬件错误后：

```text
当前命令已经不可信
```

需要清理：

```c
uart2_rx_index = 0U;
uart2_line_ready = 0U;
uart2_rx_buffer[0] = '\0';
uart2_line_invalid = 1U;
```

---

## 十八、为什么 line_invalid 要设为 1

硬件错误发生后不能：

```text
清空 buffer
→ 马上把后续字符当成新命令
```

假设：

```text
led_
→ UART Error
→ on\r\n
```

如果错误后直接：

```text
line_invalid = 0
```

那么：

```text
on
```

可能会被错误当作一条新的完整命令。

正确策略：

```text
UART Error
→ 当前行 invalid
→ 后续字符继续丢弃
→ 一直等到 '\n'
→ 损坏行结束
→ 下一行重新开始
```

这与 Day 11 的坏行状态机保持一致。

---

## 十九、Day 11 + Day 12 的配合

### Day 11

处理：

```text
非法内容
软件 buffer overflow
```

结果：

```text
line_invalid = 1
→ 丢弃到 '\n'
```

### Day 12

处理：

```text
UART Hardware Error
```

结果：

```text
作废当前 buffer
→ line_invalid = 1
→ 必要时恢复 HAL RX
→ 丢弃到 '\n'
```

因此两个层次最终统一进入：

```text
损坏行安全丢弃
```

---

## 二十、为什么 Gateway 重连后需要发送同步换行

UART ErrorCallback 会：

```text
uart2_line_invalid = 1
```

此时 STM32 会一直等待：

```text
'\n'
```

结束损坏行。

如果 Linux Gateway 重连后直接发送：

```text
led_on\r\n
```

可能发生：

```text
STM32 此时仍处于 invalid
→ l e d _ o n 全部丢弃
→ 最后的 \n 只负责清除 invalid
→ 第一条业务命令没有执行
→ 没有 ACK
→ Gateway timeout
```

因此 Gateway 新建立串口会话后，应先：

```text
发送 \r\n
```

数据流：

```text
Gateway 打开串口
→ 发送 \r\n
→ STM32 忽略 \r
→ \n 结束可能残留的 invalid 行
→ 空行不执行
→ 下一条业务命令从干净边界开始
```

---

## 二十一、为什么这个同步空行是安全的

如果 STM32 当前：

```text
line_invalid = 1
```

那么：

```text
\n
→ 结束坏行
```

如果 STM32 当前：

```text
line_invalid = 0
```

那么：

```text
\r\n
→ 形成空行
→ Day 11 逻辑直接忽略
```

因此：

```text
无论当前 STM32 是否处于坏行状态
同步 \r\n 都不会执行任何业务命令
```

---

## 二十二、中断回调设计原则

UART ErrorCallback 中只执行：

```text
读取 current_error
累计诊断状态
标记 error_pending
清理当前命令
设置 line_invalid
必要时重新 Receive_IT
记录 restart 是否失败
```

避免：

```text
printf
HAL_Delay
命令解析
LED 控制
复杂业务逻辑
Error_Handler
```

核心原则：

```text
ISR / Callback
→ 快速记录和恢复

Main Loop
→ 复杂业务和诊断
```

---

## 二十三、Day 12 完成内容

```text
✓ 理解 PE / NE / FE / ORE
✓ 区分软件缓冲区溢出与硬件 ORE
✓ 阅读本地 HAL UART 错误处理源码
✓ 跟踪 USART2_IRQHandler → HAL_UART_IRQHandler
✓ 理解 huart->ErrorCode
✓ 理解 HAL UART 错误位掩码
✓ 区分 ORE 与 FE / NE 的 RX 状态差异
✓ 新增 uart2_error_code
✓ 新增 uart2_error_pending
✓ 新增 uart2_rx_restart_failed
✓ 实现 HAL_UART_ErrorCallback()
✓ UART 错误后作废当前命令
✓ UART 错误后 line_invalid = 1
✓ 仅在包含 ORE 时重新启动 HAL_UART_Receive_IT()
✓ 检查 HAL_UART_Receive_IT() 返回状态
✓ 保持中断回调短小
✓ 编译通过
✓ 烧录最新固件
✓ Git Commit
✓ Push 到远程仓库
```

---

## 二十四、Git 提交

```text
6ee4b9d feat: recover USART2 reception after UART errors
```

最终状态：

```text
working tree clean
```

本地：

```text
v2-f407-core-board
```

与远程分支已经同步。

---

## 二十五、代码阶段与系统验收阶段的边界

Day 12 在 STM32 仓库中的：

```text
代码实现
编译
烧录
提交
```

已经完成。

但当时仍有一部分系统级真实验收需要交给：

```text
Linux Gateway Day 60
```

完成。

计划验证：

```text
USB-TTL 运行中拔出
→ Gateway 检测断开
→ USB 重新插入并 attach WSL
→ Gateway 自动重连
→ Gateway 发送同步 \r\n
→ STM32 结束可能残留 invalid 行
→ 第一条 led_on 成功
→ 第二条 led_off 成功
→ DHT11 Telemetry 正常
→ 无重复 ACK
→ USART2 RX 接收链持续工作
```

---

## 二十六、后来在 Gateway Day 60 的系统验收结果

Day 60 已进一步完成跨端验证：

```text
Gateway 首次打开串口
→ 协议边界同步

Gateway 自动重连
→ 协议边界同步
```

并进行了至少三轮：

```text
USB-TTL 断开
→ 重连
→ 同步 \r\n
→ 第一条业务命令
```

第一条：

```text
led_on / led_off
```

均直接得到：

```text
rx
→ ACK
→ MQTT success
```

此前：

```text
重连后第一条 timeout
→ 第二条才成功
```

的问题不再复现。

这说明：

```text
STM32 Day 11 坏行状态机
+
STM32 Day 12 UART 硬件错误恢复
+
Gateway Day 60 串口协议边界同步
```

形成了完整的跨端恢复机制。

---

## 二十七、完整跨端异常恢复数据流

```text
USB / UART 异常
↓
STM32 UART ErrorCallback
↓
保存 ErrorCode
↓
作废当前命令
↓
line_invalid = 1
↓
如果包含 ORE
→ 重新 HAL_UART_Receive_IT()
↓
等待 '\n' 结束损坏行
```

与此同时：

```text
Linux Gateway
→ 检测 USB-TTL 断开
→ 清理 old port
→ 非阻塞重连
→ 得到 candidate port
→ 发送 \r\n
```

STM32：

```text
收到 \r
→ 忽略

收到 \n
→ 结束 invalid 行
→ 恢复正常行状态
```

Gateway：

```text
同步成功
→ Candidate Port
变为
Active Port
```

下一条业务命令：

```text
led_on
→ STM32 RX
→ 命令执行
→ ACK
→ Linux
→ MQTT success
```

---

## 二十八、技术面复述

### 1. Day 11 和 Day 12 的区别是什么？

Day 11：

```text
协议层
→ 已经收到的字节是否可信
```

Day 12：

```text
硬件 / HAL 层
→ UART 发生错误以后接收链是否还能继续
```

---

### 2. 软件 buffer overflow 和 ORE 有什么区别？

软件 overflow：

```text
用户自己的 uart2_rx_buffer 空间不足
```

ORE：

```text
UART 硬件寄存器中的旧数据
还未被软件读取
新数据已经到达
```

两个发生在不同层。

---

### 3. 为什么不能所有 ErrorCallback 都重新 Receive_IT？

因为 FE / NE 等错误发生时：

```text
HAL 原 RX 任务可能仍处于 BUSY_RX
```

再次：

```text
HAL_UART_Receive_IT()
```

可能得到：

```text
HAL_BUSY
```

ORE 时 HAL 才会结束当前 RX，需要重新建立接收。

---

### 4. 为什么使用位与判断 ORE？

因为：

```text
ErrorCode
```

可能同时包含多个错误。

例如：

```text
FE | ORE
```

所以需要判断：

```c
(current_error & HAL_UART_ERROR_ORE) != 0U
```

而不是：

```c
current_error == HAL_UART_ERROR_ORE
```

---

### 5. 为什么 UART Error 后要整行作废？

因为发生硬件错误意味着：

```text
当前命令是否完整
已经无法保证
```

继续拼接剩余字符可能形成一个错误但看似合法的命令。

---

### 6. 为什么 ErrorCallback 后 line_invalid 不能马上清零？

因为错误后的残余字符：

```text
可能仍属于损坏的上一行
```

必须等：

```text
\n
```

明确结束这条损坏消息。

---

### 7. 为什么 Gateway 重连后先发送 \r\n？

用于：

```text
同步 UART 行协议边界
```

如果 STM32 仍处于：

```text
line_invalid
```

则：

```text
\n
```

结束坏行。

如果没有坏行：

```text
\r\n
```

只是空行，不执行任何命令。

---

### 8. 为什么 ErrorCallback 里不 printf？

因为：

```text
它运行在中断上下文
```

需要保持短小，同时 USART2 本身又是 Gateway 正式通信链路，直接打印会污染协议数据。

---

## 二十九、Day 12 最终结论

Day 12 将 STM32 USART2 接收从：

```text
只能处理正常字节流
+
协议层坏行
```

扩展为：

```text
可以识别 UART 硬件错误
→ 保存错误状态
→ 作废当前命令
→ 保持坏行安全策略
→ ORE 后恢复 HAL 中断接收链
```

再结合 Gateway Day 60：

```text
UART / USB 异常
→ STM32 进入安全坏行状态
→ Linux Gateway 重连
→ 主动发送协议同步 \r\n
→ STM32 清除残余坏行
→ 第一条业务命令正常执行
```

因此 STM32 与 Linux Gateway 的 UART 恢复机制已经从：

```text
单端局部处理
```

提升为：

```text
跨端协议协同恢复
```

当前 STM32 已完成：

```text
真实 DHT11 上行
USART2 非阻塞接收
led_on / led_off
真实 ACK
非法字节整行丢弃
超长命令整行丢弃
UART PE / NE / FE / ORE 识别
ORE 后 HAL 接收链恢复
与 Gateway 重连协议同步的真实联调
```

后续不再继续堆 UART 基础功能，进入剩余终端功能整理与阶段验收。
