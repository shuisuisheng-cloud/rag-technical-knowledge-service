---
title: Linux-STM32 物联网边缘网关 Day 53 MQTT 首次连接失败与异步重试
project: Linux-STM32 物联网边缘网关
system_layer: 通信层 / 数据中枢
document_type: software_module_record
status: software_verified
last_updated: 2026-07-12
tags: [Linux, Python, MQTT, Paho, connect_async, InitialConnection, AutoReconnect, Reliability]
---

# Linux-STM32 物联网边缘网关 Day 53 MQTT 首次连接失败与异步重试

## 今日目标

Day 52 已经解决：

```text
网关先成功连接 Broker
→ 运行期间 Broker 突然停止
→ Paho 检测断线
→ 网关自动重连
```

Day 53 解决另一个场景：

```text
网关程序启动
→ Broker 尚未运行
→ 首次连接失败
→ 网关不能直接崩溃退出
→ 后台持续尝试连接
→ Broker 后启动后自动接入
```

## 同步 connect() 的问题

原来使用：

```python
client.connect(
    broker,
    port,
    keepalive,
)
```

同步 `connect()` 会在当前调用位置立即尝试建立网络连接。

如果 Broker 没有监听端口，可能抛出：

```text
ConnectionRefusedError
```

流程变成：

```text
程序启动
→ connect()
→ 首次连接失败
→ 异常向上抛出
→ 主程序退出
```

主程序已经退出后，Paho 后台线程也没有机会继续尝试连接。

## connect_async()

Day 53 将首次连接改为：

```python
client.connect_async(
    broker,
    port,
    keepalive,
)
```

`connect_async()` 不要求调用时立刻完成连接。

它先保存 Broker 地址、端口和 Keepalive 参数，实际连接过程交给 MQTT 网络循环。

之后调用：

```python
client.loop_start()
```

启动 Paho 后台网络线程。

完整流程：

```text
创建 MQTT Client
→ 设置 userdata
→ 注册回调
→ 配置重连退避
→ connect_async()
→ loop_start()
→ 后台线程尝试首次连接
```

## connect_async() 与 loop_start() 的关系

只调用：

```python
connect_async()
```

并不代表连接已经完成。

还需要：

```python
loop_start()
```

驱动网络线程执行：

- 创建 TCP 连接；
- 发送 MQTT CONNECT；
- 接收 CONNACK；
- 调用 `on_connect()`；
- 处理首次失败和后续重试。

职责关系：

```text
connect_async()
→ 保存连接目标和参数

loop_start()
→ 启动实际网络处理和连接尝试
```

## on_connect_fail()

新增：

```python
def on_connect_fail(client, userdata):
    ...
```

当首次连接或后续连接尝试无法建立底层连接时，Paho 可以调用该回调。

它的职责是：

```text
记录连接失败
```

例如：

```text
mqtt connect failed
```

它不负责：

- 终止主进程；
- 销毁 MQTT Client；
- 在回调中写无限重连循环；
- 直接阻塞等待 Broker 恢复。

## 首次连接失败后的流程

Broker 没有启动时：

```text
网关程序启动
→ connect_async() 保存连接参数
→ loop_start() 启动后台线程
→ 第一次连接失败
→ on_connect_fail() 输出失败日志
→ Python 主线程继续运行
→ Paho 根据重连策略继续尝试
```

这时网关进程仍然存在，可以继续：

- 执行主循环；
- 检查退出信号；
- 等待 Broker 恢复；
- 跳过当前无法完成的 MQTT 发布。

## Broker 后启动后的流程

Broker 恢复监听后：

```text
Paho 后台线程再次尝试连接
→ TCP 连接建立
→ 发送 MQTT CONNECT
→ Broker 返回 CONNACK
→ 调用 on_connect()
→ 订阅 Command Topic
→ 发布 Retained Online
→ Heartbeat 恢复
→ Command 与 ACK 可用
```

## on_connect() 的统一作用

当前 `on_connect()` 同时用于：

```text
首次异步连接成功
和
运行期间断线后的重新连接成功
```

它负责：

1. 判断连接结果；
2. 输出 Broker 连接成功日志；
3. 订阅 Command Topic；
4. 发布 Retained Online Status；
5. 恢复业务链路。

因此不需要为“首次连接恢复”和“运行期间重连恢复”分别写两套业务初始化代码。

## 未连接时跳过 Telemetry

网关主循环可能周期性生成 Telemetry。

Broker 尚未连接时，如果无条件执行：

```python
publish(...)
```

会产生无意义的发布失败。

因此在发布前检查：

```python
mqtt_client.is_connected()
```

逻辑：

```text
已经连接
→ 发布 Telemetry

尚未连接
→ 跳过本次 Telemetry 发布
```

