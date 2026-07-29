---
title: Linux-STM32 物联网边缘网关 Day 56 MQTT 命令串口下发 STM32
project: Linux-STM32 物联网边缘网关
system_layer: 通信层 / 数据中枢
document_type: software_module_record
status: software_verified
last_updated: 2026-07-20
tags: [Linux, Python, MQTT, PySerial, USART2, Command, Userdata, Timeout, ACK]
---

# Linux-STM32 物联网边缘网关 Day 56 MQTT 命令串口下发 STM32

## 今日目标

完成下行链路的前半段：

```text
MQTT Command
→ Linux 网关接收与解析
→ 命令合法性检查
→ 编码为串口字节帧
→ USB-TTL TXD
→ STM32 PA3 / USART2_RX
→ STM32 中断接收完整命令行
```

## 今日结果

真实验证：

```text
led_on
→ STM32 输出 rx:led_on

led_off
→ STM32 输出 rx:led_off
```

因此已经证明：

```text
MQTT
→ Linux
→ STM32
```

命令传输链路已经跑通。

Day 56 尚未完成：

```text
STM32 解析命令
→ 控制真实 LED
→ 返回真实执行 ACK
→ Linux 发布 MQTT success ACK
```

## 串口联调准备

本次设备重新枚举后，出现了新的：

```text
BUSID
Windows COM 编号
Linux ttyUSB 编号
```

再次证明：

```text
BUSID 不能写死
COM 编号不能写死
/dev/ttyUSB* 不能写死
```

设备处于 `Not shared` 时，需要重新执行：

```text
bind
→ attach
```

管理员 PowerShell：

```powershell
usbipd list
usbipd bind --busid <实际BUSID> --force
usbipd attach --wsl --busid <实际BUSID>
usbipd list
```

## send_command_to_serial()

在 `command_handler.py` 中增加：

```python
send_command_to_serial(ser, command)
```

职责：

```text
接收已经打开的 PySerial 对象
→ 检查对象和命令是否合法
→ 构造串口协议帧
→ 编码为 bytes
→ 写入串口
→ 检查实际写入字节数
→ 返回 True 或 False
```

输入：

```text
ser
→ 已经打开的 PySerial 串口对象

command
→ 解析后的命令字符串
→ 例如 led_on、led_off
```

输出：

```text
True
→ Linux 完整写入串口字节帧

False
→ 参数、状态、命令或写入过程失败
```

## 发送前检查

发送函数需要检查：

```text
ser 是否为 None
ser.is_open 是否为 True
command 是否为 str
command.strip() 是否为空
command 是否属于支持列表
写入是否发生异常
实际写入字节数是否完整
```

## 串口命令协议帧

Python 字符串不能直接传给：

```python
ser.write()
```

`ser.write()` 接收的是：

```text
bytes
```

命令转换流程：

```text
led_on
→ 去除首尾空白
→ 添加 \r\n
→ UTF-8 编码
→ b"led_on\r\n"
→ ser.write()
```

概念代码：

```python
command_frame = command + "\r\n"
command_bytes = command_frame.encode("utf-8")
```

`\r\n` 表示一条完整命令结束。

STM32 根据换行符判断：

```text
当前命令已经接收完整
```

## ser.write() 返回值

```python
written_bytes = ser.write(command_bytes)
```

返回：

```text
实际写入的字节数
```

必须检查：

```python
if written_bytes != len(command_bytes):
    return False
```

例如：

```text
准备写入：8 字节
实际写入：5 字节
```

不能将这种情况视为成功。

比较的是：

```text
实际写入字节数
与
bytes 对象长度
```

而不是原始字符串长度。

## 串口异常处理

写入过程需要捕获：

```python
serial.SerialTimeoutException
serial.SerialException
```

### SerialTimeoutException

表示：

```text
串口写入超过 write_timeout
```

### SerialException

可能包括：

```text
USB-TTL 被拔出
设备节点失效
串口驱动异常
底层 I/O 错误
```

即使发送前已经检查：

```python
ser.is_open
```

仍然必须捕获写入异常。

原因：

```text
检查时串口正常
→ 下一瞬间设备被拔出
→ write() 执行时仍可能失败
```

前置检查不能替代运行时异常处理。

## 读超时与写超时

串口配置：

```python
serial.Serial(
    port,
    baudrate,
    timeout=0.2,
    write_timeout=0.2,
)
```

区别：

```text
timeout
→ readline() 最多等待多长时间

write_timeout
→ write() 最多等待多长时间
```

读超时避免主线程永久阻塞在串口接收。

写超时避免 Paho MQTT 回调线程永久阻塞在串口写入。

## is_open 是属性

正确：

```python
if not ser.is_open:
    return False
```

错误：

```python
if not ser.is_open():
    return False
```

