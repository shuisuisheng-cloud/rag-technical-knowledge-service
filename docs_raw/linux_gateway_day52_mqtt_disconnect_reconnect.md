---
title: Linux-STM32 物联网边缘网关 Day 52 运行期间 MQTT 断线检测与自动重连
project: Linux-STM32 物联网边缘网关
system_layer: 通信层 / 数据中枢
document_type: software_module_record
status: software_verified
last_updated: 2026-07-10
tags: [Linux, Python, MQTT, Paho, Disconnect, AutoReconnect, ExponentialBackoff, Heartbeat]
---

# Linux-STM32 物联网边缘网关 Day 52 运行期间 MQTT 断线检测与自动重连

## 今日目标

Day 52 解决的场景是：

```text
网关已经成功连接 MQTT Broker
→ 网关正在正常运行
→ Broker 在运行期间突然停止
→ MQTT 连接异常中断
→ 网关主进程不能退出
→ Paho 后台线程自动重连
→ Broker 恢复后重新建立完整业务链路
```

今天处理的是：

```text
已经建立连接后的运行期间异常断线
```

暂时没有处理：

```text
程序启动时 Broker 就不存在
```

首次连接失败场景将在 Day 53 单独解决。

## 今日完成的功能

今天完成：

1. 新增 `on_disconnect()` 回调；
2. 使用 Callback API VERSION2 的断线回调参数；
3. 区分正常断开与异常断开；
4. 输出真实 `reason_code`；
5. 在 MQTT Client 上注册断线回调；
6. 在 `config.json` 中增加最小和最大重连等待时间；
7. 将重连配置从 `main.py` 传入 `mqtt_client.py`；
8. 使用 `reconnect_delay_set()` 配置指数退避；
9. 断线期间跳过 Heartbeat 发布；
10. Broker 恢复后自动重连；
11. 重连成功后重新执行 `on_connect()`；
12. 自动恢复 Command Topic 订阅；
13. 自动重新发布 Retained Online Status；
14. 恢复 Command、ACK 和 Heartbeat 链路；
15. 保持 Ctrl+C 正常退出能力。

## 运行期间断线流程

正常运行时：

```text
Linux Gateway
→ Paho MQTT Client
→ Mosquitto Broker
```

Broker 突然停止后：

```text
TCP/MQTT 连接丢失
→ Paho 网络线程检测异常
→ 自动调用 on_disconnect()
→ 网关记录异常断线原因
→ Python 主进程继续运行
→ Paho 后台线程按照退避间隔尝试重连
```

Broker 恢复后：

```text
Paho 重新建立连接
→ Broker 返回 CONNACK
→ Paho 再次调用 on_connect()
→ 重新订阅 Command Topic
→ 重新发布 Retained Online Status
→ Heartbeat 恢复
→ Command 和 ACK 恢复
```

## on_disconnect() 的作用

`on_disconnect()` 是 MQTT 连接断开时执行的回调函数。

它不是由 `main.py` 主动调用，而是：

```text
MQTT 连接关闭
→ Paho 网络线程检测到连接事件
→ Paho 自动调用 on_disconnect()
```

Callback API VERSION2 的参数结构：

```python
def on_disconnect(
    client,
    userdata,
    disconnect_flags,
    reason_code,
    properties,
):
    pass
```

参数含义：

```text
client
→ 当前 Paho MQTT Client 对象

userdata
→ 通过 user_data_set() 保存的项目内部数据

disconnect_flags
→ 与本次断开相关的标志信息

reason_code
→ 本次断开的原因

properties
→ MQTT 5 属性；当前项目主要使用 MQTT 3.1.1
```

## 为什么最初没有打印断线信息

最初代码只判断：

```python
if reason_code == 0:
    ...
elif reason_code == 4:
    ...
```

但 Broker 被强制停止时，实际断开原因显示为：

```text
Unspecified error
```

它不等于固定数字 `4`。

因此：

```text
reason_code 不等于 0
并且不等于 4
→ 所有判断分支都没有进入
→ 终端没有打印断线日志
```

修正方法是先无条件输出真实参数：

```python
print("on_disconnect called:", reason_code)
```

确认真实值后，再区分正常断开和异常断开。

今天得到的调试原则：

