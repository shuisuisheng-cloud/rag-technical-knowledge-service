---
title: Linux-STM32 物联网边缘网关 Day 57 STM32 真实执行 ACK 闭环
project: Linux-STM32 物联网边缘网关
system_layer: 通信层 / 数据中枢
document_type: software_module_record
status: software_verified
last_updated: 2026-07-28
tags: [Linux, Python, MQTT, PySerial, STM32, ACK, Threading, StateManagement, Command]
---

# Linux-STM32 物联网边缘网关 Day 57 STM32 真实执行 ACK 闭环

## 今日目标

在 Day 56 已经完成 MQTT 命令真实串口下发的基础上，完成合法命令的真实执行 ACK 闭环：

```text
MQTT Command
→ Linux 网关
→ STM32 USART2
→ STM32 执行硬件动作
→ STM32 返回串口 ACK
→ Linux 解析并匹配 ACK
→ 发布 MQTT success / failed ACK
```

今天的核心原则是：

```text
Linux 串口写入成功
≠
STM32 执行成功
```

只有收到 STM32 返回的真实执行结果，网关才能发布可信的 MQTT success ACK。

## Day 56 结束时的状态

此前已经完成：

```text
MQTT Command
→ Linux 网关解析
→ 合法命令写入真实串口
→ STM32 收到完整命令
```

STM32 已能返回：

```text
ack:led_on:success
ack:led_off:success
```

但 Linux 网关当时只把这些行作为普通 STM32 输出处理，没有：

```text
正式识别 ACK
→ 匹配原命令
→ 发布 MQTT ACK
```

非法命令仍然可以由网关本地直接返回失败：

```text
fan_start
→ 网关判断不支持
→ 不下发 STM32
→ 直接发布 failed ACK
```

## 今日完成结果

今天完成：

```text
✓ 实现 STM32 ACK 解析
✓ 将 ACK 与温度遥测、调试日志分类
✓ 增加 pending_command 共享状态
✓ 增加 pending_since 时间字段
✓ 使用 threading.Lock 保护共享状态
✓ 合法命令发送前登记 pending 状态
✓ 存在未完成命令时拒绝第二条命令
✓ 串口发送失败时回滚 pending 状态
✓ 收到匹配 ACK 后发布真实 MQTT ACK
✓ 发布完成后清除 pending 状态
✓ led_on 真实 success ACK 闭环通过
✓ led_off 真实 success ACK 闭环通过
✓ 未使用串口写入结果伪造设备成功
```

## STM32 ACK 协议

STM32 当前统一输出：

```text
ack:<command>:<status>
```

成功示例：

```text
ack:led_on:success
ack:led_off:success
```

失败示例：

```text
ack:led_on:failed
ack:led_off:failed
ack:hello:failed
```

字段含义：

```text
ack
→ 消息类型

command
→ STM32 实际处理的命令

status
→ STM32 返回的执行结果
```

当前允许的状态：

```text
success
failed
```

所有 ACK 都以：

```text
\r\n
```

结束，Linux 网关通过按行读取获得完整串口消息。

## parse_stm32_ack()

今天增加了 ACK 解析函数：

```python
parse_stm32_ack(serial_data)
```

输入：

```text
一行已经去除换行的串口字符串
```

例如：

```text
ack:led_on:success
```

输出概念结构：

```python
{
    "command": "led_on",
    "status": "success",
}
```

如果输入不是合法 ACK，则返回：

```python
None
```

解析器需要检查：

```text
是否以 ack: 开头
字段数量是否正确
command 是否为空
status 是否属于 success / failed
```

解析器只负责：

```text
识别格式
→ 提取 command
→ 提取 status
```

它不负责：

```text
判断当前是否有等待命令
判断 ACK 是否属于当前命令
发布 MQTT
清除共享状态
```

## 串口消息分类

同一个 USART2 当前承载：

```text
温度遥测
STM32 调试日志
命令接收日志
执行 ACK
```

示例：

```text
temperature:25.6
DHT11 raw: ...
rx:led_on
ack:led_on:success
```

网关处理顺序概念上为：

```text
收到一行串口数据
→ 是否为 ACK？
    ├─ 是
    │   → parse_stm32_ack()
    │   → 进入 ACK 处理
    │
    └─ 否
        → 是否为 temperature 协议？
            ├─ 是
            │   → 遥测解析与 MQTT 发布
            │
            └─ 否
                → STM32 Debug
```