因为 `is_open` 是布尔属性，不是函数。

错误调用可能产生：

```text
TypeError: 'bool' object is not callable
```

## 删除 Linux 模拟执行

旧流程：

```text
收到 led_on
→ execute_command()
→ Linux 打印模拟执行
→ 立即发布 success ACK
```

这只能证明：

```text
Linux 模拟逻辑执行成功
```

不能证明：

```text
STM32 收到命令
STM32 解析成功
真实 LED 已经动作
```

Day 56 将流程修改为：

```text
收到合法命令
→ 转发到真实 STM32 串口
```

不再使用 Linux 本地模拟执行结果冒充设备结果。

## 使用 Paho userdata 传递串口对象

串口对象在 `main.py` 中创建：

```python
ser = open_ser_port(...)
```

MQTT 命令在：

```python
on_message()
```

中处理。

不应使用：

```text
随意定义全局变量
mqtt_client.py 反向导入 main.py
```

否则可能造成：

- 模块耦合；
- 循环导入；
- 资源生命周期不明确；
- 难以测试。

通过 Paho `userdata` 传递运行时上下文：

```python
client.user_data_set({
    "serial_port": serial_port,
})
```

回调中获取：

```python
serial_port = userdata.get("serial_port")
```

## 初始化顺序调整

原流程：

```text
先启动 MQTT
→ 后打开串口
```

这样 MQTT 回调开始工作时，可能还没有真实串口对象。

调整后的顺序：

```text
读取配置
→ ser = None
→ 尝试打开真实串口
→ 确定真实或 Mock 模式
→ 创建 MQTT Client
→ 将 ser 放入 userdata
→ 启动 Paho 后台线程
→ 进入主循环
```

这样可以保证：

```text
on_message() 工作前
userdata 中已经有确定的串口上下文
```

即使打开失败：

```text
serial_port = None
```

发送函数也能返回失败，而不是直接崩溃。

## on_message() 新流程

```text
收到 MQTT Command
→ Payload 解码
→ JSON 解析
→ 提取 command
→ 获取 serial_port
→ send_command_to_serial()
```

### 串口写入成功

输出：

```text
command forwarded to serial
```

此时不能发布 MQTT success ACK。

它只能证明：

```text
Linux 已将字节完整交给串口驱动
```

不能直接证明：

```text
STM32 已收到
STM32 已解析
LED 已动作
命令执行成功
```

### 串口写入失败

例如：

```text
ser is None
串口关闭
USB 设备拔出
写入超时
不支持的命令
```

此时可以发布：

```json
{
  "command": "led_on",
  "status": "failed"
}
```

因为命令没有成功进入设备执行阶段。

## ACK 语义分层

必须区分：

```text
MQTT JSON 格式合法
≠ Linux 串口写入成功
≠ STM32 收到完整命令
≠ STM32 命令解析成功
≠ STM32 硬件执行成功
```

当前阶段：

```text
ser.write() 返回完整字节数
→ Linux 转发成功

STM32 输出 rx:led_on
→ STM32 收到完整命令
```

但这还不能发布：

```json
{
  "command": "led_on",
  "status": "success"
}
```

必须等待 STM32 返回真实执行结果。

Day 56 阶段 ACK 协议尚未最终冻结；Day 10 STM32 最终统一为：

```text
ack:<command>:<status>
```

例如：

```text
ack:led_on:success
ack:led_off:success
```

## 真实 led_on 联调

MQTT 发布：

```json
{
  "command": "led_on"
}
```

网关输出：

```text
mqtt command received
command: led_on
command forwarded to serial: led_on
stm32 debug: rx:led_on
```

证明：

```text
MQTT
→ Paho on_message()
→ Linux 串口写入
→ CH340 TXD
→ STM32 PA3
→ USART2 中断接收
→ STM32 拼接完整命令
```

## 真实 led_off 联调

MQTT 发布：

```json
{
  "command": "led_off"
}
```

网关输出：

```text
command forwarded to serial: led_off
stm32 debug: rx:led_off
```

同样验证通过。

## 不支持命令测试

MQTT 发布：

```json
{
  "command": "fan_start"
}
```

网关输出：

```text
unsupported serial command: fan_start
mqtt ack queued: edgeaiot/stm32_node_01/ack
```

ACK Topic 收到：

```json
{
  "command": "fan_start",
  "status": "failed"
}
```

数据流：

```text
JSON 格式合法
→ command 字段存在
→ 但命令不属于支持列表
→ 不写入 STM32
→ 网关直接发布 failed ACK
```

## 为什么非法命令可以直接 failed

非法命令在 Linux 网关侧已经可以确定：

```text
设备协议不支持该命令
```

因此不需要下发 STM32，也不需要等待设备 ACK。

而合法命令：

```text
led_on
led_off
```

