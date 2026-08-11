---
title: Linux-STM32 物联网边缘网关 Day 60 完整系统集成测试
project: Linux-STM32 物联网边缘网关
system_layer: 通信层 / 数据中枢
document_type: daily_dev_record
status: verified
last_updated: 2026-08-11
tags: [Linux, Python, MQTT, STM32, UART, ACK, Timeout, Reconnect, LWT, IntegrationTest]
---

# Linux-STM32 物联网边缘网关 — Day 60

## 一、基本信息

- 日期：2026-08-11
- 学习日：Day 60
- 主题：STM32 + Linux 网关完整系统集成测试
- 阶段：Gateway V1 功能集成收口
- 状态：V1 功能层冻结，下一阶段进入技术验收

---

## 二、Day 60 背景

Day 59 已经完成：

```text
USB-TTL 运行中断开检测
→ 旧串口对象清理
→ 非阻塞周期重连
→ serial_state 共享串口状态
→ MQTT 下行使用重连后的新串口
```

同时已经具备：

```text
串口断开期间命令
→ failed

命令已经成功写入
但没有收到 ACK
→ timeout
```

Day 60 不再继续堆新功能，而是验证：

```text
真实 STM32
+
真实 UART
+
Linux Gateway
+
MQTT Broker
+
真实 ACK
+
异常恢复
```

能否作为一个完整系统稳定工作。

---

## 三、Day 60 完整测试目标

```text
串口
+
MQTT
+
ACK
+
timeout
+
STM32 RESET
+
USB-TTL 断开恢复
+
Broker 断开恢复
+
LWT
+
Ctrl+C
```

必须形成完整的系统级闭环。

---

## 四、Day 59 暴露的跨端问题

此前真实测试出现：

```text
USB-TTL 重新连接
→ STM32 DHT11 上行恢复
→ Linux 下发第一条 led_on
→ write 成功
→ STM32 没有 rx
→ 没有 ACK
→ Gateway timeout

再次发送第二条命令
→ 才正常成功
```

这说明：

```text
Telemetry 恢复
≠
UART 下行协议状态已经完全恢复
```

结合 STM32 Day 12 后确认原因：

```text
UART 发生硬件错误
→ STM32 将 uart2_line_invalid 置 1
→ 当前损坏行持续丢弃
→ 必须收到下一个 '\n'
→ 才恢复合法命令行
```

如果 Gateway 重连后直接发送：

```text
led_on\r\n
```

这一整条业务命令可能只是：

```text
用于结束 STM32 上一条 invalid 残行
```

于是：

```text
第一条业务命令被丢弃
→ 没有 ACK
→ Gateway timeout
```

---

## 五、新增串口协议边界同步

新增：

```text
sync_serial_protocol_boundary(ser)
```

职责：

```text
输入：
已经成功打开
但尚未公开给业务线程的串口对象

发送：
b"\r\n"
```

成功条件：

```text
ser 有效
→ port 已打开
→ write 完整写入
→ flush 成功
```

返回：

```text
True / False
```

这个函数不负责：

```text
pending_command
pending_since
MQTT ACK
STM32 ACK
自动重连
关闭串口
```

因为：

```text
\r\n
```

不是业务命令，而是协议同步边界。

---

## 六、为什么发送 \r\n

STM32 当前行协议：

```text
\r
→ 忽略

\n
→ 一行结束
```

UART 硬件错误后：

```text
uart2_line_invalid = 1
```

普通字符会：

```text
继续丢弃
```

直到：

```text
收到 '\n'
→ 清除 invalid
→ 下一行重新开始
```

所以 Gateway 在建立一个新的串口通信会话后：

```text
打开串口
→ 发送 \r\n
→ STM32 结束可能残留的 invalid 行
→ 不产生业务命令
→ 不产生 ACK
→ 下一条业务命令从干净边界开始
```

如果 STM32 当时本来就没有处于 invalid 状态：

```text
\r\n
```

也只会形成一个空行。