必须先识别消息类型，再进入对应业务流程。

不能把：

```text
ack:led_on:success
```

当成温度数据，也不能只把它当成普通 Debug 打印后丢弃。

## 为什么需要 pending_command

网关收到合法命令并写入 STM32 后，需要记住：

```text
当前正在等待哪个命令的结果
```

共享状态：

```python
command_state = {
    "pending_command": None,
    "pending_since": None,
    "lock": threading.Lock(),
}
```

字段职责：

```text
pending_command
→ 当前已经下发、正在等待 STM32 ACK 的命令

pending_since
→ 命令进入等待状态的时间
→ 为后续超时处理准备

lock
→ 保护 Paho 回调线程与主线程共同访问状态
```

## 两个线程为什么会访问同一状态

### Paho MQTT 后台线程

负责：

```text
接收 MQTT Command
→ 解析命令
→ 检查 busy
→ 登记 pending_command
→ 写入 STM32 串口
```

### Python 主线程

负责：

```text
持续读取 STM32 串口
→ 分类串口消息
→ 收到 ACK
→ 检查 pending_command
→ 发布 MQTT ACK
→ 清除 pending 状态
```

因此：

```text
Paho 线程写 command_state
主线程读写 command_state
```

如果没有锁，可能发生：

- 两个线程同时修改状态；
- pending_command 被覆盖；
- ACK 匹配到错误命令；
- 状态刚检查完就被另一个线程改变；
- 清除动作与新命令登记交叉执行。

## threading.Lock 的作用

访问共享状态时使用：

```python
with command_state["lock"]:
    ...
```

锁保护的是一段完整的状态操作，而不只是某一行赋值。

例如登记命令时需要把：

```text
检查 pending_command
→ 写入 pending_command
→ 写入 pending_since
```

视为一个不可被其他线程插入的整体操作。

收到 ACK 时，需要把：

```text
读取 pending_command
→ 判断是否匹配
→ 清除 pending_command
→ 清除 pending_since
```

作为一个完整状态转换。

## 单命令 pending 模型

当前网关一次只允许存在一个未完成命令：

```text
pending_command is None
→ 可以接收新合法命令

pending_command is not None
→ 网关处于 busy 状态
→ 拒绝新的设备命令
```

例如：

```text
led_on 已下发
→ 正在等待 ack:led_on:success

此时又收到 led_off
→ 不应覆盖 pending_command
→ 不应立即再次下发
```

否则可能发生：

```text
pending_command 原来是 led_on
→ 被 led_off 覆盖
→ STM32 返回 led_on ACK
→ 网关无法正确匹配
```

当前单 pending 模型适合：

```text
单设备
低频控制命令
每次只执行一个动作
```

## 为什么必须先登记 pending 再写串口

正确顺序：

```text
检查当前不 busy
→ 登记 pending_command
→ 记录 pending_since
→ 写入串口
```

不能采用：

```text
先写串口
→ 再登记 pending_command
```

因为 STM32 响应速度可能很快。

错误时序可能是：

```text
Linux 写入命令
→ STM32 立即执行并返回 ACK
→ Linux 主线程收到 ACK
→ 此时 pending_command 还没登记
→ ACK 被认为没有对应命令
```

因此发送前必须先建立等待状态。

## 串口发送失败时为什么要回滚

登记 pending 后，串口写入仍可能失败：

```text
USB-TTL 被拔出
串口对象关闭
写入超时
底层 I/O 异常
部分写入
```

如果发送失败后不回滚：

```text
pending_command 永远不为空
→ 网关一直认为有命令在等待
→ 后续所有命令都被 busy 拒绝
```

正确处理：

```text
先登记 pending
→ 尝试写串口

写入成功
→ 保留 pending
→ 等待 STM32 ACK

写入失败
→ 清除 pending_command
→ 清除 pending_since
→ 发布或返回失败结果
```

## ACK 匹配流程

收到合法 ACK 后：

```text
解析 command 和 status
→ 加锁读取 pending_command
→ 检查当前是否存在等待命令
→ 比较 ACK command 与 pending_command
```

只有满足：

```text
ACK command == pending_command
```

才能将该 ACK 视为当前命令的真实执行结果。

例如：

```text
pending_command = led_on
收到 ack:led_on:success
→ 匹配成功
```

而：

```text
pending_command = led_on
收到 ack:led_off:success
→ 不应作为当前命令结果发布
```

