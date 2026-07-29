---
title: STM32 环境感知与执行控制终端 V2 Day 9 USART2 中断式命令行接收
project: STM32 环境感知与执行控制终端
system_layer: 设备层 / 终端节点
document_type: hardware_validation
status: verified
last_updated: 2026-07-19
tags: [STM32F407VET6, USART2, Interrupt, UART, Buffer, NonBlocking, LineProtocol]
---

# STM32 环境感知与执行控制终端 V2 Day 9 USART2 中断式命令行接收

## 今日目标

建立 USART2 非阻塞逐字节接收基础：

```text
串口接收字节
→ USART2 中断
→ HAL 接收完成回调
→ 拼接完整命令行
→ 主循环处理字符串
```

为后续链路准备：

```text
MQTT Command
→ Linux 网关
→ USB-TTL
→ STM32 USART2
→ 命令解析
→ LED 执行
→ ACK
```

Day 9 只完成：

```text
可靠接收一整行字符串
```

暂时不执行 LED 命令。

## USART2 中断配置

CubeMX 中启用：

```text
USART2 Global Interrupt
```

生成 NVIC 配置：

```c
HAL_NVIC_SetPriority(USART2_IRQn, 0, 0);
HAL_NVIC_EnableIRQ(USART2_IRQn);
```

中断入口：

```c
void USART2_IRQHandler(void)
{
    HAL_UART_IRQHandler(&huart2);
}
```

## 完整中断链路

```text
PA3 收到串行数据
→ USART2 数据寄存器收到字节
→ RXNE 等硬件状态置位
→ NVIC 触发 USART2 中断
→ USART2_IRQHandler()
→ HAL_UART_IRQHandler()
→ HAL 将数据写入指定地址
→ HAL_UART_RxCpltCallback()
```

## 首次启动接收

初始化完成后，需要主动启动第一次中断接收：

```c
if (
    HAL_UART_Receive_IT(
        &huart2,
        &uart2_rx_byte,
        1U
    ) != HAL_OK
)
{
    Error_Handler();
}
```

这不是阻塞等待字符，而是向 HAL 预约：

```text
使用 USART2
→ 接收接下来的 1 个字节
→ 保存到 uart2_rx_byte
→ 使用中断方式
```

函数成功启动接收后立即返回，主循环继续运行。

## UART 句柄与回调参数

回调参数：

```c
UART_HandleTypeDef *huart
```

表示：

```text
指向 UART 句柄结构体的指针
```

判断：

```c
if (huart->Instance == USART2)
```

表示：

```text
当前接收完成事件是否来自 USART2
```

同一个 HAL 回调以后可能同时服务：

```text
USART1
USART2
其他 UART
```

因此必须通过 `Instance` 区分来源。

## 接收状态变量

```c
#define UART2_RX_BUFFER_SIZE 64U
```

当前接收一个字节：

```c
static uint8_t uart2_rx_byte = 0U;
```

完整行缓冲区：

```c
static char uart2_rx_buffer[
    UART2_RX_BUFFER_SIZE
];
```

当前写入位置：

```c
static volatile uint16_t uart2_rx_index = 0U;
```

完整行标志：

```c
static volatile uint8_t uart2_line_ready = 0U;
```

## 各变量职责

### uart2_rx_byte

```text
保存当前通过中断收到的单个字节
```

每完成一次接收，这个变量只保存一个新字符。

### uart2_rx_buffer

```text
把多个字节依次拼成一整行 C 字符串
```

例如：

```text
'l' 'e' 'd' '_' 'o' 'n' '\0'
```

### uart2_rx_index

```text
记录下一个普通字符应该写入缓冲区的下标
```

### uart2_line_ready

```text
0
→ 中断可以继续向当前缓冲区写入

1
→ 一整行已经形成，等待主循环处理
```

## volatile 的作用

`uart2_rx_index` 和 `uart2_line_ready` 会同时被：

```text
中断回调
主循环
```

访问，因此声明为：

```c
volatile
```

它告诉编译器：

```text
该变量可能在当前代码流程之外被修改
每次使用时应重新读取其值
```

`volatile` 不等于线程安全，也不能自动解决所有并发问题。

## 行协议规则

当前协议约定：

```text
普通字符
→ 写入缓冲区

\r
→ 忽略

\n
→ 一行结束
```

例如收到：

```text
led_on\r\n
```

缓冲区依次得到：

```text
'l' 'e' 'd' '_' 'o' 'n'
```

收到 `\n` 后补充：

```c
uart2_rx_buffer[uart2_rx_index] = '\0';
```

最终形成：

```c
"led_on"
```

## \r、\n 和 \0

```text
\r
→ 回车符
→ 当前协议中忽略

\n
→ 换行符
→ 表示一条命令结束

\0
→ C 字符串终止符
→ 不来自用户的可见输入
→ 由 STM32 程序主动补充
```

没有 `\0`，`printf("%s")` 和 `strcmp()` 等字符串函数无法可靠判断字符串结束位置。

## 中断回调职责

中断回调只做轻量工作：

