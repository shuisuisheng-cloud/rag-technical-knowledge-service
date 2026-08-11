---
title: STM32 环境感知与执行控制终端 V2 Day 11 USART2 损坏行安全丢弃
project: STM32 环境感知与执行控制终端
system_layer: 设备层 / 终端节点
document_type: daily_dev_record
status: verified
last_updated: 2026-07-30
tags: [STM32F407, USART2, UART, Interrupt, Protocol, ErrorHandling, Buffer, MQTT]
---

# STM32 环境感知与执行控制终端 V2 — Day 11

## 一、问题背景

真实 MQTT 下行联调中发现：

```text
STM32 复位后
第一条命令偶尔出现异常前缀字节
```

例如：

```text
rx:<异常字节>led_on
ack:<异常字节>led_on:failed
```

Linux Gateway 的 raw hex 日志确认：

```text
0xB5
0x85
0xF9
...
```

等异常字节确实出现在：

```text
led_on
```

之前。

因此问题并不是简单的：

```text
C 数组旧内容没有清零
```

而是：

```text
USART2 在真实业务字符之前
接收或解析到了异常字节
```

旧接收逻辑会把所有：

```text
非 \r
非 \n
```

的字节都写入缓冲区。

于是形成：

```text
异常字节
+
led_on
+
\r\n
```

最终字符串：

```text
!= "led_on"
```

命令解析失败。

---

## 二、Day 11 目标

增强 USART2 行协议安全性。

核心规则：

```text
一行只要出现非法字节
或者
软件接收缓冲区发生溢出

→ 当前整行都不再可信
→ 整行标记损坏
→ 后续所有字节持续丢弃
→ 一直丢弃到 '\n'
→ 不把损坏内容交给命令执行层
```

整体数据流：

```text
USART2 收到单字节
→ 判断 CR / LF
→ 判断当前行状态
→ 判断字符是否合法
→ 判断缓冲区容量

合法完整行
→ 交给主循环

损坏行
→ 整行丢弃
→ 下一行重新开始
```

---

## 三、新增 uart2_line_invalid

新增：

```c
static volatile uint8_t uart2_line_invalid = 0U;
```

含义：

```text
0
→ 当前行仍然可信

1
→ 当前行已经损坏
→ 后续字节必须一直丢弃到换行
```

原有变量继续保留。

### uart2_rx_byte

```text
当前 HAL_UART_Receive_IT()
接收到的一个字节
```

### uart2_rx_buffer

```text
当前正在组装的命令行缓冲区
```

### uart2_rx_index

```text
下一个合法字符写入位置
```

### uart2_line_ready

```text
是否已经形成一条完整合法命令
等待主循环处理
```

---

## 四、为什么 line_invalid 是状态

一旦一行出现：

```text
非法字节
```

后面即使出现：

```text
l
e
d
_
o
n
```

也不能重新认为该行合法。

因此：

```text
非法事件
→ line_invalid = 1
```

之后必须持续保持：

```text
invalid
```

直到：

```text
'\n'
```

真正结束这一行。

这是一个简单的行协议状态机。

---

## 五、合法字符范围

当前命令协议只允许：

```text
可打印 ASCII
```

范围：

```text
0x20 ～ 0x7E
```

包括：

```text
英文字母
数字
下划线
冒号
空格
普通英文符号
```

如果出现：

```text
0xB5
0x85
0xF9
```

等非可打印字节：

```text
uart2_line_invalid = 1
uart2_rx_index = 0
```

之后当前行中的：

```text
led_on
```

也不能继续保存。

---

## 六、收到 \r

当前协议规定：

```text
\r
→ 忽略
```

执行：

```text
不保存
不增加 index
不结束当前行
```

因此：

```text
\r\n
```

真正的行结束由：

```text
\n
```

负责。

---

## 七、收到 \n

### 当前行已经损坏

如果：

```text
uart2_line_invalid == 1
```

则：

```text
uart2_rx_index = 0
uart2_line_invalid = 0
```

同时：

```text
不设置 uart2_line_ready
```

即：

```text
这一整条坏行正式结束
→ 不交给主循环
→ 下一行重新恢复
```

---

### 当前行合法且非空