这不代表丢弃整个网关进程，只是当前 MQTT 输出不可用。

## 未连接时跳过 Heartbeat

Heartbeat 也需要连接 Broker 才能发布。

逻辑：

```text
达到 Heartbeat 周期
→ 检查 is_connected()

True
→ 构造并发布 Heartbeat

False
→ 跳过发布
→ 更新时间点
```

即使没有连接，也应更新时间检查点，防止主循环每次迭代都重复进入 Heartbeat 判断。

## 未连接时跳过 Graceful Offline

用户按下 Ctrl+C 时，原本会主动发布：

```text
offline + graceful_shutdown
```

但如果程序从启动到退出都没有连接成功，当前没有可用 MQTT 连接。

因此退出前应判断：

```python
if mqtt_client.is_connected():
    publish_graceful_offline()
```

未连接时：

```text
跳过 Offline 发布
→ 停止 MQTT 网络线程
→ 释放资源
→ 正常退出
```

不能因为没有连接 Broker，就在退出阶段再次产生异常。

## Day 52 与 Day 53 的区别

### Day 52

```text
程序启动时 Broker 正常
→ 首次连接成功
→ 运行期间 Broker 停止
→ on_disconnect()
→ 自动重连
```

### Day 53

```text
程序启动时 Broker 不存在
→ 首次连接无法建立
→ 主程序不能退出
→ 后台持续尝试
→ Broker 后启动后自动连接
```

共同点：

- 都依赖 Paho 网络线程；
- 都使用重连退避；
- 成功连接后都进入 `on_connect()`；
- 都需要恢复订阅、状态和业务链路。

区别：

```text
Day 52
→ 已经连接后断线

Day 53
→ 第一次连接就失败
```

## MQTT Client 初始化顺序

推荐顺序：

```python
client = mqtt.Client(...)

client.user_data_set(...)

client.on_connect = on_connect
client.on_connect_fail = on_connect_fail
client.on_disconnect = on_disconnect
client.on_message = on_message

client.reconnect_delay_set(
    mqtt_reconnect_min_delay,
    mqtt_reconnect_max_delay,
)

client.connect_async(
    broker,
    port,
    keepalive,
)

client.loop_start()
```

这样可以保证：

```text
网络事件发生前
→ userdata 已准备
→ 回调已注册
→ 重连策略已设置
```

## 为什么不在 main.py 中写重连 while 循环

不建议写：

```python
while True:
    try:
        client.connect(...)
        break
    except:
        time.sleep(...)
```

原因包括：

- 阻塞主线程；
- 自己重复实现 Paho 已有功能；
- 可能与 Paho 自动重连冲突；
- 连接状态和回调执行更难管理；
- 程序退出处理更复杂。

当前职责划分：

```text
main.py
→ 管理业务主循环与生命周期

Paho 后台线程
→ 处理网络连接和自动重试

on_connect_fail()
→ 记录连接失败

on_connect()
→ 连接成功后恢复业务
```

## 实际测试方法

### 第一步：确认 Broker 未运行

检查端口：

```bash
sudo ss -ltnp | grep 1883
```

没有输出，说明当前 1883 没有监听。

### 第二步：启动网关

运行：

```bash
python main.py
```

预期：

```text
网关主进程保持运行
首次连接失败日志出现
程序不会抛出 ConnectionRefusedError 后退出
Telemetry 和 Heartbeat 被跳过
```

### 第三步：后启动 Broker

执行：

```bash
sudo service mosquitto start
```

确认端口：

```bash
sudo ss -ltnp | grep 1883
```

### 第四步：观察自动连接

网关终端应出现：

```text
mqtt broker connected: Success
mqtt command topic subscribed: ...
mqtt message published: .../status
```

### 第五步：验证业务

发送：

```json
{
  "command": "led_on"
}
```

检查：

- Command 被接收；
- 模拟执行器被调用；
- ACK 发布成功；
- Heartbeat 开始正常发布；
- 新订阅者能够收到 Retained Online。

## 实际验证结果

```text
✓ Broker 未运行时网关能够启动
✓ 首次连接失败没有导致主进程退出
✓ on_connect_fail() 能记录失败
✓ Paho 后台持续尝试连接
✓ 未连接时不发布 Telemetry
✓ 未连接时不发布 Heartbeat
✓ Broker 后启动后自动连接
✓ on_connect() 被调用
✓ Command Topic 自动订阅
✓ Retained Online 正常发布
✓ Heartbeat 恢复
✓ Command 正常接收
✓ ACK 正常返回
✓ 从未连接时 Ctrl+C 也能安全退出
```

## 当前完整连接生命周期

### Broker 已经存在

```text
程序启动
→ connect_async()
→ loop_start()
→ 连接成功
→ on_connect()
→ 进入正常业务
```

### Broker 启动时不存在

