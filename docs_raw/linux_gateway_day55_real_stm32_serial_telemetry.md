---
title: Linux-STM32 物联网边缘网关 Day 55 真实 STM32 串口遥测上行联调
project: Linux-STM32 物联网边缘网关
system_layer: 通信层 / 数据中枢
document_type: software_module_record
status: software_verified
last_updated: 2026-07-19
tags: [Linux, Python, WSL, PySerial, STM32, USART2, MQTT, Telemetry, USBIPD, CH340]
---

# Linux-STM32 物联网边缘网关 Day 55 真实 STM32 串口遥测上行联调

## 今日目标

将 Day 54 已经完成的软件主循环接入真实 STM32，打通真实遥测上行链路：

```text
STM32 DHT11
→ USART2
→ CH340 USB-TTL
→ WSL 串口设备
→ Python 串口读取
→ 协议分类与解析
→ JSON Payload
→ MQTT Telemetry
```

## 今日结果

最终完整通过：

```text
真实 DHT11 温度
→ STM32 USART2 输出
→ Linux 网关持续读取
→ 合法温度解析
→ JSON Payload
→ MQTT Telemetry 发布
```

本日标志着项目从：

```text
Mock 串口数据验证
```

进入：

```text
真实 STM32 硬件遥测上行
```

## STM32 串口输出分类

STM32 当前通过同一个 USART2 同时输出：

```text
遥测协议帧
调试日志
错误或损坏协议帧
```

因此 Linux 网关不能把每一行串口文本都直接当作遥测解析。

## 合法遥测协议帧

格式：

```text
temperature:<value>
```

示例：

```text
temperature:25.4
```

处理流程：

```text
识别 temperature: 前缀
→ 检查字段数量
→ 将数值转换为 float
→ handle_valid_data()
→ 生成 JSON Payload
→ 发布 MQTT Telemetry
```

## 损坏的温度协议帧

示例：

```text
temperature:
temperature:abc
temperature:26.4:extra
```

这些数据属于温度协议，但协议内容不合法。

处理流程：

```text
识别为 temperature 协议
→ 结构或数值校验失败
→ handle_invalid_data()
→ 记录非法数据日志
→ 返回 None
→ 不发布 MQTT
```

## STM32 调试日志

示例：

```text
DHT11 raw: 43 0 25 4 72
board:STM32F407VET6_CORE_BOARD_V2
STM32 Environment Terminal V2 boot OK
DHT11 idle level: 1
DHT11 response: TIMEOUT
KEY PRESSED
```

处理流程：

```text
不是 temperature 协议
→ handle_debug_data()
→ 输出 STM32 debug 日志
→ 返回 None
→ 不记录为非法遥测
→ 不发布 MQTT
```

## 三类数据的完整分类

```text
串口行
  ↓
是否属于 temperature 协议？
  ├─ 否
  │   → Debug
  │   → 仅打印或记录
  │
  └─ 是
      ↓
     结构和数值是否合法？
       ├─ 否
       │   → Invalid
       │   → 记录非法协议
       │
       └─ 是
           → Valid
           → JSON
           → MQTT
```

## 为什么必须先分类再解析

错误做法：

```python
parts = serial_data.split(":")
temperature = float(parts[1])
```

如果所有串口行都直接进入这段逻辑，那么：

```text
DHT11 raw: 43 0 25 4 72
```

也会被错误地当成温度协议解析。

正确原则：

```text
先判断“这是不是我的协议”
再判断“协议内容是否正确”
```

必须区分：

```text
不是协议帧
≠
损坏的协议帧
```

## Windows 与 WSL 串口设备关系

Windows 识别 CH340 后，显示为：

```text
COM11
```

WSL 中对应的 Linux 串口设备可能是：

```text
/dev/ttyUSB0
```

它们是同一个物理 USB-TTL 在不同操作系统中的不同表示。

完整链路：

```text
CH340 物理 USB 设备
→ Windows USB 驱动
→ Windows COM 设备
→ usbipd-win
→ USB/IP
→ WSL 虚拟 USB Host
→ Linux usbserial
→ ch341 驱动
→ /dev/ttyUSB*
```

