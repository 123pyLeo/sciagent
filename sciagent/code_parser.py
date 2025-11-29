"""
Python 代码配置提取模块

自动从训练脚本中提取配置参数，无需用户做任何修改。
支持：
- config = {...} 字典定义
- lr = 0.001 简单变量赋值
- 常见的超参数命名模式
"""

import ast
import re
from pathlib import Path
from typing import Dict, Any, Optional, List, Set


# 常见的超参数名称模式
COMMON_PARAM_PATTERNS = {
    # 学习率相关
    'lr', 'learning_rate', 'base_lr', 'init_lr', 'max_lr', 'min_lr',
    # 批次大小
    'batch_size', 'batch', 'bs', 'train_batch_size', 'eval_batch_size',
    # 训练轮数
    'epochs', 'num_epochs', 'max_epochs', 'n_epochs', 'total_epochs',
    # 模型架构
    'hidden_size', 'hidden_dim', 'num_layers', 'n_layers', 'num_heads',
    'embed_dim', 'embedding_dim', 'd_model', 'dim', 'channels',
    'hidden_dim_1', 'hidden_dim_2', 'hidden_dim_3',
    # 正则化
    'dropout', 'dropout_rate', 'drop_rate', 'weight_decay', 'l2_reg',
    # 优化器
    'momentum', 'beta1', 'beta2', 'eps', 'epsilon',
    # 其他常见参数
    'seed', 'random_seed', 'num_workers', 'num_classes', 'input_size',
    'max_length', 'max_len', 'seq_length', 'warmup_steps', 'warmup_epochs',
    'gradient_clip', 'clip_grad', 'accumulation_steps',
}

# 配置字典的常见名称
CONFIG_DICT_NAMES = {
    'config', 'cfg', 'args', 'params', 'hyperparams', 'hparams',
    'settings', 'options', 'opts', 'train_config', 'model_config',
}


