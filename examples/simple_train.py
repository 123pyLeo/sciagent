#!/usr/bin/env python3
"""
超简单的训练示例 - 线性回归

不需要额外依赖，几秒钟就能跑完，用于快速测试 SciAgent
"""

import json
import random
import time
from pathlib import Path


def generate_data(n_samples=100):
    """生成简单的线性回归数据"""
    # y = 2*x + 3 + noise
    X = [random.uniform(0, 10) for _ in range(n_samples)]
    y = [2 * x + 3 + random.gauss(0, 0.5) for x in X]
    return X, y


def train_linear_regression(X, y, learning_rate=0.05, epochs=100):
    """简单的线性回归训练（梯度下降）"""
    # 初始化参数
    w = random.uniform(-1, 1)
    b = random.uniform(-1, 1)
    
    n = len(X)
    
    print(f"🚀 开始训练线性回归 (y = w*x + b)")
    print(f"  - 样本数: {n}")
    print(f"  - 学习率: {learning_rate}")
    print(f"  - 训练轮数: {epochs}")
    print()
    
    for epoch in range(1, epochs + 1):
        # 前向传播：计算预测值
        predictions = [w * x + b for x in X]
        
        # 计算损失（MSE）
        loss = sum((pred - true) ** 2 for pred, true in zip(predictions, y)) / n
        
        # 反向传播：计算梯度
        grad_w = sum(2 * (pred - true) * x for pred, true, x in zip(predictions, y, X)) / n
        grad_b = sum(2 * (pred - true) for pred, true in zip(predictions, y)) / n
        
        # 更新参数
        w = w - learning_rate * grad_w
        b = b - learning_rate * grad_b
        
        # 每10轮打印一次
        if epoch % 10 == 0 or epoch == 1:
            print(f"Epoch {epoch:3d}/{epochs} - loss: {loss:.6f}, w: {w:.4f}, b: {b:.4f}")
        
        # 保存指标
        metrics = {
            "epoch": epoch,
            "train_loss": loss,
            "w": w,
            "b": b,
            "learning_rate": learning_rate
        }
        
        with open("metrics.json", "w") as f:
            json.dump(metrics, f, indent=2)
        
        # 稍微延迟一下，让训练过程更明显
        time.sleep(0.02)
    
    print(f"\n✨ 训练完成！")
    print(f"  - 最终参数: w={w:.4f}, b={b:.4f}")
    print(f"  - 最终损失: {loss:.6f}")
    print(f"  - 真实参数: w=2.0000, b=3.0000")
    
    return loss, w, b


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="超简单线性回归训练示例")
    parser.add_argument("--lr", type=float, default=0.05, help="学习率")
    parser.add_argument("--epochs", type=int, default=80, help="训练轮数")
    parser.add_argument("--samples", type=int, default=100, help="样本数")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("  🔬 简单线性回归训练 (不需要额外依赖)")
    print("=" * 60)
    print()
    
    # 生成数据
    X, y = generate_data(args.samples)
    
    # 训练
    try:
        loss, w, b = train_linear_regression(X, y, args.lr, args.epochs)
        print("\n✓ 训练成功！")
        exit(0)
    except Exception as e:
        print(f"\n❌ 训练失败: {e}")
        exit(1)