## 匹配成功后的状态转换

```text
收到匹配 ACK
→ 取得 command 和 status
→ 清除 pending_command
→ 清除 pending_since
→ 发布 MQTT ACK
```

状态变化：

```text
IDLE
→ 收到合法 MQTT 命令
→ PENDING
→ 收到匹配 STM32 ACK
→ IDLE
```

清除状态后，网关才能接受下一条命令。

## 为什么不能只根据 status 发布

假设当前等待：

```text
pending_command = led_on
```

但串口收到：

```text
ack:led_off:success
```

如果只看到 `success` 就发布成功，会造成：

```text
led_on 请求
→ 却使用 led_off 的结果回复
```

因此必须同时验证：

```text
command
+
status
```

## MQTT ACK Payload

匹配成功后，网关根据 STM32 返回结果发布：

```json
{
  "command": "led_on",
  "status": "success"
}
```

或：

```json
{
  "command": "led_on",
  "status": "failed"
}
```

这里的 `status` 来自：

```text
STM32 真实执行 ACK
```

而不是：

```text
Linux ser.write() 的返回结果
```

## 合法命令完整数据流

以 `led_on` 为例：

```text
MQTT 发布 {"command":"led_on"}
→ Paho on_message()
→ JSON 和命令校验
→ 检查当前没有 pending
→ pending_command = "led_on"
→ 记录 pending_since
→ send_command_to_serial()
→ 写入 b"led_on\r\n"
→ STM32 USART2 中断接收
→ STM32 拼接 "led_on"
→ strcmp() 解析
→ PA1 LED 点亮
→ GPIO 读回验证
→ STM32 输出 ack:led_on:success
→ Linux 主线程读取 ACK
→ parse_stm32_ack()
→ 匹配 pending_command
→ 清除 pending 状态
→ 发布 MQTT success ACK
```

## led_on 真实验证

MQTT 输入：

```json
{
  "command": "led_on"
}
```

设备链路：

```text
command forwarded to serial: led_on
stm32 debug: rx:led_on
STM32 ACK: ack:led_on:success
```

最终 MQTT ACK：

```json
{
  "command": "led_on",
  "status": "success"
}
```

真实硬件现象：

```text
板载 LED 点亮
```

## led_off 真实验证

MQTT 输入：

```json
{
  "command": "led_off"
}
```

设备链路：

```text
command forwarded to serial: led_off
stm32 debug: rx:led_off
STM32 ACK: ack:led_off:success
```

最终 MQTT ACK：

```json
{
  "command": "led_off",
  "status": "success"
}
```

真实硬件现象：

```text
板载 LED 熄灭
```

## 非法命令仍由网关本地处理

例如：

```json
{
  "command": "fan_start"
}
```

网关已经知道该命令不属于允许集合，因此：

```text
不登记 pending_command
→ 不写入 STM32
→ 直接发布 failed ACK
```

该失败结果来自：

```text
网关协议校验
```

不是 STM32 执行结果。

## 三种失败来源

### 网关协议失败

例如：

```text
JSON 非法
缺少 command
command 类型错误
命令不受支持
```

网关可直接确定失败。

### 串口发送失败

例如：

```text
ser is None
串口关闭
写入超时
USB-TTL 被拔出
部分写入
```

此时需要回滚 pending 状态。

### STM32 执行失败

STM32 返回：

```text
ack:led_on:failed
```

网关匹配后发布：

```json
{
  "command": "led_on",
  "status": "failed"
}
```

这三种失败发生在不同层，不能混为一谈。

## 当前线程协作

```text
Paho 后台线程
→ MQTT 网络循环
→ on_message()
→ 命令校验
→ pending 登记
→ 串口发送

Python 主线程
→ 串口 readline()
→ Telemetry / Debug / ACK 分类
→ ACK 匹配
→ MQTT ACK 发布
→ pending 清理
```

当前使用锁保护命令状态，但仍应避免在持锁期间进行长时间阻塞操作。

## 当前完成的闭环

```text
MQTT Command
→ Linux 网关
→ STM32
→ LED 真实动作
→ STM32 ACK
→ Linux ACK 匹配
→ MQTT ACK
```

这意味着合法命令已经不再依赖 Linux 模拟结果，而是使用 STM32 设备侧真实执行结果。

## 当前限制

### 1. 尚未实现 ACK 超时

