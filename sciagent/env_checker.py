"""环境检测模块"""

from __future__ import annotations

import platform
import sys
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import psutil

from .ui import print_success, print_error, print_warning, print_info


class EnvironmentChecker:
    """环境检测器"""

    def __init__(self):
        self.checks: List[Tuple[str, bool, Optional[str]]] = []

    def check_python_version(self, min_version: Tuple[int, int] = (3, 9)) -> bool:
        """检查 Python 版本"""
        current = sys.version_info[:2]
        meets_requirement = current >= min_version
        
        version_str = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        
        if meets_requirement:
            msg = f"Python {version_str}"
            self.checks.append(("Python 版本", True, msg))
            return True
        else:
            msg = f"Python {version_str} (需要 >= {min_version[0]}.{min_version[1]})"
            self.checks.append(("Python 版本", False, msg))
            return False

    def check_system_info(self) -> Dict[str, str]:
        """获取系统信息"""
        info = {
            "操作系统": platform.system(),
            "系统版本": platform.release(),
            "架构": platform.machine(),
            "处理器": platform.processor() or "Unknown",
        }
        
        self.checks.append(("系统信息", True, f"{info['操作系统']} {info['系统版本']}"))
        return info

    def check_memory(self, min_gb: float = 2.0) -> bool:
        """检查可用内存"""
        memory = psutil.virtual_memory()
        available_gb = memory.available / (1024 ** 3)
        total_gb = memory.total / (1024 ** 3)
        
        meets_requirement = available_gb >= min_gb
        msg = f"{available_gb:.1f}GB 可用 / {total_gb:.1f}GB 总共"
        
        if meets_requirement:
            self.checks.append(("可用内存", True, msg))
        else:
            self.checks.append(("可用内存", False, f"{msg} (推荐 >= {min_gb}GB)"))
        
        return meets_requirement

    def check_disk_space(self, path: Path, min_gb: float = 1.0) -> bool:
        """检查磁盘空间"""
        try:
            usage = psutil.disk_usage(str(path))
            free_gb = usage.free / (1024 ** 3)
            
            meets_requirement = free_gb >= min_gb
            msg = f"{free_gb:.1f}GB 可用空间"
            
            if meets_requirement:
                self.checks.append(("磁盘空间", True, msg))
            else:
                self.checks.append(("磁盘空间", False, f"{msg} (推荐 >= {min_gb}GB)"))
            
            return meets_requirement
        except Exception:
            self.checks.append(("磁盘空间", False, "无法检测"))
            return False

    def check_git_available(self) -> bool:
        """检查 Git 是否可用"""
        try:
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                self.checks.append(("Git", True, version))
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        self.checks.append(("Git", False, "未安装"))
        return False

    def check_command_available(self, command: str) -> bool:
        """检查命令是否可用"""
        try:
            result = subprocess.run(
                [command, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return False

    def check_dependencies(self) -> bool:
        """检查依赖包"""
        # pip包名 -> Python导入名的映射
        required_packages = {
            "pyyaml": "yaml",
            "rich": "rich",
            "questionary": "questionary",
            "psutil": "psutil"
        }
        all_available = True
        
        for pip_name, import_name in required_packages.items():
            try:
                __import__(import_name)
                self.checks.append((f"包: {pip_name}", True, "已安装"))
            except ImportError:
                self.checks.append((f"包: {pip_name}", False, "未安装"))
                all_available = False
        
        return all_available

    def run_all_checks(self, workdir: Path = Path.cwd()) -> bool:
        """运行所有检查"""
        self.checks.clear()
        
        all_passed = True
        
        # 基础检查
        if not self.check_python_version():
            all_passed = False
        
        self.check_system_info()
        
        if not self.check_memory():
            all_passed = False
        
        if not self.check_disk_space(workdir):
            all_passed = False
        
        # 工具检查
        self.check_git_available()
        
        # 依赖检查
        if not self.check_dependencies():
            all_passed = False
        
        return all_passed

    def print_results(self):
        """打印检查结果"""
        print_info("环境检测结果:")
        print()
        
        for name, passed, detail in self.checks:
            if passed:
                print_success(f"{name}: {detail}")
            elif detail and "推荐" in detail:
                print_warning(f"{name}: {detail}")
            else:
                print_error(f"{name}: {detail}")

    def get_summary(self) -> Dict[str, int]:
        """获取检查摘要"""
        passed = sum(1 for _, p, _ in self.checks if p)
        failed = sum(1 for _, p, _ in self.checks if not p)
        
        return {
            "total": len(self.checks),
            "passed": passed,
            "failed": failed
        }

