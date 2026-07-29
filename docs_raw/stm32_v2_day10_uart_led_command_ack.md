---
title: STM32 环境感知与执行控制终端 V2 Day 10 UART LED 命令执行与真实 ACK
project: STM32 环境感知与执行控制终端
system_layer: 设备层 / 终端节点
document_type: hardware_validation
status: verified
last_updated: 2026-07-20
tags: [STM32F407VET6, USART2, MQTT, Command, LED, GPIO, ACK, HardwareVerification]
---

# STM32 环境感知与执行控制终端 V2 Day 10 UART LED 命令执行与真实 ACK

## 今日目标

在 Day 9 已完成 USART2 中断式行接收的基础上，实现真实下行控制：

```text
MQTT Command
→ Linux 物联网边缘网关
→ USB-TTL
→ STM32 USART2
→ 命令解析
→ 板载 LED 执行
→ GPIO 状态检查
→ STM32 返回执行 ACK
```

今天不再只停留在：

```text
收到字符串并打印
```

而是完成：

```text
接收命令
→ 解析命令
→ 执行硬件动作
→ 检查 GPIO 状态
→ 返回执行结果
```

## 当前双向链路

此前完成上行遥测：

```text
DHT11
→ STM32 采集与校验
→ temperature:<value>
→ Linux 网关
→ MQTT Telemetry
```

本日补齐设备侧下行执行：

```text
MQTT Command
→ Linux 网关
→ USART2
→ STM32
→ LED 动作
→ 串口 ACK 返回 Linux
```

当前已经初步形成：

```text
STM32 → Linux
→ 温度遥测

Linux → STM32
→ LED 控制

STM32 → Linux
→ 设备执行结果
```

## 真实联调准备

继续使用 CH340 USB-TTL。

联调原则：

```text
BUSID 不能写死
/dev/ttyUSB* 不能写死
Windows COM 编号不能写死
```

标准流程：

```text
Windows 管理员 PowerShell
→ usbipd list
→ 确认实际 BUSID
→ 必要时 bind / attach

WSL
→ 检查实际 /dev/ttyUSB*
→ 检查驱动和权限
→ 激活网关 .venv
→ 确认没有 miniterm 占用串口
```

设备重新插拔或枚举后，编号可能改变，必须以实际查询结果为准。

## 完整命令字符串

Day 9 已经将串口字节拼接为标准 C 字符串：

```c
"led_on"
"led_off"
```

主循环可以安全使用：

```c
strcmp()
```

进行命令比较。

## strcmp()

判断：

```c
strcmp(
    uart2_rx_buffer,
    "led_on"
) == 0
```

含义：

```text
两个字符串完全相同
```

必须记住：

```text
strcmp() 返回 0
→ 字符串相等
```

不是返回 `1` 才表示相等。

## 命令分支

使用互斥结构：

```c
if (...)
{
    /* led_on */
}
else if (...)
{
    /* led_off */
}
else
{
    /* unsupported */
}
```

这样一条命令只会进入一个处理分支。

## 中断层与业务层职责

USART2 中断继续只负责：

```text
接收一个字节
→ 保存到行缓冲区
→ 识别 \r 与 \n
→ 一行完成后设置 line_ready
→ 重新预约下一个字节
```

不在中断回调中执行：

```text
strcmp()
LED 控制
printf ACK
复杂命令处理
```

主循环负责：

```text
读取完整字符串
→ 判断命令
→ 执行硬件动作
→ 判断执行结果
→ 返回 ACK
```

这样可以让中断快速退出，避免影响其他中断和周期任务。

## 板载 LED 有效电平

当前板载 D2：

```text
GPIO：PA1
低电平：点亮
高电平：熄灭
```

Board 层使用：

```c
BOARD_LED_ACTIVE_LEVEL
BOARD_LED_INACTIVE_LEVEL
```

业务层不直接硬编码：

```c
GPIO_PIN_RESET
GPIO_PIN_SET
```

而是使用：

```c
Board_LED_SetAndVerify(
    BOARD_LED_ACTIVE_LEVEL
);

Board_LED_SetAndVerify(
    BOARD_LED_INACTIVE_LEVEL
);
```

这样更换开发板或 LED 有效电平时，只需要修改 Board 配置。

## Board_LED_SetAndVerify()

接口：

```c
static uint8_t Board_LED_SetAndVerify(
    GPIO_PinState target_level
);
```

职责：

```text
接收目标电平
→ 写入 PA1
→ 读取 PA1 当前电平
→ 与目标值比较
→ 返回成功或失败
```

概念实现：