```text
程序启动
→ connect_async()
→ loop_start()
→ 首次连接失败
→ on_connect_fail()
→ 主进程继续运行
→ 后台继续尝试
```

### Broker 后启动

```text
Broker 开始监听
→ Paho 重试成功
→ on_connect()
→ 恢复订阅、Online、Heartbeat、Command 和 ACK
```

### 运行期间再次断线

```text
连接丢失
→ on_disconnect()
→ Paho 自动重连
→ on_connect()
→ 再次恢复业务
```

### 正常退出

```text
Ctrl+C
→ 检查是否已连接
→ 已连接则发布 Graceful Offline
→ 未连接则跳过发布
→ disconnect / loop_stop
→ 程序退出
```

## 模块职责

### main.py

```text
读取配置
运行主循环
判断 is_connected()
控制 Telemetry 和 Heartbeat
管理正常退出
```

### mqtt_client.py

```text
创建 MQTT Client
注册连接相关回调
配置重连退避
调用 connect_async()
启动网络线程
处理连接成功和失败日志
```

### Paho 后台线程

```text
尝试首次连接
处理 MQTT 网络收发
检测运行期间断线
执行自动重连
调用连接相关回调
```

## 当前边界

Day 53 已经证明：

- Broker 启动顺序不会决定网关能否存活；
- 首次连接失败不会直接终止主程序；
- Broker 后启动后能够自动连接；
- 连接成功后业务链路能够恢复。

尚未证明：

- 真实 STM32 串口长期运行可靠；
- 串口与 MQTT 两个链路能完全独立恢复；
- 多 Broker 故障转移；
- 网络永久中断后的数据缓存；
- 离线 Telemetry 是否需要补发；
- 消息持久化和本地队列。

## 今日遇到的问题

### 同步 connect() 导致程序退出

现象：

```text
Broker 未启动
→ ConnectionRefusedError
→ 主程序退出
```

解决：

```text
connect_async()
+
loop_start()
```

### 未连接时仍尝试 publish

现象：

```text
Telemetry 或 Heartbeat 发布失败
日志重复输出
```

解决：

```python
if mqtt_client.is_connected():
    publish(...)
```

### 从未连接时退出处理

现象：

```text
正常退出阶段尝试发布 Offline
但当前没有 MQTT 连接
```

解决：

```text
退出前判断连接状态
未连接则跳过 Offline 发布
```

## 常见错误

1. 只改成 `connect_async()`，但忘记调用 `loop_start()`；
2. 在注册回调前就启动网络线程；
3. 在 `on_connect_fail()` 中写阻塞式重连；
4. 未连接时仍持续发布 Heartbeat；
5. 未连接时仍持续发布 Telemetry；
6. 从未连接时仍强行发布 Graceful Offline；
7. 首次连接和运行期重连写两套业务恢复逻辑；
8. 把“connect_async 已调用”误认为“连接已经成功”；
9. 只验证连接日志，没有验证 Command 和 ACK；
10. 忘记配置重连退避。

## 面试时怎么讲

原来的同步 `connect()` 在程序启动时 Broker 不存在的情况下会抛出 `ConnectionRefusedError`，导致网关主进程退出。

我将首次连接改成 `connect_async()`，并使用 `loop_start()` 启动 Paho 后台网络线程，让首次连接和后续重试都由网络线程负责。

连接失败时，`on_connect_fail()` 只记录失败，不阻塞主线程，也不手动实现另一套重连循环。

未连接期间，主循环通过 `is_connected()` 跳过 Telemetry、Heartbeat 和退出状态发布，避免无意义的失败日志。

Broker 后启动后，Paho 自动连接并调用 `on_connect()`，重新订阅 Command Topic、发布 Retained Online，并恢复 Heartbeat、Command 和 ACK。

这样网关不再依赖 Broker 必须先于程序启动，提高了系统的启动顺序容错和无人值守恢复能力。

## 如果从零重写

```text
1. 明确首次连接失败场景
2. 使用 connect_async() 保存连接参数
3. 注册 on_connect_fail()
4. 注册 on_connect() 和 on_disconnect()
5. 配置 reconnect_delay_set()
6. 调用 loop_start()
7. 未连接时跳过 Telemetry
8. 未连接时跳过 Heartbeat
9. 未连接时安全处理 Ctrl+C
10. Broker 关闭状态下启动网关
11. 确认主进程不退出
12. 后启动 Broker
13. 验证自动连接
14. 验证订阅、Online、Heartbeat、Command 和 ACK
```

## 后续计划

- 接入真实 STM32 USART2；
- 将串口输入接入正式 Telemetry 数据流；
- 增加串口断线与恢复；
- 区分 MQTT 连接状态和 STM32 节点状态；
- 研究离线数据缓存与恢复后的补发策略。