```text
调试回调函数
→ 先打印真实回调参数
→ 再根据实际结果设计判断
→ 不要在没有证据时猜固定错误码
```

## 正常断开与异常断开

### 正常退出

用户按下：

```text
Ctrl+C
```

程序流程：

```text
KeyboardInterrupt
→ except
→ finally
→ 发布 Retained Graceful Offline
→ disconnect()
→ Paho 调用 on_disconnect()
→ 输出 Normal disconnection
→ loop_stop()
```

状态消息：

```json
{
  "gateway": "linux_stm32_gateway_01",
  "device": "stm32_node_01",
  "status": "offline",
  "reason": "graceful_shutdown"
}
```

### 异常断开

异常场景包括：

- Mosquitto Broker 被停止；
- 网络连接中断；
- Broker 进程被终止；
- Linux 网络接口突然失效。

流程：

```text
连接突然丢失
→ 业务代码没有主动调用 disconnect()
→ Paho 自动调用 on_disconnect()
→ reason_code 表示异常原因
→ 主进程继续运行
→ Paho 后台线程尝试重连
```

终端输出类似：

```text
mqtt unexpected disconnect Unspecified error
```

异常断开时：

```text
Python 主进程仍然运行
finally 没有执行
MQTT Client 没有被业务代码主动销毁
```

## 为什么不能写死异常错误码

不同断线场景、MQTT 协议版本和 Paho 版本可能给出不同的 `reason_code` 表现。

如果把异常断线写死为某一个数字：

```python
elif reason_code == 4:
```

就可能漏掉其他真实异常。

更合理的分类是：

```text
正常断开原因
→ graceful shutdown

其他非正常原因
→ unexpected disconnect
```

回调调试阶段应优先输出真实值。

## 指数退避重连

今天在配置文件中增加：

```text
最小重连等待时间
最大重连等待时间
```

配置传递链路：

```text
config.json
→ main.py 读取配置
→ connect_mqtt_client() 参数
→ mqtt_client.py
→ client.reconnect_delay_set()
```

指数退避流程：

```text
第一次重连失败
→ 等待最小时间

再次失败
→ 等待时间逐渐增大

持续失败
→ 等待时间最多增长到最大值

重连成功
→ 等待时间恢复为最小值
```

使用指数退避可以避免：

```text
Broker 离线
→ 客户端高频疯狂重试
→ 占用 CPU
→ 产生大量网络请求
→ 日志刷屏
→ Broker 恢复时瞬间承受大量连接请求
```

## 推荐的 MQTT 初始化顺序

推荐顺序：

```python
client.user_data_set(...)

client.on_disconnect = on_disconnect
client.on_connect = on_connect
client.on_message = on_message

client.reconnect_delay_set(
    mqtt_reconnect_min_delay,
    mqtt_reconnect_max_delay,
)

client.connect(
    broker,
    port,
    keepalive,
)

client.loop_start()
```

含义：

```text
1. 准备回调函数需要的数据
2. 注册所有回调
3. 配置重连策略
4. 发起首次连接
5. 启动 MQTT 后台网络线程
```

`connect()` 负责发起连接并发送 MQTT CONNECT。

真正的连接结果需要网络循环处理 Broker 返回的 CONNACK，因此还需要：

```python
client.loop_start()
```

## 为什么不在 on_disconnect() 中直接 reconnect()

今天没有在回调中调用：

```python
client.reconnect()
```

也没有写：

```python
while True:
    client.reconnect()
```

原因是当前已经使用：

```text
loop_start()
+
reconnect_delay_set()
```

Paho 后台线程本身能够负责自动重连。

职责划分：

```text
on_disconnect()
→ 观察、记录断线事件和原因

Paho 后台网络线程
→ 根据退避策略执行重连

on_connect()
→ 连接成功后恢复业务状态
```

如果业务代码和 Paho 同时尝试重连，可能产生：

- 重复连接；
- 状态竞争；
- 回调重复执行；
- 日志混乱；
- 调试困难。

## 为什么断线期间停止 Heartbeat

原 Heartbeat 主循环会周期性执行：

```text
构造 Heartbeat
→ publish()
```

Broker 已经停止时，继续发布会产生：

```text
mqtt publish failed
mqtt publish failed
mqtt publish failed
```

这些失败日志没有业务意义，还会持续刷屏。

因此在 Heartbeat 发布前检查：