STM32 Day 11 已经保证：

```text
空行
→ 忽略
→ 不执行命令
```

因此该同步操作是安全的。

---

## 七、为什么新串口不能先公开再同步

错误流程：

```text
open_ser_port()
→ serial_state["port"] = new_ser
→ 再发送同步 \r\n
```

会存在竞争窗口：

```text
main 线程公开 new_ser
→ MQTT 线程立即取得 new_ser
→ MQTT 发送 led_on
→ 此时协议同步尚未完成
```

因此采用：

```text
candidate_ser
```

概念。

正确流程：

```text
open
→ 得到 candidate_ser

candidate_ser
→ 只由 main 线程持有
→ 暂时不放入 serial_state

执行协议同步

同步成功
→ serial_state["port"] = candidate_ser
→ 变成 active port
```

即：

```text
Candidate Port
→ 已打开
→ 但业务不可使用

Active Port
→ 打开成功
→ 协议同步成功
→ 可以供 MQTT 业务线程使用
```

---

## 八、同步失败处理

同步过程可能发生：

```text
write timeout
SerialException
OSError
不完整 write
flush 失败
```

此时：

```text
sync 返回 False
→ close candidate_ser
→ serial_state["port"] 保持 None
→ 不创建 pending
→ 不等待 ACK
→ 不发布业务 MQTT ACK
→ 等待下一轮重连
```

不能把：

```text
尚未完成初始化的串口
```

标记为：

```text
可用
```

---

## 九、首次启动串口流程

首次真实串口启动：

```text
candidate_ser = open_ser_port()
```

打开失败：

```text
port = None
→ Gateway 继续运行
→ 等待后续重连
```

打开成功：

```text
candidate_ser
→ sync_serial_protocol_boundary()
```

同步失败：

```text
close candidate_ser
→ port = None
```

同步成功：

```text
serial_state["port"] = candidate_ser
```

首次启动阶段 MQTT 网络线程尚未启动，因此：

```text
candidate_ser 同步过程中
不存在 MQTT 业务并发
```

---

## 十、自动重连串口流程

自动重连条件：

```text
真实串口模式
+
serial_state["port"] is None
+
达到 reconnect interval
```

随后：

```text
open new_ser
→ new_ser 暂时是 Candidate Port
→ 发送 \r\n
```

同步失败：

```text
close new_ser
→ port 保持 None
```

同步成功：

```text
获取 serial_state["lock"]
→ serial_state["port"] = new_ser
→ 释放锁
```

因此 MQTT 线程只能访问：

```text
已经完成协议同步的新串口
```

---

## 十一、STM32 RESET 恢复测试

测试：

```text
USB-TTL 保持连接
→ Gateway 保持运行
→ 按下 STM32 RESET
```

STM32 重新启动后输出：

```text
board:STM32F407VET6_CORE_BOARD_V2
STM32 Environment Terminal V2 boot OK
DHT11 idle level: 1
```

随后：

```text
DHT11 遥测自动恢复
```

Gateway 没有出现：

```text
SERIAL_DISCONNECTED
→ close
→ reopen ttyUSB
```

说明：

```text
STM32 MCU RESET
≠
USB 串口设备断开
```

随后第一条：

```text
led_on
→ rx:led_on
→ ack:led_on:success
→ MQTT success
```

第二条：

```text
led_off
→ success
```

验证：

```text
✓ RESET 不误触发 Linux 串口重连
✓ STM32 启动后 USART2 RX 恢复
✓ DHT11 恢复
✓ RESET 后第一条业务命令成功
```

---

## 十二、ACK Timeout 回归测试

测试方式：

保持下行：

```text
Linux
→ USB-TTL TX
→ STM32 RX
```

断开上行：

```text
STM32 TX
-X-
USB-TTL RX
→ Linux
```

发送：

```text
led_on
```

Gateway：

```text
command forwarded to serial
→ waiting for STM32 ack
```

