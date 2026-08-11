---
title: Linux-STM32 物联网边缘网关 Day 58 STM32 ACK 超时与异常响应处理
project: Linux-STM32 物联网边缘网关
system_layer: 通信层 / 数据中枢
document_type: daily_dev_record
status: software_verified
last_updated: 2026-07-30
tags: [Linux, Python, MQTT, STM32, UART, ACK, Timeout, StateMachine, Threading]
---

# Linux-STM32 物联网边缘网关 — Day 58

## 一、基本信息

- 学习日期：2026-07-29，连续完成至 07-30 凌晨
- 学习日：Day 58
- 主题：STM32 ACK 超时与异常响应处理
- Git 提交：`6476e12`
- Commit Message：`feat: add STM32 command ACK timeout handling`
- 状态：已推送，工作区 clean

## 二、Day 58 目标

Day 57 已经完成正常命令执行闭环：

```text
MQTT Command
→ Linux 网关
→ UART
→ STM32 执行
→ STM32 ACK
→ Linux 匹配 pending_command
→ MQTT success / failed
```

但是如果 STM32 没有正常返回 ACK，原来的系统缺少结束事务的机制。

Day 58 需要补齐：

```text
命令已经写入串口
→ 等待匹配 STM32 ACK
→ 超过规定时间
→ 清空 pending 状态
→ 发布 MQTT timeout
→ 允许下一条命令继续执行
```

核心问题：

```text
串口 write 成功
≠
STM32 执行结果已经确认
```

网关只有收到匹配 ACK，才能确认最终执行结果。

---

## 三、MQTT ACK 三状态

原先 ACK 构造逻辑只使用布尔值：

```text
True
→ success

False
→ failed
```

这样无法表达：

```text
命令已经下发
但最终结果无法确认
```

因此 Day 58 将 ACK 状态扩展为：

```text
success
failed
timeout
```

示例：

```json
{
  "command": "led_on",
  "status": "success"
}
```

```json
{
  "command": "led_off",
  "status": "failed"
}
```

```json
{
  "command": "led_on",
  "status": "timeout"
}
```

### 三种状态的真实含义

#### success

```text
Linux 下发命令
→ STM32 返回匹配 ACK
→ status=success
```

表示设备侧确认执行成功。

#### failed

可能来自：

```text
命令本身非法
串口尚未成功写入
STM32 返回 failed ACK
```

此时网关可以明确确认操作失败。

#### timeout

```text
命令已经成功写入串口
→ 规定时间内没有收到匹配 ACK
```

只能说明：

```text
网关无法确认最终结果
```

不能直接说明：

```text
STM32 一定没有执行
```

---

## 四、ACK Payload 参数校验

ACK 构造函数加入参数校验。

需要检查：

```text
command 是否为 str
command.strip() 后是否为空
status 是否为 str
status 是否属于允许集合
```

允许状态：

```text
success
failed
timeout
```

非法状态：

```text
unknown
```

应抛出：

```text
ValueError
```

这样可以防止内部逻辑错误产生不受协议定义的 MQTT ACK。

---

## 五、ACK Timeout 配置

在配置文件中加入：

```json
{
  "command_ack_timeout": 3.0
}
```

含义：

```text
合法命令成功写入串口后
→ 最多等待匹配 STM32 ACK 3 秒
```

该配置需要保证：

```text
是数字
并且
大于 0
```

---

## 六、为什么使用 time.monotonic()

超时计算使用：

```python
time.monotonic()
```

基本关系：

```text
elapsed =
当前 monotonic 时间
-
pending_since
```

不使用普通系统时间的原因是：

```text
系统时间可能因为：
网络校时
用户修改
时区变化
而发生跳变
```

`time.monotonic()` 只保证单调递增，因此适合：

```text
超时
重试间隔
心跳间隔
```

等相对时间计算。

---

## 七、pending_since 的职责

Day 57 的共享命令状态已经包含：

```python
command_state = {
    "pending_command": None,
    "pending_since": None,
    "lock": ...
}
```

### pending_command

表示：

```text
当前正在等待哪个 STM32 命令结果
```

### pending_since

表示：

```text
该命令从什么时候开始等待 ACK
```

状态转换：

```text
IDLE
→ 合法命令下发
→ pending_command = command
→ pending_since = time.monotonic()
→ PENDING
```

收到匹配 ACK：

```text
PENDING
→ 清除 pending_command
→ 清除 pending_since
→ IDLE
```

发生超时：

```text
PENDING
→ 清除 pending_command
→ 清除 pending_since
→ IDLE
```

---

## 八、非阻塞超时检查

新增函数：

```text
check_command_ack_timeout(
    command_state,
    timeout_seconds
)
```