写入串口后，不能立即发布 success，必须等待 STM32 的真实执行结果。

## 上行链路没有被破坏

测试下行命令期间，以下功能仍持续运行：

```text
STM32 DHT11 调试日志
temperature 遥测解析
MQTT Telemetry
Heartbeat
```

说明当前已经具备双向通信基础：

```text
STM32 → Linux → MQTT
MQTT → Linux → STM32
```

但设备执行 ACK 闭环仍未完成。

## 主线程与 Paho 线程职责

### Python 主线程

负责：

```text
持续读取串口
STM32 上行数据分类
温度解析
Telemetry 发布触发
Heartbeat 定时
串口资源生命周期管理
```

### Paho 后台线程

负责：

```text
MQTT 网络收发
连接与自动重连
on_message() 回调
Command 解析
短串口命令写入
失败 ACK 排队发布
```

串口写入配置 `write_timeout`，避免 MQTT 回调线程长期阻塞。

## CRLF 与 Git 中的 ^M

Git Diff 中出现：

```text
^M
```

通常表示文件使用了：

```text
CRLF
```

而 Linux 项目通常统一使用：

```text
LF
```

混合换行可能导致：

- Git Diff 出现大量无意义修改；
- 代码审查困难；
- 跨平台工具行为不一致；
- 合并冲突增加。

检查：

```bash
git diff --check

grep -n $'\r' command_handler.py
grep -n $'\r' mqtt_client.py
grep -n $'\r' main.py
```

无输出说明没有检测到对应问题。

## 提交前语法检查

```bash
python -m py_compile \
  main.py \
  mqtt_client.py \
  command_handler.py
```

没有输出表示语法检查通过。

这不能替代真实运行测试，但可以发现：

- 缩进错误；
- 括号错误；
- 语法错误；
- 部分名称拼写问题。

## 今日主要修改

```text
command_handler.py
→ 新增 send_command_to_serial()

mqtt_client.py
→ userdata 传递 serial_port
→ on_message() 改为真实串口转发
→ 不再模拟 success ACK

main.py
→ 串口先于 MQTT 初始化
→ 配置 write_timeout
→ 将 ser 传入 MQTT Client
```

## Day 56 验收结果

```text
✓ 完成真实串口双向接线
✓ USB-TTL 成功重新 bind 和 attach
✓ 串口对象在 MQTT 启动前创建
✓ 串口对象通过 userdata 传入回调
✓ 实现 send_command_to_serial()
✓ 支持 led_on 和 led_off
✓ 命令补充 \r\n
✓ 命令编码为 UTF-8 bytes
✓ 检查实际写入字节数
✓ 捕获写超时与串口异常
✓ led_on 成功到达 STM32
✓ led_off 成功到达 STM32
✓ STM32 打印完整接收行
✓ fan_start 被拒绝且未下发设备
✓ 不支持命令发布 failed ACK
✓ 写入成功时没有伪造 success ACK
✓ DHT11 Telemetry 持续正常
✓ Heartbeat 持续正常
✓ 统一 LF 换行并完成语法检查
```

## 当前完整状态

已完成上行：

```text
真实 DHT11
→ STM32
→ USART2
→ Linux
→ JSON
→ MQTT Telemetry
```

已完成下行传输：

```text
MQTT Command
→ Linux
→ USART2
→ STM32 收到完整字符串
```

Day 56 尚未完成：

```text
STM32 解析命令
→ 控制真实 LED
→ 返回执行结果
→ Linux 解析 ACK
→ 发布真实 MQTT ACK
```

## 当前真实边界补充

后续 STM32 Day 10 已经完成：

```text
命令解析
→ LED 真实执行
→ GPIO 回读
→ 串口 ACK 返回
```

但是 Linux 网关当前仍未实现：

```text
识别 STM32 ACK
→ 与等待命令关联
→ 根据真实结果发布 MQTT ACK
```

当前只有网关本地判定为非法的命令，才会直接发布 `failed` ACK。

## 面试表达

我通过 Paho MQTT 的 `userdata`，把主程序中已经打开的 PySerial 对象传递给 `on_message()`，避免使用全局变量或模块反向导入。

收到合法的 `led_on` 或 `led_off` 后，网关将命令补充 CRLF 结束符、编码为 UTF-8 Bytes，并写入真实 USART2，同时检查实际写入字节数，处理写超时和 `SerialException`。

我没有在 `ser.write()` 成功后立即发布设备执行成功 ACK，因为写入成功只能说明 Linux 将字节交给串口驱动。只有 STM32 真正执行硬件动作并返回结果后，网关才能发布可信的 success ACK。

## 后续计划

```text
STM32 串口 ACK
→ Linux 消息分类
→ 解析 command 与 status
→ 与等待中的命令关联
→ 发布 MQTT success / failed
→ 无响应超时处理
```
