#!/usr/bin/env python3
"""
示例：在代码里改参数，也能被 SciAgent 追踪

这个示例展示了如何在代码内部定义参数，同时让 SciAgent 能够追踪
"""

import json
import random
import time
from sciagent.track import log_params, log_metrics, save


def train_model():
    """训练模型 - 参数在代码里"""
    
    # ============================================
    # 参数定义（可以直接在这里改）
    # ============================================
    learning_rate = 0.09
    batch_size = 64
    epochs = 60
    optimizer = "adam"
    model_type = "resnet50"
    
    # ============================================
    # 关键：调用 log_params 让 SciAgent 知道这些参数
    # ============================================
    log_params(
        learning_rate=learning_rate,
        batch_size=batch_size,
        epochs=epochs,
        optimizer=optimizer,
        model_type=model_type
    )
    
    print("=" * 60)
    print("  🔬 训练开始")
    print("=" * 60)
    print(f"  学习率: {learning_rate}")
    print(f"  批次大小: {batch_size}")
    print(f"  训练轮数: {epochs}")
    print(f"  优化器: {optimizer}")
    print(f"  模型: {model_type}")
    print("=" * 60)
    print()
    
    # 模拟训练过程
    best_loss = float('inf')
    best_acc = 0.0
    
    for epoch in range(1, epochs + 1):
        # 模拟训练
        time.sleep(0.05)
        
        # 模拟指标（learning_rate 影响收敛）
        progress = epoch / epochs
        loss = 1.0 * (1 - progress) + random.uniform(-0.1, 0.1)
        accuracy = progress * 0.9 + random.uniform(0, 0.05)
        
        # 调整基于参数的影响
        if learning_rate < 0.0005:
            loss += 0.1  # 学习率太小，收敛慢
        elif learning_rate > 0.01:
            loss += 0.2  # 学习率太大，不稳定
        
        if batch_size < 16:
            accuracy -= 0.05  # batch 太小，不稳定
        elif batch_size > 128:
            loss += 0.1  # batch 太大，泛化差
        
        best_loss = min(best_loss, loss)
        best_acc = max(best_acc, accuracy)
        
        if epoch % 10 == 0 or epoch == epochs:
            print(f"Epoch {epoch:3d}/{epochs}: loss={loss:.4f}, acc={accuracy:.4f}")
    
    print()
    print("✓ 训练完成！")
    print(f"  最佳准确率: {best_acc:.4f}")
    print(f"  最佳损失: {best_loss:.4f}")
    print()
    
    # ============================================
    # 记录训练结果
    # ============================================
    log_metrics(
        final_accuracy=best_acc,
        final_loss=best_loss,
        train_loss=loss,
        train_accuracy=accuracy
    )
    
    # ============================================
    # 保存所有数据到 metrics.json
    # ============================================
    save()
    
    print("✓ 参数和指标已保存到 metrics.json")
    print("  SciAgent 会自动检测并追踪这些数据")
    
    return best_acc, best_loss


if __name__ == "__main__":
    print()
    train_model()
    print()
    print("=" * 60)
    print("  📊 使用 SciAgent 查看结果")
    print("=" * 60)
    print()
    print("  sciagent history        # 查看历史")
    print("  sciagent analyze --last # AI 分析")
    print("  sciagent weekly         # 生成周报")
    print()