职责：

```text
加锁
→ 读取 pending_command
→ 读取 pending_since

没有待确认命令
→ 返回 None

尚未达到超时时间
→ 返回 None

已经超时
→ 保存当前 command
→ pending_command = None
→ pending_since = None
→ 解锁
→ 返回超时 command
```

这个函数不负责：

```text
MQTT publish
ACK Payload 构造
sleep 等待
```

这些职责留给主循环。

---

## 九、为什么不能直接 sleep 3 秒

错误方案：

```python
time.sleep(command_ack_timeout)
```

如果在命令下发后直接等待 3 秒，会阻塞主循环。

这期间无法正常执行：

```text
STM32 遥测读取
Heartbeat
其他状态检查
Ctrl+C 响应
```

正确方式：

```text
主循环持续运行
→ 每一轮快速检查 elapsed
→ 未超时立即返回
→ 超时才进行状态转换
```

因此 ACK timeout 是：

```text
非阻塞监督
```

而不是：

```text
阻塞等待
```

---

## 十、主循环中的 ACK Timeout

主循环概念流程：

```text
while running:

    处理串口数据

    处理 Telemetry

    处理 Heartbeat

    检查 command ACK timeout

    短暂 sleep
```

ACK 等待期间，网关仍然可以：

```text
持续接收 STM32 数据
持续发布 Heartbeat
持续运行 MQTT 网络线程
持续响应程序退出
```

---

## 十一、超时后的状态恢复

发生超时时：

```text
pending_command = None
pending_since = None
```

但是：

```text
command_state["lock"]
```

必须继续存在。

锁是长期共享同步工具，不是一次命令的数据。

看到：

```text
<unlocked _thread.lock object ...>
```

表示：

```text
锁对象仍然存在
并且当前已经释放
```

这是正常状态。

---

## 十二、真实 ACK Timeout 测试

测试时只断开：

```text
STM32 PA2 TX
→
USB-TTL RXD
```

继续保留：

```text
USB-TTL TXD
→
STM32 PA3 RX

GND 共地
```

此时数据流为：

```text
MQTT led_on
→ Linux 成功写入串口
→ STM32 可以收到并执行
→ STM32 回传线路被断开
→ Linux 无法收到 rx 和 ACK
→ 3 秒后 timeout
```

网关日志：

```text
command forwarded to serial: led_on
waiting for STM32 ack
led_on is timeout
mqtt ack queued
```

MQTT 订阅端收到：

```json
{
  "command": "led_on",
  "status": "timeout"
}
```

### 重要结论

```text
timeout
```

表示：

```text
网关在规定时间内没有得到可确认结果
```

不等于：

```text
STM32 一定没有执行
```

因为设备可能已经执行，只是 ACK 丢失。

---

## 十三、Timeout 后恢复测试

重新连接 STM32 TX 回传线。

随后发送：

```text
led_off
```

得到：

```text
STM32 接收 led_off
→ LED 真实熄灭
→ ack:led_off:success
→ Linux 匹配 ACK
→ MQTT success
```

证明：

```text
timeout 后 pending 正确清空
→ 系统没有永久 busy
→ 后续命令仍然可以形成正常闭环
```

---

## 十四、Malformed ACK

测试条件：

```text
pending_command = led_on
```

收到：

```text
ack:led_on:unknown
```

其中：

```text
unknown
```

不属于允许状态。

处理：

```text
parse_stm32_ack()
→ 判断 ACK 格式非法
→ malformed ACK
→ 不清除 pending
→ 不发布 success / failed
```

结果：

```text
pending_command 仍然是 led_on
```

因为一个格式错误的 ACK 不能结束当前事务。

---

## 十五、Mismatched ACK

测试：

```text
pending_command = led_on
```

但收到：

```text
ack:led_off:success
```

结果：

```text
ACK command = led_off
pending command = led_on
→ 不匹配
→ 不清除 led_on
→ 不发布 led_on success
→ 继续等待真正的 led_on ACK
```

这样避免：

```text
A 命令
被 B 命令的 ACK 错误确认
```

---

## 十六、Unexpected / Late ACK

测试：

```text
pending_command = None
```

此时收到：

```text
ack:led_on:success
```

处理：

```text
当前没有等待事务
→ unexpected ACK
→ 不发布新的 MQTT success
→ command_state 保持空
```

这可以避免：

```text
第一次：
led_on timeout

稍后旧 ACK 到达：
led_on success
```

导致上层同时看到：

```text
timeout
+
success
```

两个冲突结果。

---

## 十七、Busy 与 Timeout 联合测试

测试流程：

```text
led_on 下发
→ pending = led_on
→ 等待 ACK
```

3 秒内再次发送：

