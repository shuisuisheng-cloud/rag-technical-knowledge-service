---
title: Linux-STM32 物联网边缘网关 Day 59 USB-TTL 断开检测与串口自动重连
project: Linux-STM32 物联网边缘网关
system_layer: 通信层 / 数据中枢
document_type: daily_dev_record
status: software_verified
last_updated: 2026-08-01
tags: [Linux, Python, UART, PySerial, MQTT, Reconnect, Threading, FaultRecovery, STM32]
---

# Linux-STM32 物联网边缘网关 — Day 59

## 一、基本信息

- 完成日期：2026-08-01
- 对应计划：补做 2026-07-30 的学习内容
- 学习日：Day 59
- 主题：USB-TTL 运行中断开检测与串口自动重连
- Git 提交：`39a92a5`
- Commit Message：`feat: add serial disconnect recovery and auto reconnect`
- 状态：已推送 `origin/main`
- 最终工作区：clean

---

## 二、问题背景

Day 58 已经实现：

```text
MQTT Command
→ Linux
→ STM32
→ ACK
→ success / failed / timeout
```

但是串口此前只在程序启动时打开一次。

如果程序运行期间拔掉 USB-TTL：

```text
/dev/ttyUSB0 消失
→ readline() 抛出异常
→ 原串口对象失效
```

旧逻辑无法区分：

```text
当前暂时没有串口数据
```

和：

```text
USB-TTL 已经真正断开
```

如果所有异常都简单返回：

```python
None
```

主循环会不断：

```text
使用旧 ser
→ 再次读取
→ 再次异常
→ 再次使用旧 ser
```

结果：

```text
日志不断刷屏
且
永远无法进入真正的重连流程
```

---

## 三、Day 59 目标

完整数据流：

```text
网关正常运行
→ USB-TTL 被拔掉
→ 识别致命串口错误
→ 关闭旧串口对象
→ serial_state["port"] = None

主循环继续运行
→ MQTT 保持运行
→ Heartbeat 保持运行
→ ACK timeout 保持运行

达到重连间隔
→ 尝试重新打开串口

设备还不存在
→ 保持 None
→ 等下一周期

设备重新出现
→ 打开新串口
→ 更新共享 serial_state
→ STM32 Telemetry 恢复
→ MQTT 下行使用新串口
```

---

## 四、为什么原来的 None 不够

原来的：

```text
read_data_from_port()
```

可能因为很多情况返回 `None`：

```text
readline() 超时
空行
UnicodeDecodeError
ser 不存在
SerialException
设备真正断开
```

但是这些情况需要主循环采取不同动作。

例如：

```text
暂时没有数据
→ 保留串口对象

设备已经断开
→ 必须关闭旧对象
→ 进入重连
```

所以不能继续让一个：

```python
None
```

承担所有状态。

---

## 五、串口读取状态常量

新增：

```python
SERIAL_NO_DATA = "SERIAL_NO_DATA"
SERIAL_DATA = "SERIAL_DATA"
SERIAL_DISCONNECTED = "SERIAL_DISCONNECTED"
```

Python 没有 C 语言的：

```c
#define
```

因此使用：

```text
模块级
全大写
不重新赋值
```

的变量表达常量。

---

## 六、read_data_from_port() 新返回契约

统一返回：

```text
(status, data)
```

### SERIAL_NO_DATA

返回：

```python
(SERIAL_NO_DATA, None)
```

适用情况：

```text
readline() 返回 b""
空字符串
当前没有完整数据
UnicodeDecodeError
```

含义：

```text
当前这一轮没有可处理数据
但不能证明串口已经断开
```

---

### SERIAL_DATA

返回：

```python
(SERIAL_DATA, line)
```

例如收到：

```text
b"temperature:24.5\r\n"
```

经过解码与 strip 后：

```text
status = SERIAL_DATA
data = "temperature:24.5"
```

只有这个状态进入：

```text
process_serial_data()
```

---

### SERIAL_DISCONNECTED

返回：

```python
(SERIAL_DISCONNECTED, None)
```

适用情况：

```text
ser is None
SerialException
致命 OSError
```

含义：

```text
当前串口对象已经不能继续使用
```

主循环必须将其废弃。

---

## 七、为什么 UnicodeDecodeError 不是断开

如果收到一行异常字节：

```text
正常串口仍然在线
但
这一行无法 UTF-8 解码
```

这并不等于：

```text
USB-TTL 设备已经消失
```

所以：

```text
UnicodeDecodeError
→ 打印 raw bytes
→ 打印 raw hex
→ 丢弃这一行
→ SERIAL_NO_DATA
→ 保留串口
```

