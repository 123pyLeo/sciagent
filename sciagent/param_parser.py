"""命令行参数自动解析模块"""

import re
from typing import Dict, Any, List
from pathlib import Path


def parse_command_params(command: str) -> Dict[str, Any]:
    """
    自动解析命令行参数
    
    Args:
        command: 完整的命令字符串
        
    Returns:
        解析出的参数字典
    """
    params = {}
    
    # 解析常见的参数格式：
    # 1. --arg value 或 --arg=value
    # 2. -a value
    # 3. --flag (布尔参数)
    
    # 匹配 --key value 或 --key=value
    long_arg_pattern = r'--([a-zA-Z][a-zA-Z0-9_-]*)[=\s]+([^\s-][^\s]*)'
    matches = re.findall(long_arg_pattern, command)
    for key, value in matches:
        params[key] = _parse_value(value)
    
    # 匹配 --flag (没有值的布尔参数)
    flag_pattern = r'--([a-zA-Z][a-zA-Z0-9_-]*)(?=\s|$)'
    flags = re.findall(flag_pattern, command)
    for flag in flags:
        if flag not in params:  # 避免覆盖已有值
            params[flag] = True
    
    # 匹配 -a value (短参数)
    short_arg_pattern = r'\s-([a-zA-Z])\s+([^\s-][^\s]*)'
    short_matches = re.findall(short_arg_pattern, command)
    for key, value in short_matches:
        params[f"_{key}"] = _parse_value(value)  # 短参数加下划线前缀
    
    return params


def _parse_value(value_str: str) -> Any:
    """
    智能解析参数值类型
    
    Args:
        value_str: 参数值字符串
        
    Returns:
        解析后的值（保持原类型）
    """
    value_str = value_str.strip()
    
    # 尝试解析为数字
    try:
        if '.' in value_str or 'e' in value_str.lower():
            return float(value_str)
        else:
            return int(value_str)
    except ValueError:
        pass
    
    # 布尔值
    if value_str.lower() in ['true', 'yes', 'y', '1']:
        return True
    if value_str.lower() in ['false', 'no', 'n', '0']:
        return False
    
    # None
    if value_str.lower() in ['none', 'null']:
        return None
    
    # 列表（逗号分隔）
    if ',' in value_str and not value_str.startswith('['):
        items = [_parse_value(item.strip()) for item in value_str.split(',')]
        return items
    
    # 默认返回字符串
    return value_str


def detect_config_files(command: str, workdir: Path) -> List[Path]:
    """
    自动检测命令中引用的配置文件
    
    Args:
        command: 完整的命令字符串
        workdir: 工作目录
        
    Returns:
        检测到的配置文件路径列表
    """
    config_files = []
    
    # 常见的配置文件扩展名
    config_extensions = ['.yaml', '.yml', '.json', '.toml', '.ini', '.cfg', '.conf']
    
    # 常见的配置参数名
    config_param_names = [
        'config', 'cfg', 'conf', 'settings', 'params', 'hparams', 
        'hyperparams', 'options', 'args'
    ]
    
    # 1. 从参数中查找（--config xxx.yaml）
    for param_name in config_param_names:
        pattern = rf'--{param_name}[=\s]+([^\s]+)'
        matches = re.findall(pattern, command)
        for match in matches:
            file_path = Path(match)
            if not file_path.is_absolute():
                file_path = workdir / file_path
            if file_path.exists() and file_path.suffix in config_extensions:
                config_files.append(file_path)
    
    # 2. 从命令中查找可能的配置文件名
    words = command.split()
    for word in words:
        if any(word.endswith(ext) for ext in config_extensions):
            file_path = Path(word)
            if not file_path.is_absolute():
                file_path = workdir / file_path
            if file_path.exists():
                config_files.append(file_path)
    
    # 3. 检查工作目录中的常见配置文件
    common_config_names = [
        'config.yaml', 'config.yml', 'config.json',
        'hparams.yaml', 'hparams.yml',
        'settings.yaml', 'settings.yml',
        'params.yaml', 'params.yml'
    ]
    
    for config_name in common_config_names:
        config_path = workdir / config_name
        if config_path.exists() and config_path not in config_files:
            # 只在命令中提到这个文件名时才自动添加
            if config_name in command or config_name.split('.')[0] in command:
                config_files.append(config_path)
    
    return config_files


def extract_python_args(command: str) -> Dict[str, Any]:
    """
    从 Python 命令中提取 argparse 风格的参数
    
    Args:
        command: Python 命令
        
    Returns:
        提取的参数字典
    """
    if 'python' not in command.lower():
        return {}
    
    # 提取 python script.py 后面的所有参数
    parts = command.split()
    
    # 找到 .py 文件的位置
    script_idx = -1
    for i, part in enumerate(parts):
        if part.endswith('.py'):
            script_idx = i
            break
    
    if script_idx == -1:
        return {}
    
    # 提取脚本参数部分
    args_part = ' '.join(parts[script_idx + 1:])
    
    return parse_command_params(args_part)

