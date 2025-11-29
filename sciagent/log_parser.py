"""
stdout 日志自动解析模块

自动从训练输出中提取指标，无需用户修改任何代码。
支持常见的深度学习框架输出格式。
"""

import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field


@dataclass
class ParsedMetrics:
    """解析后的指标数据"""
    # 最终指标（取最后一次出现的值）
    final_metrics: Dict[str, float] = field(default_factory=dict)
    # 历史指标（用于追踪趋势）
    history: Dict[str, List[float]] = field(default_factory=dict)
    # 检测到的 epoch 数
    epochs_detected: int = 0
    # 最佳指标
    best_metrics: Dict[str, float] = field(default_factory=dict)
    # 训练配置（从日志中提取）
    config: Dict[str, Any] = field(default_factory=dict)


class LogParser:
    """训练日志解析器"""
    
    # 常见的指标名称变体映射到标准名称
    METRIC_ALIASES = {
        # Loss 类
        'loss': 'loss',
        'train_loss': 'train_loss',
        'val_loss': 'val_loss',
        'test_loss': 'test_loss',
        'validation_loss': 'val_loss',
        'training_loss': 'train_loss',
        # Accuracy 类
        'acc': 'accuracy',
        'accuracy': 'accuracy',
        'train_acc': 'train_accuracy',
        'val_acc': 'val_accuracy',
        'test_acc': 'test_accuracy',
        'train_accuracy': 'train_accuracy',
        'val_accuracy': 'val_accuracy',
        'test_accuracy': 'test_accuracy',
        'validation_accuracy': 'val_accuracy',
        # 其他常见指标
        'f1': 'f1_score',
        'f1_score': 'f1_score',
        'f1-score': 'f1_score',
        'precision': 'precision',
        'recall': 'recall',
        'auc': 'auc',
        'auroc': 'auc',
        'mse': 'mse',
        'mae': 'mae',
        'rmse': 'rmse',
        'lr': 'learning_rate',
        'learning_rate': 'learning_rate',
    }
    
    # 指标提取正则表达式模式
    PATTERNS = [
        # 格式: "Loss: 0.1234" 或 "loss=0.1234" 或 "loss: 0.1234"
        r'(?P<name>[\w_]+)[\s]*[:=][\s]*(?P<value>[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)',
        
        # 格式: "Acc: 97.82%" 或 "accuracy: 97.82%"
        r'(?P<name>[\w_]+)[\s]*[:=][\s]*(?P<value>[-+]?\d*\.?\d+)[\s]*%',
        
        # 格式: "训练 - Loss: 0.1234, Acc: 92.34%"（中文标签）
        r'(?:训练|测试|验证)[\s]*[-–][\s]*(?P<pairs>(?:[\w_]+[\s]*[:=][\s]*[-+]?\d*\.?\d+%?[\s]*[,，]?[\s]*)+)',
        
        # 格式: "Epoch 1/10" 或 "epoch: 1"
        r'[Ee]poch[\s]*(?:[:=][\s]*)?(?P<epoch>\d+)(?:/(?P<total>\d+))?',
        
        # 格式: "[Epoch 5] loss: 0.123, acc: 0.95"
        r'\[?[Ee]poch[\s]*(?P<epoch>\d+)\]?[\s]*(?P<pairs>(?:[\w_]+[\s]*[:=][\s]*[-+]?\d*\.?\d+%?[\s]*[,，]?[\s]*)+)',
    ]
    
    # 配置参数提取模式
    CONFIG_PATTERNS = [
        # 格式: "learning_rate: 0.001" 或 "lr=0.001"
        r'(?P<name>learning_rate|lr|batch_size|epochs?|num_epochs|hidden_dim|dropout|weight_decay)[\s]*[:=][\s]*(?P<value>[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)',
    ]
    
    def __init__(self):
        self.compiled_patterns = [re.compile(p, re.IGNORECASE) for p in self.PATTERNS]
        self.compiled_config_patterns = [re.compile(p, re.IGNORECASE) for p in self.CONFIG_PATTERNS]
    
    def parse(self, log_content: str) -> ParsedMetrics:
        """
        解析日志内容，提取指标
        
        Args:
            log_content: 日志文本内容
            
        Returns:
            ParsedMetrics 对象
        """
        result = ParsedMetrics()
        
        # 按行处理
        lines = log_content.split('\n')
        
        for line in lines:
            # 跳过进度条行（tqdm 等）
            if self._is_progress_bar(line):
                continue
            
            # 提取配置参数
            self._extract_config(line, result)
            
            # 提取 epoch 信息
            self._extract_epoch(line, result)
            
            # 提取指标
            self._extract_metrics(line, result)
            
            # 检测最佳指标
            self._extract_best_metrics(line, result)
        
        # 生成最终指标
        self._finalize_metrics(result)
        
        return result
    
    def _is_progress_bar(self, line: str) -> bool:
        """检测是否为进度条行"""
        # tqdm 进度条特征
        if '|' in line and ('it/s' in line or 'B/s' in line):
            return True
        # 百分比进度条
        if re.match(r'^\s*\d+%\|', line):
            return True
        return False
    
    def _extract_config(self, line: str, result: ParsedMetrics) -> None:
        """提取配置参数"""
        for pattern in self.compiled_config_patterns:
            for match in pattern.finditer(line):
                name = match.group('name').lower()
                try:
                    value = float(match.group('value'))
                    # 转换为标准名称
                    std_name = self.METRIC_ALIASES.get(name, name)
                    result.config[std_name] = value
                except (ValueError, TypeError):
                    pass
    
    def _extract_epoch(self, line: str, result: ParsedMetrics) -> None:
        """提取 epoch 信息"""
        # Epoch X/Y 格式
        match = re.search(r'[Ee]poch[\s]*(?:[:=][\s]*)?(\d+)(?:/(\d+))?', line)
        if match:
            epoch = int(match.group(1))
            result.epochs_detected = max(result.epochs_detected, epoch)
    
    def _extract_metrics(self, line: str, result: ParsedMetrics) -> None:
        """提取指标值"""
        # 方法1：直接匹配 key: value 或 key=value 格式
        # 支持多种格式
        patterns = [
            # loss: 0.1234 或 loss=0.1234
            r'(?P<name>\b(?:train_?|val_?|test_?|validation_?)?(?:loss|acc(?:uracy)?|f1(?:_?score)?|precision|recall|auc|mse|mae|rmse)\b)[\s]*[:=][\s]*(?P<value>[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)[\s]*%?',
            # Loss: 0.1234（首字母大写）
            r'(?P<name>\b(?:Train_?|Val_?|Test_?|Validation_?)?(?:Loss|Acc(?:uracy)?|F1(?:_?[Ss]core)?|Precision|Recall|AUC|MSE|MAE|RMSE)\b)[\s]*[:=][\s]*(?P<value>[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)[\s]*%?',
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, line, re.IGNORECASE):
                name = match.group('name').lower().strip()
                value_str = match.group('value')
                
                try:
                    value = float(value_str)
                    
                    # 如果是百分比格式（行中有 %），转换为小数
                    if '%' in line[match.end():match.end()+2]:
                        value = value / 100.0
                    
                    # 标准化名称
                    std_name = self._standardize_metric_name(name)
                    
                    # 添加到历史
                    if std_name not in result.history:
                        result.history[std_name] = []
                    result.history[std_name].append(value)
                    
                except (ValueError, TypeError):
                    pass
    
    def _extract_best_metrics(self, line: str, result: ParsedMetrics) -> None:
        """提取最佳指标（从 "best" 或 "最佳" 相关行）"""
        lower_line = line.lower()
        if 'best' in lower_line or '最佳' in line or '保存' in line:
            # 尝试提取指标值
            # 格式: "Best accuracy: 0.9782" 或 "最佳准确率: 97.82%"
            match = re.search(
                r'(?:best|最佳)[\s]*(?:[\w_]*)?[\s]*[:=]?[\s]*(?P<value>[-+]?\d*\.?\d+)[\s]*%?',
                line, re.IGNORECASE
            )
            if match:
                try:
                    value = float(match.group('value'))
                    # 检测是百分比还是小数
                    if '%' in line or value > 1.5:  # 大于1.5通常是百分比
                        value = value / 100.0
                    result.best_metrics['best_accuracy'] = value
                except (ValueError, TypeError):
                    pass
    
    def _standardize_metric_name(self, name: str) -> str:
        """标准化指标名称"""
        name = name.lower().strip()
        name = name.replace('-', '_').replace(' ', '_')
        
        # 使用别名映射
        if name in self.METRIC_ALIASES:
            return self.METRIC_ALIASES[name]
        
        return name
    
    def _finalize_metrics(self, result: ParsedMetrics) -> None:
        """生成最终指标"""
        # 对于每个指标，取最后一个值作为最终值
        for name, values in result.history.items():
            if values:
                result.final_metrics[f'final_{name}'] = values[-1]
                
                # 如果有多个值，也记录第一个值用于对比
                if len(values) > 1:
                    result.final_metrics[f'initial_{name}'] = values[0]
        
        # 添加最佳指标
        result.final_metrics.update(result.best_metrics)
        
        # 添加 epoch 数
        if result.epochs_detected > 0:
            result.final_metrics['epochs_completed'] = result.epochs_detected