而：

```text
SerialException
OSError
```

才属于需要关闭当前串口对象的致命错误。

---

## 八、主循环统一处理三种状态

概念逻辑：

```text
SERIAL_DATA
→ process_serial_data()

SERIAL_NO_DATA
→ 本轮不处理串口
→ Heartbeat继续
→ ACK timeout继续

SERIAL_DISCONNECTED
→ 关闭旧串口
→ serial_state["port"] = None
→ 等待自动重连
```

这样：

```text
读取层
```

只负责告诉主循环：

```text
发生了什么
```

而：

```text
主循环
```

负责决定：

```text
下一步怎么办
```

---

## 九、为什么需要关闭旧串口对象

不能只写：

```python
ser = None
```

因为：

```text
Python 引用消失
```

不等于：

```text
底层串口资源已经主动释放
```

正确流程：

```text
保存 old_ser
→ 获取 serial_state lock
→ 确认共享 port 仍然是 old_ser
→ close_ser_port(old_ser)
→ serial_state["port"] = None
→ 解锁
```

对象身份检查可以避免：

```text
准备关闭 old_ser
→ 另一线程已经放入 new_ser
→ 主线程却错误关闭 new_ser
```

---

## 十、serial_state 共享状态

新增：

```python
serial_state = {
    "port": None,
    "lock": threading.Lock(),
}
```

### port

表示：

```text
当前有效串口对象
```

不可用时：

```python
None
```

### lock

保护：

```text
串口对象关闭
串口对象替换
MQTT 命令写入
```

---

## 十一、为什么不能只修改 main() 局部变量

错误方案：

```python
ser = new_ser
```

可能产生：

```text
main()
→ 已经使用 new_ser

MQTT userdata
→ 仍然保存 old_ser
```

结果：

```text
STM32 Telemetry 已经恢复
但
MQTT Command 仍然写向旧串口
```

所以必须让：

```text
main 线程
+
Paho MQTT 线程
```

访问同一个：

```python
serial_state
```

重连后只更新：

```python
serial_state["port"] = new_ser
```

而不是重新创建一个全新字典。

---

## 十二、为什么不能重新创建 serial_state

错误：

```python
serial_state = {
    "port": new_ser,
    "lock": threading.Lock(),
}
```

因为 MQTT userdata 可能仍然引用：

```text
旧 serial_state 字典
```

正确：

```text
始终保留同一个字典对象
→ 只修改其中 port 字段
```

这样：

```text
主线程
与
MQTT 回调线程
```

始终看到同一份当前串口状态。

---

## 十三、非阻塞串口重连

新增：

```text
serial_reconnect_interval
last_serial_reconnect_attempt
```

### serial_reconnect_interval

表示：

```text
两次重新打开串口之间的最小间隔
```

### last_serial_reconnect_attempt

记录：

```text
上一次尝试重连时的 monotonic 时间
```

重连条件：

```text
当前不是 Mock 模式
+
serial_state["port"] is None
+
距离上一次重连已经达到 interval
```

---

## 十四、重连数据流

```text
port is None
→ 检查 monotonic 时间差
```

未达到间隔：

```text
什么都不做
→ 主循环继续
```

达到间隔：

```text
先更新 last_serial_reconnect_attempt
→ 尝试一次 open_ser_port()
```

失败：

```text
new_ser is None
→ port 继续保持 None
→ 等待下一次周期
```

成功：

```text
获取 serial_state lock
→ serial_state["port"] = new_ser
→ 解锁
```

---

## 十五、为什么不能使用阻塞 while 重连

错误设计：

```python
while serial_state["port"] is None:
    serial_state["port"] = open_ser_port(...)
```

如果设备一直没有插入：

```text
主线程永远卡在这里
```

造成：

```text
Heartbeat 停止
ACK timeout 停止
其他主循环任务停止
Ctrl+C 响应变差
日志和 CPU 被重连占用
```

正确方案：

```text
主循环每一轮快速检查
→ 到时间只尝试一次
→ 无论成功还是失败都继续其他任务
```

因此重连是：

```text
非阻塞周期重试
```

---

## 十六、重要 Bug：正常状态下重复打开串口

最初重连判断遗漏：

```python
serial_state["port"] is None
```

导致即使串口正常，也会周期性：

```text
重新 open /dev/ttyUSB0
```

可能造成：

```text
重复打开串口
覆盖当前对象
旧对象未关闭
文件描述符泄漏
多重占用
```

最终重连条件必须包含：

```text
serial_state["port"] is None
```

这样：

```text
串口正常
→ 不重连

串口已经失效
→ 才进入重连逻辑
```