```c
static uint8_t Board_LED_SetAndVerify(
    GPIO_PinState target_level
)
{
    HAL_GPIO_WritePin(
        BOARD_LED_GPIO_PORT,
        BOARD_LED_GPIO_PIN,
        target_level
    );

    if (
        HAL_GPIO_ReadPin(
            BOARD_LED_GPIO_PORT,
            BOARD_LED_GPIO_PIN
        ) == target_level
    )
    {
        return 1U;
    }

    return 0U;
}
```

返回值：

```text
1U
→ GPIO 读回电平与目标电平一致

0U
→ GPIO 读回电平与目标电平不一致
```

该函数只负责：

```text
执行
+
检查
```

不负责决定或打印 ACK。

ACK 仍由主循环业务逻辑决定。

## ACK 串口协议

统一格式：

```text
ack:<command>:<status>
```

成功：

```text
ack:led_on:success
ack:led_off:success
```

失败：

```text
ack:led_on:failed
ack:led_off:failed
ack:hello:failed
```

所有 ACK 必须以：

```text
\r\n
```

结尾。

例如：

```c
printf(
    "ack:led_on:success\r\n"
);
```

## 为什么 ACK 必须带换行

Linux 网关按行读取串口数据。

如果 ACK 没有换行，可能与后续 DHT11 日志粘连：

```text
ack:led_on:successDHT11 raw: ...
```

这样 Linux 无法把 ACK 当成独立协议帧解析。

因此：

```text
\r\n
→ 串口帧结束标志
```

## 主循环命令处理流程

```text
uart2_line_ready == 1
→ 读取完整命令
→ 输出 rx:<command>

→ 如果 led_on
    → 写入 LED 有效电平
    → GPIO 读回
    → success 或 failed ACK

→ 否则如果 led_off
    → 写入 LED 无效电平
    → GPIO 读回
    → success 或 failed ACK

→ 否则
    → 不改变 LED
    → 返回 failed ACK

→ uart2_rx_index 清零
→ uart2_line_ready 最后清零
```

概念代码：

```c
if (uart2_line_ready == 1U)
{
    printf(
        "rx:%s\r\n",
        uart2_rx_buffer
    );

    if (
        strcmp(
            uart2_rx_buffer,
            "led_on"
        ) == 0
    )
    {
        if (
            Board_LED_SetAndVerify(
                BOARD_LED_ACTIVE_LEVEL
            ) == 1U
        )
        {
            printf(
                "ack:led_on:success\r\n"
            );
        }
        else
        {
            printf(
                "ack:led_on:failed\r\n"
            );
        }
    }
    else if (
        strcmp(
            uart2_rx_buffer,
            "led_off"
        ) == 0
    )
    {
        if (
            Board_LED_SetAndVerify(
                BOARD_LED_INACTIVE_LEVEL
            ) == 1U
        )
        {
            printf(
                "ack:led_off:success\r\n"
            );
        }
        else
        {
            printf(
                "ack:led_off:failed\r\n"
            );
        }
    }
    else
    {
        printf(
            "ack:%s:failed\r\n",
            uart2_rx_buffer
        );
    }

    uart2_rx_index = 0U;
    uart2_line_ready = 0U;
}
```

## 真实 led_on 验证

MQTT 发布：

```json
{
  "command": "led_on"
}
```

链路结果：

```text
mqtt command received
command: led_on
command forwarded to serial: led_on
stm32 debug: rx:led_on
stm32 debug: ack:led_on:success
```

真实硬件现象：

```text
板载 LED 点亮
```

证明：

```text
MQTT 消息到达网关
→ 网关串口转发成功
→ STM32 收到完整命令
→ STM32 完成命令解析
→ PA1 被设置为有效电平
→ GPIO 读回正确
→ STM32 返回成功 ACK
```

## 真实 led_off 验证

MQTT 发布：

```json
{
  "command": "led_off"
}
```

结果：

```text
mqtt command received
command: led_off
command forwarded to serial: led_off
stm32 debug: rx:led_off
stm32 debug: ack:led_off:success
```

真实硬件现象：

```text
板载 LED 熄灭
```

## 非法命令验证

Linux 网关当前只允许：

```text
led_on
led_off
```

因此 `hello` 无法通过 MQTT 网关下发 STM32。

为了测试 STM32 自身的非法命令分支，需要停止网关后使用：

```bash
python -m serial.tools.miniterm \
  /dev/ttyUSB实际编号 \
  115200 \
  --eol CRLF \
  --echo
```

发送：

```text
hello
```

STM32 返回：

```text
rx:hello
ack:hello:failed
```

同时确认：

```text
LED 状态未改变
DHT11 仍继续周期采集
后续合法命令仍能正常接收
```

测试完成后：

```text
Ctrl+]
```

退出 miniterm，避免与网关同时占用串口。

## 四种“成功”必须区分