虽然已经保存：

```text
pending_since
```

但当前尚未完整实现：

```text
当前时间 - pending_since >= timeout
→ 清除 pending
→ 发布 timeout / failed
```

### 2. 一次只能处理一个命令

当前使用单一：

```text
pending_command
```

不支持多个命令并发等待。

### 3. ACK 没有 request_id

当前依靠：

```text
command 名称
```

进行匹配。

连续发送相同命令时，不容易区分：

```text
第一次 led_on
第二次 led_on
```

后续更完整的协议应增加：

```text
request_id
```

### 4. 迟到 ACK 尚未完整处理

命令超时清理后，STM32 可能又返回旧 ACK。

需要明确：

```text
迟到 ACK
→ 不得错误匹配新命令
```

### 5. 格式错误 ACK 仍需强化

后续需要专门测试：

```text
ack:
ack:led_on
ack:led_on:unknown
ack:led_on:success:extra
```

### 6. 串口断开恢复尚未完成

运行期间拔出 USB-TTL 后，还需要完成：

```text
检测串口失效
→ 关闭旧对象
→ 周期重新扫描设备
→ 重新打开串口
→ 恢复上下行
```

### 7. STM32 首条命令偶发污染

真实联调中发现：

```text
STM32 复位或刚启动后
第一条接收行偶尔夹杂随机字节
```

这是设备侧 USART2 接收恢复和坏行处理问题。

网关 Day 57 的 ACK 闭环可以独立提交，STM32 侧后续需要：

```text
坏行标记
→ 丢弃整行直到 \n
→ UART 错误恢复
→ 重新启动中断接收
```

## Day 57 验收结果

```text
✓ STM32 ACK 协议识别通过
✓ parse_stm32_ack() 解析通过
✓ ACK / Telemetry / Debug 分类通过
✓ pending_command 状态建立
✓ pending_since 状态建立
✓ threading.Lock 共享状态保护
✓ busy 状态拒绝新命令
✓ 发送前登记 pending
✓ 发送失败回滚 pending
✓ matched ACK 清除 pending
✓ led_on 真实 MQTT success ACK
✓ led_off 真实 MQTT success ACK
✓ 非法命令仍由网关直接 failed
✓ 没有使用 ser.write() 伪造 success
✓ DHT11 Telemetry 未被破坏
✓ MQTT Heartbeat 未被破坏
```

## Git 提交

```text
commit: 54caa5e
message: feat: complete STM32 command ACK loop
```

提交前完成：

```bash
python -m py_compile \
  main.py \
  mqtt_client.py \
  command_handler.py

git diff --check
```

最终工作区保持干净，并已完成远程同步。

## 当前项目边界

已经完成：

```text
真实 DHT11 上行遥测
MQTT 命令真实串口下发
STM32 LED 真实执行
STM32 设备侧 ACK
Linux ACK 解析
单 pending 命令关联
真实 MQTT success / failed ACK
MQTT 断线自动重连
Heartbeat
LWT 与 Retained Status
```

尚未完成：

```text
ACK 超时
无响应处理
迟到 ACK
错误格式 ACK
重复命令与乱序消息
USB-TTL 运行中断开与恢复
完整集成测试
V1 冻结与技术面验收
```

## 面试表达

我为 MQTT 到 STM32 的合法控制命令实现了设备侧真实 ACK 闭环。

Paho 回调收到合法命令后，不会在串口写入成功时立即发布 success，而是先在共享状态中登记 `pending_command` 和 `pending_since`，再将命令写入串口。登记动作和 ACK 处理使用 `threading.Lock` 保护，避免 Paho 后台线程与串口主线程并发修改状态。

STM32 完成 LED 控制和 GPIO 读回后，返回 `ack:<command>:<status>`。Linux 主线程解析 ACK，并且只有当 ACK 中的命令与 `pending_command` 匹配时，才清除等待状态并发布 MQTT success 或 failed。

当前采用单 pending 模型，下一步将利用 `pending_since` 实现 ACK 超时，并处理无响应、迟到 ACK、格式错误和串口断开恢复。

## 下一步

```text
pending_since
→ time.monotonic()
→ 检查等待时间
→ 超时清除 pending
→ 发布 timeout / failed
```

随后测试：

```text
STM32 无响应
ACK 格式错误
ACK 命令不匹配
迟到 ACK
重复命令
USB-TTL 拔出与重新连接
```