---

## 十七、启动时打开失败不能回退 Mock

旧设计：

```text
配置选择真实串口
→ 首次打开失败
→ 自动进入 Mock 模式
```

问题：

```text
USB-TTL 稍后重新出现
→ 程序仍在 Mock
→ 永远不会再恢复真实串口
```

新设计：

```text
配置要求真实串口
→ 首次打开失败
→ port = None
→ use_mock_serial 仍然为 False
→ 主循环等待真实设备重连
```

只有用户配置明确选择：

```text
Mock
```

才进入模拟模式。

---

## 十八、MQTT 回调必须获取最新 port

MQTT 客户端 userdata 保存：

```python
serial_state
```

收到 MQTT 命令时：

```text
on_message()
→ 从 userdata 获取 serial_state
→ 解析命令
→ 准备真正写串口时
→ 获取 serial_state["lock"]
→ 在锁内重新读取 serial_state["port"]
→ 完成一次 write
→ 解锁
```

不能在函数一开始长期缓存：

```python
serial_port = serial_state["port"]
```

因为中间可能发生：

```text
MQTT线程获得 old_ser
→ main线程发现断开
→ main关闭 old_ser
→ port 被替换
→ MQTT线程继续向 old_ser 写
```

---

## 十九、serial_state lock 的真正职责

锁保护的是：

```text
串口对象生命周期
```

例如：

```text
关闭旧对象
替换新对象
命令写入期间保持对象有效
```

不是把：

```text
所有 UART 读写
```

全部串行化。

---

## 二十、为什么 readline() 不长期持锁

当前架构：

```text
主线程
→ UART read

Paho线程
→ UART write
```

串口本身支持双向通信：

```text
STM32 TX → Linux RX
Linux TX → STM32 RX
```

如果：

```text
整个 readline()
```

期间一直持有锁，那么当读取等待超时时：

```text
MQTT 下行也必须等锁
```

因此：

```text
readline 不长期持有 serial_state lock
```

锁主要用于：

```text
close
replace
write
```

之间的生命周期同步。

---

## 二十一、command_state 与 serial_state 两把锁

### command_state["lock"]

保护：

```text
pending_command
pending_since
```

解决：

```text
busy
ACK 匹配
timeout 清理
发送失败回滚
```

### serial_state["lock"]

保护：

```text
当前 port
关闭旧 port
替换新 port
命令 write
```

因此：

```text
command_state
→ 命令事务状态

serial_state
→ 串口资源生命周期
```

两者职责不同。

---

## 二十二、断开期间命令为什么是 failed

当：

```text
serial_state["port"] is None
```

此时收到：

```json
{
  "command": "led_on"
}
```

数据流：

```text
合法命令
→ 准备下发
→ 当前没有可用串口
→ send_command_to_serial() 失败
→ 回滚 pending
→ MQTT failed
```

这里可以明确判断：

```text
命令没有成功交给串口传输层
```

所以使用：

```text
failed
```

---

## 二十三、为什么写入成功后无 ACK 是 timeout

另一种情况：

```text
write() 已经成功
→ 随后线路或设备出现问题
→ 没有收到 ACK
```

STM32：

```text
可能已经收到并执行
```

所以网关不能说：

```text
failed
```

只能说：

```text
timeout
```

即：

```text
规定时间内无法确认结果
```

---

## 二十四、pending 回滚

命令下发前已经登记：

```text
pending_command
pending_since
```

如果随后：

```text
port is None
```

或者：

```text
串口 write 失败
```

则必须：

```text
获取 command_state lock
→ 确认 pending_command 仍属于当前 command
→ pending_command = None
→ pending_since = None
→ MQTT failed
```

否则：

```text
失败命令永久占据 pending
→ 后续所有命令一直 busy
```

---

## 二十五、真实 USB-TTL 热拔出测试

正常运行时：

```text
DHT11 raw
→ temperature
→ MQTT telemetry
→ Heartbeat
```

运行期间拔掉整个 USB-TTL。

网关出现：

```text
device reports readiness to read but returned no data
(device disconnected or multiple access on port?)
```

随后：

```text
串口被关闭
serial_state["port"] = None
```

但：

```text
main.py 没有崩溃
Heartbeat 继续发布
ACK timeout 继续运行
```

证明：

```text
串口子系统故障
没有拖垮整个 Gateway
```

---

## 二十六、重连失败状态

### Errno 2

```text
No such file or directory
```

表示：

```text
/dev/ttyUSB0 当前不存在
```

例如设备还没有重新 attach 到 WSL。

---

### Errno 13

```text
Permission denied
```

