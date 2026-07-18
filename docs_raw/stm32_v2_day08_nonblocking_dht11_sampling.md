---
title: STM32F407VET6 V2 Day 8 DHT11 非阻塞周期采集与 USART2 持续输出
project: STM32 环境感知与执行控制终端
system_layer: 设备层 / 终端节点
document_type: hardware_validation
status: verified
last_updated: 2026-07-18
tags: [STM32F407VET6, DHT11, HAL_GetTick, NonBlocking, USART2, Scheduling]
---

# STM32F407VET6 V2 Day 8 DHT11 非阻塞周期采集与 USART2 持续输出

## 今日目标

将 DHT11 从阻塞式延时采集改成基于 `HAL_GetTick()` 的非阻塞周期采集。

实现：

```text
主循环持续运行
→ 每约 2 秒触发一次 DHT11 读取
→ 读取成功后输出温度
→ 其余时间主循环可以继续执行其他任务
```

## 原有阻塞方式的问题

原来可能使用：

```c
HAL_Delay(1000);
```

控制 DHT11 的读取周期。

`HAL_Delay()` 会阻塞当前执行流程。

阻塞期间，主循环无法继续及时处理：

- 按键事件；
- LED 控制；
- OLED 刷新；
- 串口命令；
- 报警逻辑；
- 后续其他传感器任务。

随着系统功能增加，长时间阻塞会降低系统响应能力。

## 非阻塞调度变量

定义上一次采集时间：

```c
uint32_t last_dht11_sample_time = 0;
```

定义采集周期：

```c
#define DHT11_SAMPLE_PERIOD_MS 2000U
```

含义：

```text
last_dht11_sample_time
→ 上一次执行 DHT11 采集时的系统毫秒时间

DHT11_SAMPLE_PERIOD_MS
→ 两次采集之间需要等待的时间
```

## HAL_GetTick()

`HAL_GetTick()` 返回 STM32 从启动到当前经过的毫秒数。

例如：

```text
启动时：0
1 秒后：1000
2 秒后：2000
```

当前时间：

```c
uint32_t now = HAL_GetTick();
```

判断距离上一次采集是否已经达到周期：

```c
if (
    now - last_dht11_sample_time
    >= DHT11_SAMPLE_PERIOD_MS
)
{
    ...
}
```

## 为什么使用时间差

判断方式：

```text
当前时间 - 上次执行时间 >= 采集周期
```

而不是让程序停在原地等待 2 秒。

主循环会持续运行，只在时间条件满足时执行一次 DHT11 采集。

这是一种简单的非阻塞周期调度方式。

## 当前采集流程

主循环中的逻辑：

```text
读取当前 Tick
→ 判断是否达到 2 秒周期
→ 未达到：继续运行主循环
→ 已达到：更新时间戳
→ 调用 DHT11_ReadData()
→ 校验成功后解析温度
→ USART2 输出温度
```

伪代码：

```c
uint32_t now = HAL_GetTick();

if (
    now - last_dht11_sample_time
    >= DHT11_SAMPLE_PERIOD_MS
)
{
    last_dht11_sample_time = now;

    if (DHT11_ReadData(data))
    {
        printf("temperature:%.1f\r\n", temperature);
    }
}
```

## 为什么及时更新时间戳

达到采集周期后，需要更新：

```c
last_dht11_sample_time = now;
```

否则时间条件会在之后的每一轮循环中持续成立：

```text
now - old_time 始终大于 2000
→ 每轮循环都读取 DHT11
→ 失去周期控制
```

更新时间戳后，下一次采集需要重新等待约 2 秒。

## DHT11 采集周期

当前设置：

```text
2 秒
```

DHT11 本身不适合进行非常高频的读取。

设置合理采集周期可以：

- 避免重复读取过快；
- 减少无意义的数据；
- 给其他模块留出执行时间；
- 为 Linux 网关提供稳定的周期数据流。

## 读取成功才输出

只有当：

```c
DHT11_ReadData(data)
```

返回成功时，才解析和发送温度。

流程：

```text
读取成功
→ 校验通过
→ 解析温度
→ USART2 输出

读取失败
→ 不发送错误数据
→ 等待下一次采集周期
```

这样可以保证网关收到的内容来自通过校验的有效传感器数据。

## USART2 输出格式

输出格式继续与 Linux 网关保持一致：

```text
temperature:26.0
```

完整串口数据：

```text
temperature:26.0\r\n
```

其中：

```text
temperature
→ 字段名称

26.0
→ 浮点温度值

\r\n
→ 一行数据结束
```

Linux 网关可以使用按行读取的方式接收。

## 实际验证

实际串口可以持续看到类似输出：

```text
temperature:26.0
temperature:26.0
temperature:26.0
```

相邻数据之间约间隔 2 秒。

验证结果：

```text
✓ DHT11 能够周期读取
✓ 不再使用 HAL_Delay(1000)
✓ 主循环不会被秒级延时阻塞
✓ 读取成功后持续输出温度
✓ 串口格式保持稳定
✓ 输出周期可以供 Linux 网关持续读取
```

## Day 7 与 Day 8 的区别

Day 7 重点：

```text
能否完成一次完整 DHT11 数据读取
```

包括：

- 40 bit 读取；
- 字节组装；
- 校验和；
- 温度解析；
- 单次串口输出。

Day 8 重点：

```text
如何把一次读取变成可长期运行的周期任务
```

包括：

- `HAL_GetTick()`；
- 上次采集时间；
- 采集周期；
- 非阻塞调度；
- 持续串口输出。

## 完整数据流

```text
HAL_GetTick()
→ 判断采集周期
→ DHT11_ReadData()
→ 40 bit 数据
→ 校验和验证
→ 温度解析
→ USART2 输出
→ Linux 网关持续读取
→ MQTT Telemetry
```

## 非阻塞的含义

当前所谓非阻塞，主要是指：

```text
不再使用秒级 HAL_Delay() 等待下一次采集
```

但 DHT11 单次通信内部仍然包含：

- 微秒级等待；
- GPIO 电平轮询；
- 超时判断。

因此它还不是完整的异步状态机驱动。

更准确的描述是：

```text
采集周期调度非阻塞
DHT11 单次时序读取仍然是同步执行
```

## 当前边界

Day 8 尚未完成：

- DHT11 完全异步状态机；
- 温度和湿度同时输出；
- 传感器连续失败计数；
- 失败状态上报；
- 正式串口帧协议；
- 串口接收 Linux 控制命令；
- 多传感器统一调度；
- FreeRTOS 任务化。

## 面试时怎么讲

我使用 `HAL_GetTick()` 将 DHT11 的采集周期从阻塞式延时改成了非阻塞调度。

程序保存上一次采集时间，并使用当前 Tick 与上次时间的差值判断是否达到 2 秒周期。

未达到周期时，主循环继续执行其他逻辑；达到周期后更新采集时间，调用 DHT11 驱动，并且只在读取和校验成功时通过 USART2 输出温度。

这样删除了秒级 `HAL_Delay()`，提高了主循环对按键、显示、控制命令和其他模块的响应能力。

当前属于采集周期非阻塞，DHT11 单次微秒时序读取仍然是同步执行，后续可以进一步重构为状态机。

## 后续计划

- 与 Linux 网关进行真实串口持续联调；
- 确认 Linux 串口设备名；
- 将网关波特率调整为 115200；
- 验证持续读取 `temperature:<value>`；
- 增加湿度字段；
- 增加 DHT11 读取失败统计；
- 后续设计多字段串口协议。
