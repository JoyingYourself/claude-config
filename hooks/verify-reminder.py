#!/usr/bin/env python3
"""Stop Hook: 30% 概率注入校验提醒，避免提醒疲劳"""
import random
import time

REMINDERS = [
    # 校验提醒
    "🔍 下次响应前请执行内部校验：检查所有数字、路径、逻辑是否准确。",
    "⚠️ 记住：输出前做第二遍检查。数据从源文件引用，路径用 Read 确认。",
    "✅ 强制校验提醒：确认数据溯源、计算正确、路径存在、逻辑一致后再输出。",
    "📋 检查清单：□数据溯源 □计算验证 □代码逻辑 □文件路径 □逻辑一致性",
    "🔄 第二遍检查：如果发现任何错误，请内部修正后再呈现，不要等用户指出。",
]

if random.random() < 0.3:  # 30% 概率触发
    seed = int(time.time()) // 300
    random.seed(seed)
    print(random.choice(REMINDERS))