class CodeConfigExtractor:
    """从 Python 代码中提取配置参数"""
    
    def __init__(self):
        self.extracted_params: Dict[str, Any] = {}
        self.config_dicts: Dict[str, Dict[str, Any]] = {}
    
    def extract_from_file(self, file_path: str) -> Dict[str, Any]:
        """
        从 Python 文件中提取配置参数
        
        Args:
            file_path: Python 文件路径
            
        Returns:
            提取的配置参数字典
        """
        try:
            path = Path(file_path)
            if not path.exists() or path.suffix != '.py':
                return {}
            
            code = path.read_text(encoding='utf-8', errors='ignore')
            return self.extract_from_code(code)
        except Exception:
            return {}
    
    def extract_from_code(self, code: str) -> Dict[str, Any]:
        """
        从 Python 代码字符串中提取配置参数
        
        Args:
            code: Python 代码字符串
            
        Returns:
            提取的配置参数字典
        """
        self.extracted_params = {}
        self.config_dicts = {}
        
        try:
            tree = ast.parse(code)
            self._visit_module(tree)
        except SyntaxError:
            # 如果 AST 解析失败，尝试用正则表达式
            self._extract_with_regex(code)
        
        # 合并结果：优先使用 config 字典中的值
        result = {}
        
        # 添加独立变量
        result.update(self.extracted_params)
        
        # 添加配置字典中的值（会覆盖同名的独立变量）
        for dict_name, dict_values in self.config_dicts.items():
            for key, value in dict_values.items():
                # 使用 dict_name.key 或直接 key
                if dict_name in CONFIG_DICT_NAMES:
                    result[key] = value
                else:
                    result[f"{dict_name}.{key}"] = value
        
        return result
    
    def _visit_module(self, tree: ast.Module) -> None:
        """遍历 AST 模块"""
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                self._handle_assign(node)
            elif isinstance(node, ast.AnnAssign):
                self._handle_ann_assign(node)
    
    def _handle_assign(self, node: ast.Assign) -> None:
        """处理赋值语句"""
        for target in node.targets:
            if isinstance(target, ast.Name):
                var_name = target.id
                value = self._eval_node(node.value)
                
                if value is not None:
                    # 检查是否是配置字典
                    if isinstance(value, dict) and var_name.lower() in CONFIG_DICT_NAMES:
                        self.config_dicts[var_name] = value
                    # 检查是否是常见的超参数名
                    elif var_name.lower() in COMMON_PARAM_PATTERNS:
                        self.extracted_params[var_name] = value
                    # 检查是否是类似超参数的命名（包含关键词）
                    elif self._is_param_like_name(var_name):
                        self.extracted_params[var_name] = value
    
    def _handle_ann_assign(self, node: ast.AnnAssign) -> None:
        """处理带注解的赋值语句"""
        if isinstance(node.target, ast.Name) and node.value:
            var_name = node.target.id
            value = self._eval_node(node.value)
            
            if value is not None:
                if var_name.lower() in COMMON_PARAM_PATTERNS or self._is_param_like_name(var_name):
                    self.extracted_params[var_name] = value
    
    def _eval_node(self, node: ast.expr) -> Any:
        """安全地评估 AST 节点的值"""
        try:
            if isinstance(node, ast.Constant):
                return node.value
            elif isinstance(node, ast.Num):  # Python 3.7 兼容
                return node.n
            elif isinstance(node, ast.Str):  # Python 3.7 兼容
                return node.s
            elif isinstance(node, ast.NameConstant):  # Python 3.7 兼容
                return node.value
            elif isinstance(node, ast.Dict):
                return self._eval_dict(node)
            elif isinstance(node, ast.List):
                return self._eval_list(node)
            elif isinstance(node, ast.Tuple):
                return self._eval_tuple(node)
            elif isinstance(node, ast.UnaryOp):
                if isinstance(node.op, ast.USub):
                    operand = self._eval_node(node.operand)
                    if operand is not None:
                        return -operand
            elif isinstance(node, ast.BinOp):
                # 处理简单的二元运算（如 1e-4）
                left = self._eval_node(node.left)
                right = self._eval_node(node.right)
                if left is not None and right is not None:
                    if isinstance(node.op, ast.Mult):
                        return left * right
                    elif isinstance(node.op, ast.Div):
                        return left / right
                    elif isinstance(node.op, ast.Add):
                        return left + right
                    elif isinstance(node.op, ast.Sub):
                        return left - right
                    elif isinstance(node.op, ast.Pow):
                        return left ** right
            elif isinstance(node, ast.Call):
                # 处理一些常见的函数调用
                if isinstance(node.func, ast.Attribute):
                    # torch.cuda.is_available() 等
                    return None  # 跳过函数调用
                elif isinstance(node.func, ast.Name):
                    # int(), float() 等
                    if node.func.id in ('int', 'float', 'str', 'bool'):
                        if node.args:
                            return self._eval_node(node.args[0])
            elif isinstance(node, ast.IfExp):
                # 三元表达式：x if condition else y
                # 返回两个可能的值中的一个（优先返回 body）
                body_val = self._eval_node(node.body)
                if body_val is not None:
                    return body_val
                return self._eval_node(node.orelse)
        except Exception:
            pass
        return None
    
    def _eval_dict(self, node: ast.Dict) -> Optional[Dict[str, Any]]:
        """评估字典字面量"""
        result = {}
        for key, value in zip(node.keys, node.values):
            if key is None:  # **kwargs 展开
                continue
            key_val = self._eval_node(key)
            val_val = self._eval_node(value)
            if key_val is not None and val_val is not None:
                result[str(key_val)] = val_val
        return result if result else None
    
    def _eval_list(self, node: ast.List) -> Optional[List[Any]]:
        """评估列表字面量"""
        result = []
        for elt in node.elts:
            val = self._eval_node(elt)
            if val is not None:
                result.append(val)
        return result if result else None
    
    def _eval_tuple(self, node: ast.Tuple) -> Optional[tuple]:
        """评估元组字面量"""
        result = []
        for elt in node.elts:
            val = self._eval_node(elt)
            if val is not None:
                result.append(val)
        return tuple(result) if result else None
    
    def _is_param_like_name(self, name: str) -> bool:
        """检查变量名是否像超参数"""
        name_lower = name.lower()
        
        # 包含常见关键词
        keywords = ['lr', 'rate', 'size', 'dim', 'num', 'max', 'min', 
                   'epoch', 'batch', 'hidden', 'layer', 'dropout', 
                   'decay', 'step', 'warmup', 'clip', 'embed']
        
        for keyword in keywords:
            if keyword in name_lower:
                return True
        
        return False
    
    def _extract_with_regex(self, code: str) -> None:
        """使用正则表达式提取（AST 解析失败时的备选方案）"""
        # 匹配简单的变量赋值：var_name = 0.001
        pattern = r'^(\w+)\s*=\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*(?:#.*)?$'
        
        for line in code.split('\n'):
            line = line.strip()
            match = re.match(pattern, line)
            if match:
                var_name = match.group(1)
                value_str = match.group(2)
                
                if var_name.lower() in COMMON_PARAM_PATTERNS or self._is_param_like_name(var_name):
                    try:
                        if '.' in value_str or 'e' in value_str.lower():
                            self.extracted_params[var_name] = float(value_str)
                        else:
                            self.extracted_params[var_name] = int(value_str)
                    except ValueError:
                        pass


def extract_config_from_script(script_path: str) -> Dict[str, Any]:
    """
    从 Python 训练脚本中提取配置参数
    
    Args:
        script_path: 脚本文件路径
        
    Returns:
        提取的配置参数字典
    """
    extractor = CodeConfigExtractor()
    return extractor.extract_from_file(script_path)


def extract_config_from_command(command: str, workdir: Path) -> Dict[str, Any]:
    """
    从命令中提取脚本路径并解析配置
    
    Args:
        command: 执行命令（如 "python train.py --lr 0.001"）
        workdir: 工作目录
        
    Returns:
        提取的配置参数字典
    """
    # 提取 Python 脚本路径
    match = re.search(r'python[3]?\s+([^\s]+\.py)', command)
    if not match:
        return {}
    
    script_name = match.group(1)
    script_path = workdir / script_name
    
    if not script_path.exists():
        # 尝试绝对路径
        script_path = Path(script_name)
    
    if script_path.exists():
        return extract_config_from_script(str(script_path))
    
    return {}


if __name__ == '__main__':
    # 测试
    test_code = '''
# 训练配置
config = {
    "input_size": 784,
    "hidden_dim_1": 256,
    "hidden_dim_2": 128,
    "learning_rate": 0.001,
    "batch_size": 64,
    "num_epochs": 10,
    "dropout_rate": 0.3,
}

# 独立变量
lr = 0.001
epochs = 100
batch_size = 32
hidden_size = 512

# 设备选择（三元表达式）
device = "cuda" if True else "cpu"
'''
    
    print("=" * 60)
    print("CodeConfigExtractor 测试")
    print("=" * 60)
    
    extractor = CodeConfigExtractor()
    result = extractor.extract_from_code(test_code)
    
    print("\n提取的配置参数:")
    for k, v in sorted(result.items()):
        print(f"  {k}: {v}")