### Linux 串口写入成功

```text
ser.write() 返回完整字节数
```

只能证明：

```text
Linux 已将字节交给串口驱动或发送缓冲区
```

不能证明 STM32 已经收到。

### STM32 接收成功

```text
rx:led_on
```

证明：

```text
STM32 已经收到并拼接出完整命令
```

还不能证明 LED 已经执行。

### STM32 GPIO 执行成功

```text
ack:led_on:success
```

当前证明：

```text
STM32 已解析命令
并且 PA1 读回电平与目标电平一致
```

### 真实物理执行器成功

肉眼确认：

```text
led_on
→ LED 真实点亮

led_off
→ LED 真实熄灭
```

GPIO 读回不能百分之百证明 LED 本体发光。

仍可能存在：

- LED 损坏；
- 电阻断路；
- 焊点异常；
- 执行器机械部分失效。

以后控制电机、风扇等设备时，需要：

```text
反馈引脚
电流检测
转速传感器
位置传感器
```

才能形成更完整的物理闭环。

## 当前 ACK 阶段

STM32 已经能够产生设备侧真实 ACK：

```text
ack:led_on:success
ack:led_off:success
ack:hello:failed
```

Linux 网关当前能够收到这些串口行，但仍将其作为普通 STM32 输出或 Debug 处理。

网关尚未完成：

```text
识别 ACK
→ 解析 command 和 status
→ 匹配等待中的命令
→ 判断超时
→ 发布正式 MQTT ACK
```

所以当前完成的是：

```text
设备端执行 ACK
```

尚未完成：

```text
网关端真实 MQTT ACK 闭环
```

## 并行运行结果

联调期间，DHT11 仍持续输出：

```text
DHT11 raw: ...
temperature:...
```

以下功能可以并行运行：

```text
USART2 中断接收
主循环命令解析
LED 动作执行
串口 ACK 发送
DHT11 每约 2 秒采集
MQTT 上行遥测
```

没有因为等待串口命令而阻塞主循环。

## 当前限制

1. ACK 中没有请求 ID，连续或重复命令不容易精确关联；
2. Linux 网关尚未正式解析 ACK；
3. 单缓冲区在主循环未处理上一行时可能丢弃新字符；
4. GPIO 读回不是独立物理反馈；
5. 尚未处理 USART 溢出、帧错误和中断异常恢复；
6. DHT11、UART 命令和按键逻辑仍集中在 `main.c`；
7. 尚未处理重复命令、乱序 ACK 和超时。

## Git 提交

```text
commit: fd57bce
message: feat: execute UART LED commands with verified ACK
branch: v2-f407-core-board
working tree: clean
```

## Day 10 验收结果

```text
✓ USART2 真实下行通过
✓ 完整命令接收通过
✓ strcmp() 命令解析通过
✓ led_on 真实点亮
✓ led_off 真实熄灭
✓ GPIO 读回验证通过
✓ 成功 ACK 返回 Linux
✓ 非法命令失败 ACK 通过
✓ DHT11 并行采集正常
✓ MQTT 到设备动作链路通过
✓ Git 提交和推送完成
```

## 当前完整链路

```text
MQTT Command
→ Linux 网关
→ USB-TTL
→ STM32 USART2
→ 中断接收
→ 完整字符串
→ strcmp() 解析
→ PA1 LED 动作
→ GPIO 读回
→ 串口 ACK
→ Linux 收到 ACK
```

## 当前边界

设备侧已经完成：

```text
接收
→ 解析
→ 执行
→ GPIO 检查
→ ACK
```

网关侧仍需完成：

```text
接收 ACK
→ 分类
→ 解析
→ 命令关联
→ 发布 MQTT ACK
→ 超时处理
```

## 面试表达

我在 USART2 中断行接收基础上，将完整命令交给主循环处理。

主循环通过 `strcmp()` 识别 `led_on` 和 `led_off`，使用 Board 层的有效电平宏控制 PA1，随后通过 `HAL_GPIO_ReadPin()` 检查引脚电平是否与目标一致，并根据结果返回 `success` 或 `failed` ACK。

我没有把复杂字符串处理和 GPIO 控制放入 UART 中断回调，而是让中断只负责快速收字节、拼接命令和设置标志，保证 DHT11 周期采集等其他功能继续运行。

当前 STM32 已经能返回真实设备 ACK，但 Linux 网关还没有把 ACK 与等待命令关联并发布 MQTT ACK，这是下一阶段的核心任务。

## 下一步

```text
Linux 网关收到串口 ACK
→ 区分 Telemetry / Debug / ACK
→ 解析 command 和 status
→ 与等待中的合法命令关联
→ 发布 MQTT success / failed
→ 增加无响应与超时处理
```
