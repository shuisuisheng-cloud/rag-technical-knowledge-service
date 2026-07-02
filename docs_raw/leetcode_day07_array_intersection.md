---

title: LeetCode Day 7 两个数组的交集
project: LeetCode 算法学习
system_layer: 独立算法学习
document_type: algorithm_learning_note
status: sample_verified
last_updated: 2026-07-02
tags: [Python, 数组, 集合, 去重, ACM输入输出]

---
# LeetCode Day 7 两个数组的交集
## 目标
处理两个数组的交集，并打印出数量以及按第一个数组数的排序，打印出交集
## 核心文件或数据结构
lookup = set(nums2)
seen = set()
result = []
## 输入输出
输入 第一和第二个数组的数的个数，第一和第二个数组的数
输出 交集的数的数量 交集的数
## 数据流或控制流
使用 lookup 快速判断数字是否存在于第二个数组；
遍历第一个数组；
数字存在于 lookup 且没有出现在 seen 中时加入结果；
使用 seen 避免重复；
保留第一个数组中的出现顺序。
## 验证结果
三组测试样例通过，并已完成 Git 提交和 push。
## 当前边界
当前实现按照 nums1 的遍历顺序保存结果，
不是按照数字大小排序，也不能依赖普通 set 的输出顺序。
## 复杂度
时间复杂度：O(n + m)

建立 nums2 集合需要 O(m)，遍历 nums1 需要 O(n)。

空间复杂度：O(m + k)

lookup 最多保存 m 个数字，seen 和 result 最多保存 k 个交集元素。