```python
mqtt_client.is_connected()
```

判断结果：

```text
True
→ 当前 MQTT 连接存在，允许发布 Heartbeat

False
→ 当前 MQTT 未连接，跳过本次发布
```

跳过 Heartbeat 不代表整个主循环停止，网关主进程仍然继续运行。

## 为什么断线期间仍更新时间点

当达到 Heartbeat 周期时：

```text
已连接
→ 发布 Heartbeat

未连接
→ 跳过 Heartbeat
```

无论是否真正发布，都更新时间检查点。

如果不更新时间：

```text
Heartbeat 条件一直成立
→ 主循环每次迭代都进入判断
→ 高频检查连接状态
→ 可能持续刷日志
```

正确行为：

```text
按正常 Heartbeat 周期检查一次
→ 未连接则跳过
→ 更新时间点
→ 下一个周期再检查
```

## 为什么 on_connect() 能恢复业务

当前 `on_connect()` 已经负责：

1. 判断 MQTT 连接是否成功；
2. 订阅 Command Topic；
3. 发布 Retained Online Status。

首次连接成功时会调用：

```text
on_connect()
```

运行期间异常断线后重新连接成功，也会再次调用：

```text
on_connect()
```

因此重连代码中不需要重复手写：

```text
subscribe command
publish online
```

将连接成功后的业务初始化统一放入 `on_connect()`，可以避免重复代码和状态不一致。

## 重连后恢复的不只是 TCP

仅看到：

```text
mqtt broker connected
```

只能证明连接建立。

完整业务恢复还需要验证：

- Broker 返回连接成功；
- Command Topic 重新订阅；
- Retained Online 重新发布；
- Heartbeat 恢复；
- Command 能够接收；
- 执行逻辑能够运行；
- ACK 能够返回。

## Mosquitto service stop 的问题

测试时执行：

```bash
sudo service mosquitto stop
```

虽然提示停止成功，但：

```bash
sudo ss -ltnp | grep 1883
```

仍然显示 Mosquitto 正在监听端口。

这说明：

```text
服务脚本认为已经停止
但真实 Mosquitto 进程仍在运行
```

进一步排查：

```bash
ps -fp PID
ps -ef | grep '[m]osquitto'
```

确认真实 PID 后：

```bash
sudo kill -TERM PID
```

再次检查：

```bash
sudo ss -ltnp | grep 1883
```

没有输出，才说明 Broker 真正停止。

测试原则：

```text
service 命令的文字提示只是参考
端口监听和真实进程才是实际运行证据
```

## Broker 恢复测试

重新启动：

```bash
sudo service mosquitto start
```

检查：

```bash
sudo ss -ltnp | grep 1883
```

出现：

```text
127.0.0.1:1883
[::1]:1883
```

说明 Broker 恢复监听。

随后网关自动输出：

```text
mqtt broker connected: Success
mqtt command topic subscribed: ...
mqtt message published: .../status
```

分别证明：

```text
连接恢复
Command 订阅恢复
Retained Online 恢复
```

## 重连后的 Command 与 ACK 验证

发送：

```json
{
  "command": "led_on"
}
```

网关输出：

```text
mqtt command received
command: led_on
simulated actuator: LED ON
command executed successfully: led_on
mqtt ack queued: edgeaiot/stm32_node_01/ack
```

ACK 订阅端收到：

```json
{
  "command": "led_on",
  "status": "success"
}
```

同时 Heartbeat 恢复。

这证明恢复的不只是底层 TCP，而是完整业务链路。

## 实际测试结果

```text
✓ 首次连接正常
✓ Telemetry 正常
✓ Heartbeat 正常
✓ Broker 被真实关闭
✓ on_disconnect() 被触发
✓ 异常原因被正确输出
✓ 网关主进程没有退出
✓ 断线期间 Heartbeat 不刷失败日志
✓ Broker 恢复后自动重连
✓ on_connect() 再次执行
✓ Command Topic 自动重新订阅
✓ Retained Online 重新发布
✓ Command 正常接收
✓ ACK 正常返回
✓ Heartbeat 恢复
✓ Ctrl+C 被判断为正常断开
✓ Graceful Offline 正常发布
```

## 当前完整连接生命周期

### 启动

