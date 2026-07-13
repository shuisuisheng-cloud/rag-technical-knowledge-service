---
title: LeetCode Day 10 均值 方差 标准差
project: LeetCode 算法学习
system_layer: 独立算法学习
document_type: algorithm_learning_note
status: sample_verified
last_updated: 2026-07-12
tags: [Python, 数学基础, 均值, 方差, 标准差, ACM输入输出]
---

# LeetCode Day 10 均值、方差与标准差

## 今日目标

不使用 NumPy 和 `statistics`，计算一组数据的：

- 均值；
- 总体方差；
- 标准差。

## 输入与输出

第一行输入数据数量 `n`，第二行输入 `n` 个浮点数。

```python
n = int(sys.stdin.readline())
nums = list(map(float, sys.stdin.readline().split()))
```

结果保留六位小数：

```python
print(f"{mean:.6f}")
print(f"{variance:.6f}")
print(f"{std:.6f}")
```

## 核心公式

```text
均值 = sum(nums) / n

总体方差 = Σ(x - mean)² / n

标准差 = sqrt(variance)
```

Python 中使用：

```python
import math

std = math.sqrt(variance)
```

## 完整流程

```text
读取 n 和数据
→ 计算均值
→ 累加每个元素与均值的偏差平方
→ 除以 n 得到总体方差
→ 开平方得到标准差
→ 输出结果
```

## 复杂度

```text
时间复杂度：O(n)
空间复杂度：O(n)
```

当前使用列表保存全部输入，因此空间复杂度为 `O(n)`。

## 易错点

- 输入需要转换为 `float`；
- 总体方差除以 `n`，不是 `n - 1`；
- 必须计算偏差的平方；
- 标准差是方差的平方根；
- 输出保留六位小数。

## 面试时怎么讲

我先对所有数据求和并除以 `n` 得到均值，然后再次遍历数组，累加每个元素与均值之差的平方。

本题计算总体方差，因此偏差平方和除以 `n`。最后使用 `math.sqrt()` 计算标准差。

整个算法时间复杂度为 `O(n)`，当前使用列表保存输入，因此空间复杂度为 `O(n)`。