如果：

```text
line_invalid == 0
且
index > 0
```

则：

```text
buffer[index] = '\0'
→ uart2_line_ready = 1
```

形成合法 C 字符串。

---

### 当前行为空

如果：

```text
index == 0
```

则：

```text
忽略空行
```

不进入命令执行层。

---

## 八、收到普通字节

首先判断：

```text
当前行是否已经 invalid
```

如果已经损坏：

```text
直接丢弃
→ 不保存
→ 不增加 index
→ 一直等待 '\n'
```

如果当前行仍然有效，再判断字符是否合法。

---

## 九、收到非法字节

如果普通字节不属于：

```text
0x20 ～ 0x7E
```

则：

```text
uart2_line_invalid = 1
uart2_rx_index = 0
```

并且：

```text
不尝试继续组装当前命令
```

之后所有字符一直丢弃到：

```text
\n
```

---

## 十、合法字节与缓冲区空间

如果：

```text
字符合法
+
buffer 仍有空间
```

则：

```text
buffer[index] = byte
index++
```

---

## 十一、软件缓冲区溢出

当前：

```text
uart2_rx_buffer[64]
```

需要至少留出一个位置：

```text
'\0'
```

因此最多只能保存：

```text
63 个普通字符
```

如果继续收到第 64 个普通字符：

```text
软件缓冲区溢出
```

新的处理：

```text
uart2_line_invalid = 1
uart2_rx_index = 0
→ 当前整行作废
→ 后续字节一直丢弃到 '\n'
```

---

## 十二、为什么溢出后不能只截断

旧方案可能：

```text
收到 100 字节消息
→ buffer 只能保存前 63 个
→ 后面的字符忽略
→ 收到换行
→ 将前 63 字符当成完整命令
```

这样就把：

```text
被截断的消息
```

错误解释为：

```text
完整消息
```

这是危险的。

新原则：

```text
消息一旦发生溢出
→ 完整性已经无法保证
→ 整行作废
→ 不解析
→ 不执行
```

---

## 十三、为什么不能只忽略非法字节

假设收到：

```text
0xB5 + led_on + \n
```

错误做法：

```text
忽略 0xB5
→ 剩下 led_on
→ 看起来变成合法命令
→ 执行 LED
```

这意味着接收端主动：

```text
修复了损坏命令
```

但接收端无法知道原始发送方真正想发送的是什么。

安全做法：

```text
检测到 0xB5
→ 整行 invalid
→ led_on 也丢弃
→ 不执行 LED
```

在控制系统里：

```text
拒绝不可信命令
```

通常比：

```text
猜测并执行被损坏的命令
```

更安全。

---

## 十四、回调完整判断顺序

```text
收到 byte
│
├─ '\r'
│  → 忽略
│
├─ '\n'
│  │
│  ├─ 当前行 invalid
│  │  → 清 index
│  │  → 清 invalid
│  │  → 不产生 line_ready
│  │
│  ├─ 当前行有效且非空
│  │  → 添加 '\0'
│  │  → line_ready = 1
│  │
│  └─ 空行
│     → 忽略
│
└─ 普通字节
   │
   ├─ 当前行已经 invalid
   │  → 丢弃
   │
   ├─ 非可打印 ASCII
   │  → invalid = 1
   │  → index = 0
   │
   ├─ buffer 有空间
   │  → 保存字节
   │  → index++
   │
   └─ buffer 已满
      → invalid = 1
      → index = 0
```

---

## 十五、为什么回调最后必须继续 Receive_IT

每次：

```text
HAL_UART_RxCpltCallback()
```

处理完一个字节后，仍然执行：

```c
HAL_UART_Receive_IT(
    huart,
    &uart2_rx_byte,
    1U
);
```

原因：

```text
HAL 单字节中断接收
每完成一次后
需要重新预约下一次接收
```

否则接收链会停止。

---

## 十六、回调与主循环职责

USART2 中断回调只负责：

```text
接收单字节
判断行边界
检查字符合法性
维护缓冲区
维护 invalid 状态
形成 line_ready
重新启动下一字节接收
```

不负责：

```text
strcmp 命令解析
LED 控制
复杂日志
长时间等待
```