```text
读取配置
→ 创建 Client
→ 注册 LWT
→ 注册回调
→ 配置重连退避
→ connect()
→ loop_start()
→ on_connect()
```

### 正常运行

```text
Telemetry 发布
Heartbeat 发布
Command 接收
ACK 返回
Retained Status
```

### 运行期间断线

```text
Broker 消失
→ on_disconnect()
→ 记录异常
→ Heartbeat 暂停
→ Paho 自动重连
```

### Broker 恢复

```text
重连成功
→ on_connect()
→ 恢复订阅
→ 发布 Online
→ 恢复 Heartbeat、Command 和 ACK
```

### 正常退出

```text
Ctrl+C
→ 发布 Graceful Offline
→ disconnect()
→ on_disconnect() 正常原因
→ loop_stop()
```

## 模块职责

### main.py

```text
读取重连配置
传递 MQTT 参数
判断当前连接状态
控制 Heartbeat
管理主进程生命周期
处理正常退出
```

### mqtt_client.py

```text
创建 MQTT Client
注册回调
设置重连策略
建立 Broker 连接
处理连接与断线日志
恢复连接后的业务初始化
```

### Paho 后台线程

```text
处理 MQTT 网络收发
检测连接丢失
执行自动重连
调用 on_disconnect()
调用 on_connect()
调用 on_message()
```

### Mosquitto Broker

```text
接受 Client 连接
路由 Topic 消息
保存 Retained Status
在异常断线时触发 LWT
```

## 今日遇到的问题

### on_disconnect 没有输出

原因：

```text
异常 reason_code 被错误写死为数字 4
实际异常原因不是固定数字 4
```

修复：

```text
先打印真实 reason_code
再区分正常与异常
```

### service stop 后端口仍在

原因：

```text
服务脚本状态
与
真实监听 1883 的进程状态
不一致
```

修复：

```text
查询端口
→ 查询 PID
→ kill -TERM
→ 再次检查端口
```

### IDE 无法提示连接状态方法

原因：

```text
mqtt_client 初始值为 None
create_mqtt_client() 没有返回类型标注
Pylance 无法确定具体类型
```

这不代表方法不存在，只是静态类型推断不足。

后续可以为创建函数增加 Paho Client 返回类型标注。

## 当前边界

Day 52 已经证明：

- 运行期间 Broker 断开能够被检测；
- 网关主进程不会退出；
- Paho 能自动重连；
- 重连后业务链路能够恢复。

尚未证明：

- 程序启动时 Broker 不存在也能正常运行；
- 真实 STM32 串口链路可靠；
- STM32 节点始终在线；
- 多 Broker 故障转移；
- 网络永久稳定。

## 面试时怎么讲

我为 Linux 网关增加了运行期间 MQTT 断线检测和自动重连能力。

Paho 网络线程检测到连接中断后会自动调用 `on_disconnect()`。我根据真实 `reason_code` 区分正常退出和异常断线，而不是把异常原因写死成某一个数字。

我没有在回调中手动执行阻塞式重连，而是使用 `reconnect_delay_set()` 配置指数退避，由 Paho 后台线程负责恢复连接。

断线期间，主线程通过 `is_connected()` 跳过 Heartbeat，避免无效发布和日志刷屏。

重连成功后，Paho 再次调用 `on_connect()`，自动恢复 Command Topic 订阅并重新发布 Retained Online。

最后通过停止和恢复 Mosquitto，验证了 Status、Heartbeat、Command 和 ACK 均能恢复。

## 如果从零重写

```text
1. 明确正常断开与异常断开
2. 编写 on_disconnect()
3. 先输出真实 reason_code
4. 注册断线回调
5. 配置最小和最大重连间隔
6. 使用 reconnect_delay_set()
7. 让 Paho 网络线程负责重连
8. Heartbeat 发布前检查连接状态
9. 将恢复逻辑统一放入 on_connect()
10. 关闭 Broker 测试断线
11. 恢复 Broker 测试重连
12. 验证 Status、Command、ACK 和 Heartbeat
13. 验证 Ctrl+C 正常退出
```

## 后续计划

Day 53 处理：

```text
程序启动时 Broker 尚未运行
→ 首次连接失败不能导致程序崩溃
→ 网关主进程先正常运行
→ 后台持续尝试连接
→ Broker 后启动后自动接入
```