表示：

```text
/dev/ttyUSB0 已经存在
但当前用户没有打开权限
```

恢复权限：

```bash
sudo chgrp dialout /dev/ttyUSB0
sudo chmod 660 /dev/ttyUSB0
```

目标权限：

```text
crw-rw---- root dialout ... /dev/ttyUSB0
```

权限恢复后，下一次周期重连：

```text
成功打开 /dev/ttyUSB0
```

随后：

```text
DHT11 raw
temperature
MQTT telemetry
```

重新出现。

---

## 二十七、WSL 中 USB 重新接入仍需外部处理

当前 Python 网关可以：

```text
发现 /dev/ttyUSB0 不存在
→ 周期重试
→ 设备重新出现后自动打开
```

但不能自动完成 Windows 到 WSL 的 USB 挂载。

重新插入后通常仍需要 Windows 管理员 PowerShell：

```powershell
usbipd list
usbipd attach --wsl --busid <实际BUSID>
```

因此：

```text
Gateway 自动重连
```

的边界是：

```text
设备已经重新出现在 WSL
```

之后。

---

## 二十八、断开期间命令测试

串口断开：

```python
serial_state["port"] = None
```

此时发送：

```json
{
  "command": "led_on"
}
```

网关：

```text
收到 MQTT command
→ 当前 port=None
→ send_command_to_serial() 返回 False
→ pending 回滚
→ MQTT failed
```

证明：

```text
断开期间不会写入旧串口
不会永久 pending
不会导致后续一直 busy
```

---

## 二十九、重连后的命令测试

串口重新打开并恢复 DHT11 遥测后：

第一次发送：

```text
led_on
```

曾出现：

```text
command forwarded to serial
→ waiting for STM32 ACK
→ STM32 没有 rx
→ 没有 ACK
→ timeout
```

第二次再次发送：

```text
led_on
```

得到：

```text
rx:led_on
→ ack:led_on:success
→ Linux valid ACK
→ MQTT success
```

这个现象证明：

```text
共享 serial_state 已经生效
MQTT 确实使用了重连后的新串口
timeout 能正确结束没有 ACK 的事务
后续事务仍然可以成功
```

但同时暴露：

```text
STM32 重连后的第一条下行命令
仍可能不可靠
```

这个问题需要 STM32 侧继续处理 UART 接收错误恢复。

---

## 三十、为什么 Telemetry 恢复不代表 Command 恢复

DHT11 遥测验证：

```text
STM32 TX
→ USB-TTL RX
→ Linux
```

这是：

```text
上行方向
```

而命令依赖：

```text
Linux
→ USB-TTL TX
→ STM32 RX
```

还依赖：

```text
STM32 USART2 中断接收链正常
```

因此：

```text
Telemetry 已经恢复
```

不能单独证明：

```text
Command + ACK 闭环完全恢复
```

---

## 三十一、完整自动重连数据流

```text
正常运行
→ read_data_from_port(current_port)
```

正常数据：

```text
SERIAL_DATA
→ process_serial_data()
```

暂时无数据：

```text
SERIAL_NO_DATA
→ 主循环继续
```

USB-TTL 拔出：

```text
SerialException / OSError
→ SERIAL_DISCONNECTED
→ 关闭 old_ser
→ serial_state["port"] = None
```

随后：

```text
MQTT继续
Heartbeat继续
ACK timeout继续
```

达到重连时间：

```text
open_ser_port(configured_port)
```

设备不存在：

```text
Errno 2
→ 保持 None
```

权限不足：

```text
Errno 13
→ 保持 None
```

设备存在且权限正常：

```text
open 成功
→ new_ser
→ serial_state["port"] = new_ser
```

随后：

```text
使用 new_ser 读取
→ Telemetry 恢复
```

下一条 MQTT Command：

```text
on_message()
→ 获取同一个 serial_state
→ 锁内取得 new_ser
→ 命令写入 STM32
```

---

## 三十二、Day 59 验收结果

```text
✓ SERIAL_NO_DATA / DATA / DISCONNECTED 状态区分
✓ UnicodeDecodeError 不误判设备断开
✓ SerialException 识别
✓ OSError 识别
✓ 断开后关闭旧端口
✓ 断开后共享 port 清空
✓ 不重复使用坏串口对象
✓ 网关进程不崩溃
✓ Heartbeat 在断联期间继续运行
✓ ACK timeout 在断联期间继续运行
✓ 非阻塞周期重连
✓ 串口正常时不重复 open
✓ 启动失败后继续等待真实串口
✓ 不再自动回退 Mock
✓ Errno 2 验证
✓ Errno 13 验证
✓ 权限恢复后自动重连
✓ DHT11 Telemetry 自动恢复
✓ MQTT 回调共享 serial_state
✓ MQTT 下行使用最新 port
✓ close / replace / write 使用统一串口锁
✓ 断开期间命令 failed
✓ write 成功但没有 ACK 时 timeout
✓ timeout 后 pending 清空
✓ 后续命令可以 success
✓ Ctrl+C 正常退出
✓ py_compile 通过
✓ git diff --check 通过
✓ Commit / Push 完成
```