业务执行仍在：

```text
main loop
```

完成。

---

## 十七、与 Gateway Day 58 的异常闭环

当 STM32 收到受污染命令：

```text
非法字节
→ 整行 invalid
→ 不执行
→ 不发送 success ACK
```

Gateway：

```text
合法 MQTT command
→ 已经成功写入串口
→ pending_command 等待
→ STM32 没有返回匹配 ACK
→ 超过 ACK timeout
→ 清空 pending
→ 发布 timeout
```

因此形成：

```text
STM32
→ 协议层安全拒绝损坏命令

Linux Gateway
→ 事务层通过 timeout 结束等待
```

这是合理的异常闭环。

---

## 十八、为什么 STM32 不应该伪造 failed ACK

对于：

```text
损坏到无法确认原始命令内容的整行
```

STM32 不一定知道：

```text
这原本究竟是哪条命令
```

因此直接构造：

```text
ack:led_on:failed
```

可能同样是不可信的。

当前选择：

```text
损坏行
→ 静默丢弃
```

让 Gateway 通过：

```text
timeout
```

结束无法确认的事务。

---

## 十九、Day 11 完成内容

```text
✓ 非法字节检测
✓ uart2_line_invalid 状态
✓ 损坏行持续丢弃到 '\n'
✓ 非法字节后不尝试恢复当前命令
✓ 软件缓冲区溢出整行作废
✓ 超长命令不会被截断后执行
✓ 空行忽略
✓ 合法行正常形成 C 字符串
✓ HAL_UART_Receive_IT 接收链保持
✓ 固件编译通过
✓ 固件烧录
✓ 与 Gateway ACK timeout 路径配合验证
✓ DHT11 Telemetry 不受影响
```

---

## 二十、Day 11 尚未处理

Day 11 解决的是：

```text
字节已经成功进入 Rx callback
之后如何判断这一行是否可信
```

尚未解决：

```text
PE
NE
FE
ORE
```

等 UART 硬件错误。

还没有实现：

```text
HAL_UART_ErrorCallback()
```

以及：

```text
ORE 后重新建立 HAL_UART_Receive_IT()
```

这些进入 Day 12。

---

## 二十一、Day 11 与 Day 12 的职责边界

### Day 11

```text
协议层
```

关注：

```text
已经收到的数据内容是否可信
```

例如：

```text
非法字节
软件 buffer 溢出
损坏行
空行
```

### Day 12

```text
UART / HAL 硬件错误恢复层
```

关注：

```text
UART 硬件本身发生错误以后
接收任务是否还能继续
```

例如：

```text
ORE
FE
NE
PE
```

---

## 二十二、技术面复述

### 1. 为什么出现一个非法字节后要丢弃整行？

因为接收端无法确定：

```text
剩余字符
是否仍属于原始完整消息
```

不能擅自修复损坏命令。

### 2. 为什么软件缓冲区溢出后也要整行丢弃？

因为：

```text
消息已经被截断
```

不能把：

```text
部分消息
```

当成完整命令执行。

### 3. 为什么要一直丢弃到 \n？

因为当前协议是：

```text
行协议
```

只有：

```text
\n
```

才能明确表示当前损坏消息已经结束。

### 4. 为什么空行不执行命令？

空行没有业务语义，只是协议边界。

### 5. 为什么损坏命令宁可 timeout 也不尝试修复？

因为控制系统中：

```text
错误执行
```

通常比：

```text
拒绝执行
```

风险更高。

---

## 二十三、Day 11 结论

Day 11 将 USART2 接收从：

```text
只要不是 \r 或 \n
→ 全部写进命令缓冲区
```

升级为：

```text
合法字符
→ 正常组装

非法字节
→ 整行作废

软件 buffer 溢出
→ 整行作废

损坏状态
→ 一直保持到 '\n'

合法下一行
→ 自动恢复
```

因此：

```text
受污染命令不会被修复后执行
超长命令不会被截断后执行
坏行结束后下一条命令仍能正常接收
```

下一步进入：

```text
STM32 V2 Day 12
→ HAL_UART_ErrorCallback()
→ PE / NE / FE / ORE
→ UART 接收链恢复
```