def parse_log_file(log_path: str) -> Dict[str, float]:
    """
    解析日志文件，返回提取的指标
    
    Args:
        log_path: 日志文件路径
        
    Returns:
        指标字典
    """
    try:
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        parser = LogParser()
        result = parser.parse(content)
        
        return result.final_metrics
    except Exception as e:
        # 静默失败，返回空字典
        return {}


def parse_log_content(content: str) -> Dict[str, float]:
    """
    解析日志内容字符串，返回提取的指标
    
    Args:
        content: 日志文本内容
        
    Returns:
        指标字典
    """
    parser = LogParser()
    result = parser.parse(content)
    return result.final_metrics


# 便捷函数
def extract_metrics_from_stdout(stdout_content: str) -> Dict[str, float]:
    """
    从 stdout 输出中提取指标（guardian.py 调用此函数）
    
    Args:
        stdout_content: stdout 输出内容
        
    Returns:
        提取的指标字典
    """
    return parse_log_content(stdout_content)


if __name__ == '__main__':
    # 测试用例
    test_logs = [
        # PyTorch 风格
        """
        Epoch 1/10
        Train Loss: 0.5234, Train Acc: 82.34%
        Val Loss: 0.4123, Val Acc: 87.56%
        
        Epoch 2/10
        Train Loss: 0.3456, Train Acc: 89.12%
        Val Loss: 0.3012, Val Acc: 91.23%
        
        Best accuracy: 91.23%
        """,
        
        # TensorFlow/Keras 风格
        """
        Epoch 1/5
        loss: 0.6931 - accuracy: 0.5234 - val_loss: 0.6543 - val_accuracy: 0.6789
        Epoch 2/5
        loss: 0.4567 - accuracy: 0.7890 - val_loss: 0.4321 - val_accuracy: 0.8234
        """,
        
        # 简单格式
        """
        Training...
        loss=0.234, acc=0.956
        Final loss: 0.123, Final acc: 0.978
        """,
        
        # 中文格式
        """
        📈 Epoch 1/5 (lr=0.001000)
           训练 - Loss: 0.2345, Acc: 92.34%
           测试 - Loss: 0.1234, Acc: 97.82%
           ✅ 保存最佳模型 (Acc: 97.82%)
        """,
    ]
    
    print("=" * 60)
    print("LogParser 测试")
    print("=" * 60)
    
    for i, log in enumerate(test_logs, 1):
        print(f"\n--- 测试用例 {i} ---")
        metrics = parse_log_content(log)
        print(f"提取的指标: {metrics}")