---

## 三十三、当前已知限制

### 1. 串口路径仍然固定

当前主要尝试：

```text
/dev/ttyUSB0
```

如果设备重新枚举为：

```text
/dev/ttyUSB1
```

无法自动发现。

未来可以根据：

```text
VID
PID
USB serial number
设备描述
```

定位目标设备。

### 2. usbipd attach 仍需 Windows 外部操作

网关暂时不能自动完成：

```text
Windows USB
→ WSL USB
```

的设备挂载。

### 3. WSL 串口权限可能需要手动恢复

重新 attach 后可能需要：

```bash
sudo chgrp dialout /dev/ttyUSB0
sudo chmod 660 /dev/ttyUSB0
```

### 4. 尚无串口状态 MQTT Topic

目前没有独立发布：

```text
serial_connected
serial_disconnected
serial_reconnecting
```

### 5. 重连后第一条 STM32 命令仍可能 timeout

网关已经能够正确：

```text
无 ACK
→ timeout
→ 清空 pending
```

但设备侧还需要补 UART 硬件错误恢复。

### 6. 没有 request_id

当前仍是：

```text
单 pending 模型
```

一次只允许一个等待 ACK 的命令。

迟到 ACK 与新的同名命令之间仍存在关联歧义。

---

## 三十四、技术面复述

### 1. 为什么不能让 None 同时表示无数据和断开？

因为处理策略不同：

```text
无数据
→ 保留当前串口

断开
→ 废弃当前串口
→ 进入重连
```

### 2. 为什么自动重连不能使用阻塞 while？

因为会停止：

```text
Heartbeat
ACK timeout
主循环其他任务
Ctrl+C
```

### 3. 为什么需要 serial_state？

因为：

```text
main线程
与
MQTT线程
```

都需要访问当前串口，而重连后串口对象会发生变化。

### 4. 为什么需要 serial_state["lock"]？

为了避免：

```text
主线程正在 close / replace port
MQTT线程同时执行 write
```

### 5. 为什么断开期间命令直接 failed？

因为命令尚未成功写入串口，网关可以确定传输阶段失败。

### 6. 为什么 write 成功后没有 ACK 是 timeout？

因为设备可能已经执行，只是结果无法确认。

### 7. 为什么 DHT11 恢复不代表命令完全恢复？

因为 DHT11 只验证 STM32 → Linux 上行；Command 还依赖 Linux → STM32 下行和 STM32 UART RX 状态。

---

## 三十五、Day 59 完成边界

Day 59 已完成：

```text
串口断开检测
旧串口对象清理
共享串口状态
非阻塞周期重连
重连后新串口替换
MQTT线程使用新串口
断开期间 failed
等待 ACK 期间 timeout
Telemetry 恢复
后续命令恢复
```

Day 59 未完成：

```text
VID / PID 自动寻找设备
自动 usbipd attach
自动恢复 WSL 权限
串口状态 MQTT Topic
STM32 UART 硬件错误恢复
request_id
```

---

## 三十六、下一步

先进入 STM32 侧：

```text
HAL_UART_ErrorCallback()
→ 识别 ORE / FE / NE
→ 当前行标记损坏
→ 清理接收状态
→ 必要时重新启动 HAL_UART_Receive_IT()
```

随后回到 Linux Gateway Day 60：

```text
完整系统集成测试
→ MQTT
→ UART
→ STM32
→ ACK
→ timeout
→ USB-TTL断开恢复
→ STM32 RESET
→ Broker断开恢复
→ Heartbeat
→ LWT
→ Ctrl+C
```

---

## 三十七、Day 59 结论

Day 59 将网关从：

```text
串口只在程序启动时打开一次
→ 运行中断开后必须重启程序
```

升级为：

```text
运行中识别 USB-TTL 断开
→ 安全关闭旧对象
→ Gateway 其他功能继续运行
→ 周期性非阻塞重连
→ 新串口替换共享状态
→ Telemetry 恢复
→ MQTT 下行使用新串口
```

这标志着 Linux-STM32 物联网边缘网关已经具备基础的串口链路自恢复能力。