STM32 可能已经执行命令，但是 Gateway 收不到 ACK。

达到 timeout：

```text
led_on is timeout
```

MQTT：

```json
{
  "command": "led_on",
  "status": "timeout"
}
```

重新接回 STM32 TX，不重启程序。

发送：

```text
led_off
```

得到：

```text
rx:led_off
→ ack:led_off:success
→ MQTT success
```

验证：

```text
✓ Day 58 timeout 没有退化
✓ timeout 后 pending 清理
✓ 后续命令不 busy
✓ write 成功仍然不能等价于执行结果确认
```

---

## 十三、USB-TTL 断开恢复测试

累计进行了至少三轮真实恢复：

```text
正常运行
→ 拔出 USB-TTL
→ Gateway 判断 SERIAL_DISCONNECTED
→ 关闭旧串口
→ serial_state["port"] = None
```

同时：

```text
MQTT 继续
Heartbeat 继续
Gateway main 不退出
```

重新插入：

```text
Windows USB 插入
→ usbipd attach
→ 恢复 dialout 权限
→ Gateway 周期重连
→ open 新串口
→ 自动发送 \r\n
→ STM32 协议边界同步
→ DHT11 恢复
```

随后第一条：

```text
led_on / led_off
```

三轮都直接得到：

```text
rx
→ ACK
→ MQTT success
```

不再出现 Day 59 中：

```text
重连后第一条命令 timeout
→ 第二条才成功
```

的问题。

---

## 十四、Broker 断开恢复

停止 Mosquitto 后：

```text
MQTT Broker 断开
→ MQTT 网络暂时不可用
```

但是：

```text
Gateway main 继续运行
→ STM32 UART 继续读取
```

说明：

```text
MQTT 子系统故障
≠
整个 Gateway 故障
```

这是故障隔离：

```text
一个子系统失败
→ 不传播到串口子系统
```

Broker 恢复后：

```text
Paho 后台线程
→ 自动重新连接
→ on_connect()
→ 重新订阅 command Topic
→ 重新发布 online retained 状态
```

随后：

```text
led_on
led_off
→ STM32 真实执行
→ ACK success
```

---

## 十五、MQTT 自动重连机制

当前依赖：

```text
connect_async()
loop_start()
reconnect_delay_set()
```

### connect_async()

```text
异步发起 MQTT 连接
→ main 线程不等待 Broker
```

### loop_start()

```text
启动 Paho 后台网络线程
→ 负责 MQTT 网络收发和 callback
```

### reconnect_delay_set()

```text
设置自动重连退避时间
```

Broker 恢复后再次触发：

```text
on_connect()
```

然后：

```text
重新 subscribe command
→ 重新 publish retained online
```

---

## 十六、LWT 异常退出测试

先订阅：

```text
edgeaiot/gateway/linux_stm32_gateway_01/status
```

找到：

```text
python main.py
```

对应 PID。

执行：

```bash
kill -9 <PID>
```

`SIGKILL` 无法让 Python 执行：

```text
KeyboardInterrupt
finally
graceful_shutdown
disconnect
```

因此 Gateway 无法主动发布 offline。

Broker 检测到客户端异常消失后，根据预注册 LWT 自动发布：

```json
{
  "status": "offline",
  "reason": "unexpected_disconnect"
}
```

新的订阅者也可以立即得到：

```text
offline / unexpected_disconnect
```

证明：

```text
✓ LWT 生效
✓ LWT retained 生效
```

---

## 十七、LWT 恢复

重新启动 Gateway：

```text
打开串口
→ 串口协议同步
→ MQTT 连接
→ on_connect()
```

随后发布 retained：

```json
{
  "status": "online",
  "reason": "connected"
}
```

覆盖之前的：

```json
{
  "status": "offline",
  "reason": "unexpected_disconnect"
}
```

之后新订阅者得到：

```text
online / connected
```

说明：

```text
Broker 中保留的网关状态
最终能重新与真实 Gateway 状态一致
```

---