```text
led_off
```

因为：

```text
pending_command != None
```

所以：

```text
led_off 不下发
→ MQTT failed
```

随后：

```text
led_on 达到 3 秒
→ MQTT timeout
→ pending 清空
```

订阅端最终看到：

```json
{
  "command": "led_off",
  "status": "failed"
}
```

以及：

```json
{
  "command": "led_on",
  "status": "timeout"
}
```

证明：

```text
单 pending 串行保护有效
busy 不会覆盖旧事务
timeout 可以最终结束旧事务
timeout 后系统不会永久 busy
```

---

## 十八、异常 ACK 的处理原则

当前原则：

```text
合法且匹配的 ACK
→ 可以结束 pending

malformed ACK
→ 不能结束 pending

mismatched ACK
→ 不能结束 pending

当前没有 pending 的 ACK
→ 作为 unexpected / late ACK
→ 不重复发布结果
```

因此：

```text
ACK 存在
```

不等于：

```text
ACK 可以被当前事务接受
```

必须同时满足：

```text
格式合法
+
command 匹配
+
当前确实存在 pending
```

---

## 十九、Day 58 完整状态机

```text
IDLE
│
│ 合法 MQTT 命令
↓
登记 pending_command
登记 pending_since
│
│
├─ 串口写入失败
│  → 清空 pending
│  → MQTT failed
│  → IDLE
│
└─ 串口写入成功
   ↓
 PENDING
   │
   ├─ 收到匹配 success ACK
   │  → 清空 pending
   │  → MQTT success
   │  → IDLE
   │
   ├─ 收到匹配 failed ACK
   │  → 清空 pending
   │  → MQTT failed
   │  → IDLE
   │
   ├─ malformed ACK
   │  → 保留 pending
   │
   ├─ mismatched ACK
   │  → 保留 pending
   │
   └─ 超过 timeout
      → 清空 pending
      → MQTT timeout
      → IDLE
```

---

## 二十、Day 58 验收结果

```text
✓ success / failed / timeout 三状态 ACK
✓ ACK 参数校验
✓ command_ack_timeout 配置
✓ time.monotonic() 超时计算
✓ 非阻塞 timeout 检查
✓ timeout 后安全清除 pending
✓ MQTT timeout 发布
✓ timeout 后允许新命令
✓ malformed ACK 不结束 pending
✓ mismatched ACK 不结束 pending
✓ late ACK 不重复发布 success
✓ busy + timeout 联合测试
✓ 重新接线后 success 闭环恢复
✓ Telemetry 持续运行
✓ Heartbeat 持续运行
✓ Ctrl+C 正常退出
✓ Git 提交并推送
```

---

## 二十一、当前项目边界

已经完成：

```text
STM32 DHT11
→ UART
→ Linux Gateway
→ MQTT Telemetry
```

以及：

```text
MQTT Command
→ Linux Gateway
→ STM32
→ STM32 ACK
→ Linux 关联
→ MQTT success / failed / timeout
```

仍未完成：

```text
USB-TTL 运行中整体断开
串口 read/write 致命异常恢复
自动重新打开串口
重连后上下行恢复
固定串口路径问题
request_id
```

---

## 二十二、技术面复述

### 1. 为什么 timeout 不能直接叫 failed？

因为：

```text
write 已经成功
```

只能证明数据已经交给串口传输层。

STM32 可能：

```text
已经执行
但 ACK 丢失
```

因此网关只能说：

```text
结果无法确认
```

而不能说：

```text
设备一定执行失败
```

### 2. 为什么使用 monotonic？

因为超时是：

```text
相对时间
```

不应该受到系统时钟调整影响。

### 3. 为什么 timeout 后必须清除 pending？

否则：

```text
pending 永远存在
→ 网关永久 busy
→ 后续所有命令都无法执行
```

### 4. 为什么 malformed ACK 不能清 pending？

因为格式错误的数据不能作为可信事务结果。

### 5. 为什么 mismatched ACK 不能清 pending？

因为必须保证：

```text
请求命令
=
ACK 对应命令
```

否则会发生命令结果串线。

---

## 二十三、Day 58 结论

Day 58 将控制链路从：

```text
只有正常 ACK 才能结束事务
```

升级为：

```text
正常 ACK
→ success / failed

无有效 ACK
→ timeout

异常 ACK
→ 不错误结束事务
```

网关已经能够在 STM32 无响应、ACK 格式错误、命令不匹配或迟到 ACK 的情况下保持状态一致，并在事务结束后继续处理下一条命令。

下一步：

```text
USB-TTL 运行中断开
→ 识别串口失效
→ 清理旧串口
→ 自动重连
→ 恢复上下行
```
