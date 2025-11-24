"""
SciAgent 参数追踪辅助模块

用于在代码内部追踪参数，无需改用命令行参数
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional


class ParamTracker:
    """参数追踪器 - 让代码内的参数也能被 SciAgent 追踪"""
    
    def __init__(self):
        self.params = {}
        self.metrics = {}
        self.metadata = {}
    
    def log_params(self, **kwargs):
        """
        记录参数
        
        使用方式：
            from sciagent import track
            
            lr = 0.001
            batch_size = 32
            
            track.log_params(
                lr=lr,
                batch_size=batch_size,
                epochs=100
            )
        """
        self.params.update(kwargs)
    
    def log_param(self, key: str, value: Any):
        """记录单个参数"""
        self.params[key] = value
    
    def log_metrics(self, **kwargs):
        """
        记录指标
        
        使用方式：
            track.log_metrics(
                accuracy=0.95,
                loss=0.12
            )
        """
        self.metrics.update(kwargs)
    
    def log_metric(self, key: str, value: Any):
        """记录单个指标"""
        self.metrics[key] = value
    
    def log_metadata(self, **kwargs):
        """记录元数据"""
        self.metadata.update(kwargs)
    
    def save(self, output_file: str = "metrics.json"):
        """
        保存所有追踪的数据到文件
        
        参数会同时保存到 metrics.json 和 params.json
        这样 SciAgent 就能追踪参数变化（通过 params.json → config_values）
        
        Args:
            output_file: 输出文件路径，默认 "metrics.json"
        """
        # 1. 保存 metrics.json（包含指标和参数）
        metrics_data = {}
        
        if self.params:
            metrics_data.update(self.params)
        
        if self.metrics:
            metrics_data.update(self.metrics)
        
        if self.metadata:
            metrics_data['_metadata'] = self.metadata
        
        output_path = Path(output_file)
        
        # 如果文件已存在，合并内容
        if output_path.exists():
            try:
                with open(output_path, 'r') as f:
                    existing_data = json.load(f)
                existing_data.update(metrics_data)
                metrics_data = existing_data
            except Exception:
                pass
        
        with open(output_path, 'w') as f:
            json.dump(metrics_data, f, indent=2)
        
        # 2. 单独保存 params.json（让 SciAgent 能追踪参数变化）
        if self.params:
            params_path = Path("params.json")
            with open(params_path, 'w') as f:
                json.dump(self.params, f, indent=2)
    
    def __enter__(self):
        """支持 with 语句"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出时自动保存"""
        self.save()


# 全局追踪器实例
_global_tracker = ParamTracker()


def log_params(**kwargs):
    """
    记录参数（全局函数）
    
    使用方式：
        from sciagent.track import log_params
        
        lr = 0.001
        batch_size = 32
        
        log_params(lr=lr, batch_size=batch_size, epochs=100)
    """
    _global_tracker.log_params(**kwargs)


def log_param(key: str, value: Any):
    """记录单个参数（全局函数）"""
    _global_tracker.log_param(key, value)


def log_metrics(**kwargs):
    """
    记录指标（全局函数）
    
    使用方式：
        from sciagent.track import log_metrics
        
        log_metrics(accuracy=0.95, loss=0.12)
    """
    _global_tracker.log_metrics(**kwargs)


def log_metric(key: str, value: Any):
    """记录单个指标（全局函数）"""
    _global_tracker.log_metric(key, value)


def log_metadata(**kwargs):
    """记录元数据（全局函数）"""
    _global_tracker.log_metadata(**kwargs)


def save(output_file: str = "metrics.json"):
    """
    保存所有追踪的数据（全局函数）
    
    使用方式：
        from sciagent.track import save
        
        save()  # 保存到 metrics.json
        save("results.json")  # 保存到自定义位置
    """
    _global_tracker.save(output_file)


def auto_track(func):
    """
    装饰器：自动追踪函数的参数和返回值
    
    使用方式：
        from sciagent.track import auto_track
        
        @auto_track
        def train(lr=0.001, batch_size=32, epochs=100):
            # 训练代码
            return {"accuracy": 0.95, "loss": 0.12}
        
        # 参数和返回值会自动保存到 metrics.json
    """
    import functools
    import inspect
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # 获取函数签名
        sig = inspect.signature(func)
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()
        
        # 记录参数
        log_params(**bound_args.arguments)
        
        # 执行函数
        result = func(*args, **kwargs)
        
        # 如果返回值是字典，记录为指标
        if isinstance(result, dict):
            log_metrics(**result)
        
        # 自动保存
        save()
        
        return result
    
    return wrapper


# 简化的 API
track = _global_tracker