## 十八、正常退出与异常退出

### Ctrl+C

```text
KeyboardInterrupt
→ finally
→ graceful_shutdown
→ 主动发布 offline
→ reason=graceful_shutdown
→ MQTT 正常 disconnect
```

### kill -9

```text
Python 无法进入 finally
→ 无法主动发布 offline
→ Broker 通过 LWT 发布
→ reason=unexpected_disconnect
```

所以系统能够区分：

```text
正常退出
```

和：

```text
异常崩溃
```

---

## 十九、Day 60 验证矩阵

```text
✓ 首次串口打开协议同步
✓ 自动重连协议同步
✓ 同步空行不创建 pending
✓ 同步空行不等待 ACK
✓ 同步空行不产生业务 ACK

✓ DHT11 正常 Telemetry
✓ led_on success
✓ led_off success

✓ STM32 RESET 恢复
✓ RESET 后第一条命令成功

✓ ACK timeout
✓ timeout 后 pending 清理
✓ timeout 后下一条命令成功

✓ USB-TTL 断开检测
✓ 旧串口对象清理
✓ Heartbeat 保持
✓ 断联期间命令 failed
✓ 非阻塞自动重连
✓ 三轮重连后第一条业务命令成功

✓ Broker 断开
✓ UART 子系统继续运行
✓ Broker 恢复
✓ Paho 自动重连
✓ command Topic 重新订阅
✓ 下行命令恢复

✓ kill -9
✓ LWT unexpected_disconnect
✓ LWT retain
✓ Gateway 重启后 online 覆盖 offline

✓ Ctrl+C graceful_shutdown
✓ 正常 MQTT disconnect
```

---

## 二十、当前 V1 已知限制

当前仍保留：

```text
1. 单 pending 模型
2. 没有 request_id
3. 迟到 ACK 与新同名命令仍存在关联歧义
4. 串口仍以固定设备路径为主
5. usbipd attach 依赖 Windows 外部操作
6. WSL 串口权限可能需要人工恢复
7. 暂无完整多设备支持
8. 尚未实现生产级持久化发送队列
```

这些问题不继续塞入 Day 60。

后续：

```text
V1 技术面验收
→ 判断哪些属于 V1 必须修复
→ 其余进入 V2 工程化升级
```

---

## 二十一、V1 最终数据流

### Telemetry

```text
STM32 DHT11
→ USART2
→ USB-TTL
→ Linux Gateway
→ 数据解析
→ MQTT Telemetry
```

### Command

```text
MQTT Command
→ Linux Gateway
→ UART
→ STM32
→ LED 真实执行
→ STM32 ACK
→ Linux ACK 匹配
→ MQTT success / failed / timeout
```

### Serial Failure

```text
USB-TTL 拔出
→ SERIAL_DISCONNECTED
→ close old port
→ port=None
→ Gateway 其他子系统继续
→ 周期性 reconnect
→ Candidate Port
→ \r\n 协议同步
→ Active Port
→ Telemetry / Command 恢复
```

### MQTT Failure

```text
Broker 断开
→ UART 子系统继续
→ Paho 自动重连
→ on_connect
→ resubscribe
→ online retained
→ Command 恢复
```

---

## 二十二、Day 60 结论

Day 60 将系统从：

```text
各个功能模块分别能工作
```

提升为：

```text
真实 STM32
+
真实 UART
+
Linux Gateway
+
MQTT Broker
+
真实 ACK
+
异常恢复
```

经过完整系统集成验证的 V1。

目前 Gateway 已具备：

```text
真实遥测
真实下行
设备 ACK
ACK timeout
USB 串口故障恢复
STM32 RESET 恢复
Broker 故障恢复
Heartbeat
LWT
Retained Status
正常退出状态
异常退出状态
协议边界重新同步
```

Day 60 完成后：

```text
Linux-STM32 物联网边缘网关
V1 功能开发正式冻结
```

下一阶段：

```text
V1 技术面验收
```