```text
判断 UART 来源
→ 检查当前字节
→ 普通字符写入缓冲区
→ 遇到换行补 \0
→ 设置 line_ready
→ 重新预约下一个字节
```

不在中断中执行：

```text
printf
strcmp
LED 控制
复杂协议解析
耗时业务逻辑
```

原因：

- 中断应尽快退出；
- 避免阻塞其他中断；
- 减少系统实时性问题；
- 业务逻辑更容易测试；
- 降低共享状态复杂度。

## 为什么必须重新调用 HAL_UART_Receive_IT()

一次调用：

```c
HAL_UART_Receive_IT(..., 1U)
```

只预约接收：

```text
一个字节
```

接收完成后，HAL 不会自动永久接收后续所有字节。

因此回调末尾需要再次执行：

```c
HAL_UART_Receive_IT(
    huart,
    &uart2_rx_byte,
    1U
);
```

流程是：

```text
预约一个字节
→ 收到一个字节
→ 进入回调
→ 处理该字节
→ 再预约一个字节
```

这样才能形成连续接收链。

重新接收逻辑不能只放在某个普通字符分支中，否则遇到换行或其他情况后，接收链可能停止。

## 缓冲区越界保护

缓冲区大小：

```text
64 字节
```

需要给字符串终止符保留一个位置，因此最多保存：

```text
63 个普通字符
```

写入前必须保证：

```c
uart2_rx_index < UART2_RX_BUFFER_SIZE - 1U
```

超出的字符被忽略，避免：

- 数组越界；
- 覆盖其他内存；
- 程序异常；
- 后续字符串不可控。

## 主循环处理

主循环检查：

```c
if (uart2_line_ready == 1U)
```

处理完整字符串：

```c
printf(
    "rx:%s\r\n",
    uart2_rx_buffer
);
```

处理完成后：

```c
uart2_rx_index = 0U;
uart2_line_ready = 0U;
```

顺序含义：

```text
先处理完整字符串
→ 将下一次写入位置恢复到 0
→ 最后清除 ready 标志
→ 将缓冲区使用权交回中断
```

## 为什么数组不需要整体清零

下一行从：

```text
下标 0
```

开始覆盖旧内容，并在新行结束时重新写入：

```text
\0
```

因此旧字符串后面的残留字符不会被新的标准 C 字符串访问。

每次整体清零会增加不必要的处理时间。

## 实际验收

普通输入：

```text
hello
led_on
test123
```

输出：

```text
rx:hello
rx:led_on
rx:test123
```

超长输入：

```text
最多保存 63 个字符
多余字符被忽略
没有发生数组越界
```

恢复测试：

```text
发送超长行
→ 再发送 hello
→ 仍能输出 rx:hello
```

并行运行：

```text
USART2 中断接收正常
DHT11 每约 2 秒采集正常
主循环没有被串口等待阻塞
```

## 当前单缓冲区限制

当前只有一个行缓冲区。

当：

```text
uart2_line_ready = 1
```

且主循环尚未处理旧命令时，新收到的普通字符会被暂时丢弃。

对当前场景：

```text
低频
短命令
一次只发送一条
```

已经足够。

后续高频命令可以升级为：

```text
双缓冲区
或
环形缓冲区
```

目前不提前增加复杂度。

## Day 9 验收结果

```text
✓ USART2 TX/RX 正常
✓ USART2 全局中断已启用
✓ 单字节中断接收正常
✓ HAL 接收回调正常
✓ \r\n 行协议正常
✓ C 字符串终止正常
✓ 缓冲区越界保护正常
✓ 超长输入后可以恢复
✓ DHT11 并行运行正常
✓ 主循环未被串口接收阻塞
```

## 当前完整数据流

```text
Linux 串口发送 led_on\r\n
→ STM32 PA3 接收字节
→ USART2 中断
→ HAL_UART_IRQHandler()
→ HAL_UART_RxCpltCallback()
→ 普通字符写入缓冲区
→ \n 表示命令完成
→ 补充 \0
→ uart2_line_ready = 1
→ 主循环打印完整命令
```

## 当前边界

已完成：

```text
逐字节接收
→ 完整命令行拼接
→ 主循环读取字符串
```

尚未完成：

```text
命令解析
LED 执行
GPIO 状态检查
设备 ACK
Linux MQTT ACK
```

## 面试表达

我使用 `HAL_UART_Receive_IT()` 实现 USART2 单字节中断接收。

程序首次启动时预约一个字节，硬件收到数据后进入 `USART2_IRQHandler()`，再由 HAL 调用接收完成回调。回调只负责保存普通字符、识别 CRLF、设置完整行标志并重新预约下一字节。

完整命令在主循环中处理，避免在中断中进行字符串比较、打印和硬件控制。

我使用固定长度行缓冲区，并为 `\0` 保留位置，限制最多保存 63 个字符，防止缓冲区越界。当前是单缓冲区设计，适合低频短命令，后续高频场景可升级为双缓冲区或环形缓冲区。

## 下一步

```text
完整字符串
→ strcmp() 命令解析
→ led_on / led_off
→ PA1 板载 LED 控制
→ GPIO 读回验证
→ 返回串口 ACK
```