## BUSID、COM 和 ttyUSB 不能写死

以下信息都可能发生变化：

```text
BUSID
Windows COM 编号
/dev/ttyUSB 编号
```

变化原因包括：

- 更换 USB 接口；
- 设备重新插拔；
- Windows 重新枚举；
- 同时连接其他 USB 串口设备；
- WSL 重启。

正确做法是每次联调前查询真实状态。

## Windows 侧 usbipd 流程

管理员 PowerShell：

```powershell
usbipd list
```

找到实际的 CH340 设备和 BUSID。

首次共享或设备已被取消共享时：

```powershell
usbipd bind --busid <实际BUSID>
```

若存在 USB 过滤驱动兼容问题，可根据实际情况使用：

```powershell
usbipd bind --busid <实际BUSID> --force
```

将设备连接到 WSL：

```powershell
usbipd attach --wsl --busid <实际BUSID>
```

再次检查：

```powershell
usbipd list
```

状态应为：

```text
Attached
```

## bind 与 attach 的区别

```text
bind
→ 允许物理 USB 设备被 usbipd 共享

attach
→ 将已经共享的 USB 设备连接到当前 WSL
```

状态变化：

```text
Not shared
→ Shared
→ Attached
```

## Linux 驱动与设备节点

进入 WSL 后检查：

```bash
ls -l /dev/ttyUSB* /dev/ttyACM* 2>/dev/null
```

如果 USB 已经 Attached，但没有出现设备节点，可以检查：

```bash
sudo dmesg | tail -n 50
```

必要时加载 CH340/CH341 驱动：

```bash
sudo modprobe ch341
```

正常内核日志可能包括：

```text
vhci_hcd: Device attached
usbserial: USB Serial support registered
ch341-uart converter detected
ch341-uart converter now attached to ttyUSB0
```

各层职责：

```text
vhci_hcd
→ WSL 虚拟 USB Host 收到设备

usbserial
→ Linux USB 串口通用框架

ch341
→ 识别 CH340/CH341 转换芯片

ttyUSB0
→ Linux 创建可供用户程序访问的字符设备
```

## 串口权限

检查：

```bash
ls -l /dev/ttyUSB0
```

理想权限：

```text
crw-rw---- 1 root dialout ... /dev/ttyUSB0
```

含义：

```text
c
→ 字符设备

root
→ 设备所有者

dialout
→ 串口设备所属组

660
→ root 与 dialout 组可以读写
```

将当前用户加入 `dialout`：

```bash
sudo usermod -aG dialout $USER
```

用户组变化通常需要重新登录或重启 WSL 才能完整生效。

必要时调整当前设备节点：

```bash
sudo chgrp dialout /dev/ttyUSB0
sudo chmod 660 /dev/ttyUSB0
```

不推荐长期使用：

```bash
sudo chmod 666 /dev/ttyUSB0
```

因为它允许所有用户读写串口设备。

## PySerial 验证流程

进入网关项目：

```bash
cd ~/projects/mqtt-iot-gateway
source .venv/bin/activate
```

枚举串口：

```bash
python -m serial.tools.list_ports -v
```

这只能证明 PySerial 能发现设备，不能证明串口通信参数和接线正确。

观察原始串口：

```bash
python -m serial.tools.miniterm /dev/ttyUSB0 115200
```

实际看到：

```text
DHT11 raw: 43 0 25 4 72
temperature:25.4
```

说明：

```text
STM32 PA2 TX → CH340 RX 接线正确
GND 共地正确
USART2 波特率 115200 正确
8N1 参数正确
STM32 固件正常运行
WSL 串口读取正常
```

退出 miniterm：

```text
Ctrl+]
```

退出后再启动网关，避免两个程序同时占用串口。

## 网关真实配置

```json
{
  "use_real_serial": true,
  "port": "/dev/ttyUSB0",
  "baudrate": 115200,
  "mqtt_enabled": true
}
```

设备路径必须以实际枚举结果为准。

## 真实运行结果

网关持续收到：

```text
stm32 debug: DHT11 raw: 42 0 25 3 70
valid data: device: stm32_node_01 temperature: 25.3
mqtt message published: edgeaiot/stm32_node_01/telemetry
```

MQTT 订阅端收到：

```json
{
  "device": "stm32_node_01",
  "temperature": 25.3,
  "status": "normal",
  "timestamp": "2026-07-19 21:29:08",
  "temperature_threshold": 30
}
```

## STM32 复位恢复测试

网关运行期间按下 STM32 复位键。

STM32 重新输出：

```text
board:STM32F407VET6_CORE_BOARD_V2
STM32 Environment Terminal V2 boot OK
DHT11 idle level: 1
```

网关处理结果：

```text
启动日志
→ Debug

后续 temperature
→ Valid
→ JSON
→ MQTT
```

网关没有退出，也不需要重新打开串口。

这证明：

```text
STM32 软件重启
不会破坏 Linux 已建立的 USB 串口连接
```

前提是 USB-TTL 本身没有被拔出。

## 故障定位顺序

真实串口没有数据时，应按层排查：

```text
第一层：Windows 是否识别设备？
→ 设备管理器 / COM 设备

第二层：USB 是否交给 WSL？
→ usbipd list
→ Attached

第三层：Linux 内核是否收到设备？
→ dmesg
→ vhci_hcd

第四层：驱动是否识别芯片？
→ ch341-uart converter detected

第五层：是否创建设备节点？
→ /dev/ttyUSB*

第六层：当前用户是否有权限？
→ root:dialout
→ 660

第七层：PySerial 是否能打开？
→ list_ports
→ miniterm

第八层：原始串口数据是否正确？
→ 波特率
→ 8N1
→ TX/RX
→ 共地

第九层：协议分类是否正确？
→ Debug / Invalid / Valid

第十层：MQTT 是否正常？
→ Telemetry Topic 订阅验证
```

不能一看到 `main.py` 没数据，就直接修改 Python 解析代码。

## Day 55 验收结果

```text
✓ 温度协议、损坏协议和调试日志完成分类
✓ STM32 调试日志不再被当作非法遥测
✓ 损坏的 temperature 帧仍会记录 Invalid
✓ Windows 正确识别 CH340
✓ CH340 成功 bind 和 attach 到 WSL
✓ ch341 驱动成功加载
✓ /dev/ttyUSB* 成功创建
✓ dialout 权限问题解决
✓ PySerial list_ports 成功
✓ miniterm 成功读取 STM32 原始输出
✓ 真实 DHT11 温度持续进入网关
✓ 真实温度成功转换为 JSON
✓ 真实 Telemetry 持续发布到 MQTT
✓ Heartbeat 同时正常运行
✓ STM32 复位后数据自动恢复
```

## 当前边界

已完成：

```text
STM32
→ Linux 串口
→ 数据分类与解析
→ MQTT Telemetry
```

尚未完成：

```text
MQTT Command
→ Linux 网关
→ 串口下发 STM32
→ STM32 执行
→ STM32 返回 ACK
→ Linux 发布 MQTT ACK
```

还未处理：

- USB-TTL 运行中拔出；
- 串口自动重新连接；
- 下行命令；
- 真实设备执行 ACK；
- 完整上下行集成测试。

## 面试表达

我在 WSL 2 中完成了 STM32 与 Linux 网关的真实串口联调。

Windows 将 CH340 识别为 COM 设备，再通过 usbipd-win 将物理 USB 设备附加到 WSL。WSL 内核通过 vhci_hcd、usbserial 和 ch341 驱动创建设备节点 `/dev/ttyUSB*`。

我先使用 `dmesg`、设备权限和 PySerial 工具逐层确认底层链路，再启动业务程序。网关不会把所有串口行都当成遥测，而是先区分合法温度协议、损坏协议和 STM32 调试日志。

最终真实 DHT11 温度能够转换为 JSON 并持续发布到 MQTT Telemetry Topic，STM32 软件复位后链路也能自动恢复。

## 后续计划

```text
MQTT Command
→ Linux 网关
→ USART2 下发 STM32
```

同时继续验证：

- BUSID 与设备节点动态变化；
- 串口发送超时；
- STM32 命令接收；
- 上下行并行运行。
