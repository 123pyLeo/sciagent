"""代码变更追踪模块 - 用于生成周报中的代码变更摘要"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

from .ui import print_info, print_warning, print_error


class CodeChangeTracker:
    """代码变更追踪器"""
    
    def __init__(self, workdir: Path):
        """
        初始化追踪器
        
        Args:
            workdir: 工作目录
        """
        self.workdir = workdir
        self.is_git_repo = self._check_git()
    
    def _check_git(self) -> bool:
        """检查是否是 Git 仓库"""
        git_dir = self.workdir / ".git"
        return git_dir.exists() and git_dir.is_dir()
    
    def get_git_changes(self, since_days: int = 7) -> Optional[Dict]:
        """
        获取 Git 变更记录
        
        Args:
            since_days: 统计最近几天
            
        Returns:
            变更信息字典，如果不是 Git 仓库则返回 None
        """
        if not self.is_git_repo:
            return None
        
        since_date = datetime.now() - timedelta(days=since_days)
        since_str = since_date.strftime('%Y-%m-%d')
        
        try:
            # 获取提交记录
            commits = self._get_commits(since_str)
            
            # 获取文件变更统计
            file_stats = self._get_file_stats(since_str)
            
            # 获取修改的文件列表
            changed_files = self._get_changed_files(since_str)
            
            return {
                'commits': commits,
                'file_stats': file_stats,
                'changed_files': changed_files,
                'has_changes': len(commits) > 0
            }
            
        except Exception as e:
            print_warning(f"获取 Git 变更失败: {e}")
            return None
    
    def _get_commits(self, since_date: str) -> List[Dict]:
        """获取提交记录"""
        try:
            result = subprocess.run(
                ['git', 'log', f'--since={since_date}', 
                 '--pretty=format:%H|%an|%ad|%s', '--date=short'],
                cwd=self.workdir,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                return []
            
            commits = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                parts = line.split('|', 3)
                if len(parts) == 4:
                    commits.append({
                        'hash': parts[0][:8],
                        'author': parts[1],
                        'date': parts[2],
                        'message': parts[3]
                    })
            
            return commits
            
        except Exception:
            return []
    
    def _get_file_stats(self, since_date: str) -> Dict[str, int]:
        """获取文件变更统计"""
        try:
            result = subprocess.run(
                ['git', 'diff', f'--since={since_date}', 
                 '--numstat', 'HEAD~1', 'HEAD'],
                cwd=self.workdir,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            total_additions = 0
            total_deletions = 0
            
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                parts = line.split('\t')
                if len(parts) >= 2:
                    try:
                        additions = int(parts[0]) if parts[0] != '-' else 0
                        deletions = int(parts[1]) if parts[1] != '-' else 0
                        total_additions += additions
                        total_deletions += deletions
                    except ValueError:
                        continue
            
            return {
                'additions': total_additions,
                'deletions': total_deletions,
                'total': total_additions + total_deletions
            }
            
        except Exception:
            return {'additions': 0, 'deletions': 0, 'total': 0}
    
    def _get_changed_files(self, since_date: str) -> List[str]:
        """获取变更的文件列表"""
        try:
            result = subprocess.run(
                ['git', 'diff', f'--since={since_date}', 
                 '--name-only', 'HEAD~1', 'HEAD'],
                cwd=self.workdir,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            files = [f for f in result.stdout.strip().split('\n') if f]
            
            # 按文件类型分类
            categorized = self._categorize_files(files)
            
            return categorized
            
        except Exception:
            return []
    
    def _categorize_files(self, files: List[str]) -> List[Dict]:
        """
        按文件类型分类
        
        Args:
            files: 文件路径列表
            
        Returns:
            分类后的文件信息
        """
        categories = {
            'model': [],      # 模型相关
            'data': [],       # 数据处理
            'loss': [],       # 损失函数
            'train': [],      # 训练脚本
            'config': [],     # 配置文件
            'other': []       # 其他
        }
        
        for file in files:
            file_lower = file.lower()
            
            # 分类逻辑
            if any(k in file_lower for k in ['model', 'net', 'arch']):
                categories['model'].append(file)
            elif any(k in file_lower for k in ['data', 'dataset', 'loader']):
                categories['data'].append(file)
            elif any(k in file_lower for k in ['loss', 'criterion']):
                categories['loss'].append(file)
            elif any(k in file_lower for k in ['train', 'main']):
                categories['train'].append(file)
            elif any(k in file_lower for k in ['config', 'yaml', 'json', '.cfg']):
                categories['config'].append(file)
            else:
                categories['other'].append(file)
        
        # 转换为列表格式
        result = []
        for category, file_list in categories.items():
            if file_list:
                result.append({
                    'category': category,
                    'files': file_list
                })
        
        return result
    
    def get_file_changes_by_mtime(
        self,
        since_days: int = 7,
        extensions: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        通过文件修改时间获取变更（不依赖 Git）
        
        Args:
            since_days: 统计最近几天
            extensions: 要检查的文件扩展名（如 ['.py', '.yaml']）
            
        Returns:
            变更的文件列表
        """
        if extensions is None:
            extensions = ['.py', '.yaml', '.yml', '.json', '.toml', '.sh']
        
        since_time = datetime.now() - timedelta(days=since_days)
        changed_files = []
        
        try:
            # 遍历工作目录
            for root, dirs, files in os.walk(self.workdir):
                # 跳过隐藏目录、虚拟环境、构建目录
                dirs[:] = [d for d in dirs if not d.startswith('.') 
                          and d not in [
                              'venv', 'env', 'light_env', 'virtualenv',  # 虚拟环境
                              '__pycache__', 'node_modules',              # 缓存
                              'build', 'dist', '.egg-info',               # 构建目录
                          ]]
                
                for file in files:
                    file_path = Path(root) / file
                    
                    # 检查扩展名
                    if file_path.suffix not in extensions:
                        continue
                    
                    # 检查修改时间
                    try:
                        mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                        if mtime >= since_time:
                            rel_path = file_path.relative_to(self.workdir)
                            changed_files.append({
                                'path': str(rel_path),
                                'mtime': mtime.strftime('%Y-%m-%d %H:%M'),
                                'size': file_path.stat().st_size
                            })
                    except Exception:
                        continue
            
            # 按修改时间排序
            changed_files.sort(key=lambda x: x['mtime'], reverse=True)
            
            return changed_files
            
        except Exception as e:
            print_error(f"获取文件变更失败: {e}")
            return []
    
    def get_code_diff_summary(self, since_days: int = 7) -> Optional[str]:
        """
        获取代码差异摘要（用于 AI 分析）
        
        Args:
            since_days: 统计最近几天
            
        Returns:
            差异摘要文本
        """
        if not self.is_git_repo:
            return None
        
        since_date = datetime.now() - timedelta(days=since_days)
        since_str = since_date.strftime('%Y-%m-%d')
        
        try:
            # 获取简要的 diff 统计
            result = subprocess.run(
                ['git', 'diff', f'--since={since_date}', '--stat', 'HEAD~1', 'HEAD'],
                cwd=self.workdir,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
            
            # 如果上面失败，尝试获取提交信息
            result = subprocess.run(
                ['git', 'log', f'--since={since_str}', 
                 '--pretty=format:%s', '--no-merges'],
                cwd=self.workdir,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0 and result.stdout.strip():
                messages = result.stdout.strip().split('\n')
                return '\n'.join(f"- {msg}" for msg in messages if msg)
            
            return None
            
        except Exception:
            return None


def generate_code_change_summary(
    workdir: Path,
    since_days: int = 7,
    use_ai: bool = False,
    llm_config: Optional[Dict] = None
) -> str:
    """
    生成代码变更摘要
    
    Args:
        workdir: 工作目录
        since_days: 统计最近几天
        use_ai: 是否使用 AI 总结
        llm_config: LLM 配置
        
    Returns:
        Markdown 格式的代码变更摘要
    """
    tracker = CodeChangeTracker(workdir)
    lines = []
    
    lines.append(f"## 📝 代码变更（最近 {since_days} 天）\n")
    
    # 尝试使用 Git
    git_changes = tracker.get_git_changes(since_days)
    
    if git_changes and git_changes['has_changes']:
        # Git 仓库且有变更
        commits = git_changes['commits']
        file_stats = git_changes['file_stats']
        changed_files = git_changes['changed_files']
        
        lines.append(f"**提交数量**: {len(commits)} 个\n")
        
        if file_stats['total'] > 0:
            lines.append(
                f"**代码变更**: +{file_stats['additions']} "
                f"-{file_stats['deletions']} 行\n"
            )
        
        lines.append("\n### 提交记录\n")
        for commit in commits[:10]:  # 最多显示 10 个
            lines.append(
                f"- `{commit['hash']}` [{commit['date']}] "
                f"{commit['message']}\n"
            )
        
        if changed_files:
            lines.append("\n### 修改的文件\n")
            for cat_info in changed_files:
                category = cat_info['category']
                files = cat_info['files']
                
                category_names = {
                    'model': '模型架构',
                    'data': '数据处理',
                    'loss': '损失函数',
                    'train': '训练脚本',
                    'config': '配置文件',
                    'other': '其他'
                }
                
                lines.append(f"\n**{category_names.get(category, category)}**:\n")
                for file in files[:5]:  # 每类最多5个
                    lines.append(f"- `{file}`\n")
        
        # 如果启用 AI，生成代码变更总结
        if use_ai and llm_config and llm_config.get('llm_api_key'):
            lines.append("\n### 🤖 代码变更总结\n")
            
            # 构建更丰富的上下文
            context_parts = []
            context_parts.append(f"提交数量: {len(commits)}")
            
            if commits:
                context_parts.append("\n提交信息:")
                for commit in commits[:5]:  # 前5个提交
                    context_parts.append(f"- {commit['message']}")
            
            if changed_files:
                context_parts.append("\n修改的文件:")
                for cat_info in changed_files[:3]:  # 前3个分类
                    category = cat_info['category']
                    files = cat_info['files'][:3]  # 每个分类前3个文件
                    context_parts.append(f"- {category}: {', '.join(files)}")
            
            change_context = '\n'.join(context_parts)
            
            try:
                from .agent_llm import AgentsLLM
                
                llm = AgentsLLM(
                    provider=llm_config.get('llm_provider'),
                    api_key=llm_config.get('llm_api_key'),
                    base_url=llm_config.get('llm_base_url'),
                    model=llm_config.get('llm_model'),
                    temperature=0.7
                )
                
                # 根据时间范围调整提示词
                time_context = "昨天相比前天" if since_days == 1 else (
                    "本月相比上月" if since_days >= 28 else "本周相比上周"
                )
                
                messages = [
                    {
                        "role": "system",
                        "content": "你是一个技术 Leader，需要审查代码提交并给出具体的技术细节总结，用于团队汇报和技术复盘。避免空话套话，要具体、可执行、有技术深度。"
                    },
                    {
                        "role": "user",
                        "content": f"请总结{time_context}的代码改进（3-5 条要点，每条具体说明技术实现）：\n\n{change_context}\n\n要求：\n1. 具体说明改了哪些文件的什么功能（不要泛泛而谈）\n2. 关键技术点：用了什么技术/框架/算法/设计模式\n3. 解决了什么具体问题（要有实际场景，不是'提升性能'这种空话）\n4. 如果是重构，说明具体的重构手段（如抽象类/工厂模式/依赖注入）\n5. 如果有性能优化，给出具体指标或改进点\n\n示例格式：\n• 模型架构：在 `model.py` 中引入多头注意力机制，替换原有的 LSTM 编码器\n• 数据处理：`dataloader.py` 增加动态批处理，减少 30% 内存占用\n• 训练优化：实现梯度累积（accumulation_steps=4），支持大 batch 训练"
                    }
                ]
                
                summary_chunks = []
                for chunk in llm.think(messages, temperature=0.5):
                    summary_chunks.append(chunk)
                
                lines.append("".join(summary_chunks) + "\n")
                
            except Exception as e:
                lines.append(f"*AI 总结失败: {e}*\n")
    
    else:
        # 不是 Git 仓库或无变更，使用文件修改时间
        lines.append("*Git 仓库未检测到变更，使用文件修改时间追踪*\n")
        
        file_changes = tracker.get_file_changes_by_mtime(since_days)
        
        if file_changes:
            lines.append(f"\n**修改/新增的文件**: {len(file_changes)} 个\n")
            lines.append("\n### 最近修改的文件\n")
            
            for file_info in file_changes[:20]:  # 最多显示 20 个
                lines.append(
                    f"- `{file_info['path']}` "
                    f"({file_info['mtime']})\n"
                )
            
            # 如果启用 AI，对文件修改也进行总结
            if use_ai and llm_config and llm_config.get('llm_api_key'):
                lines.append("\n### 🤖 代码变更总结\n")
                
                # 构建文件修改上下文
                context_parts = []
                context_parts.append(f"修改/新增文件数量: {len(file_changes)}")
                context_parts.append("\n主要修改的文件:")
                
                # 按文件类型分类
                file_by_type = {}
                for f in file_changes[:15]:  # 前15个文件
                    path = f['path']
                    file_lower = path.lower()
                    
                    # 简单分类
                    if any(k in file_lower for k in ['model', 'net', 'arch']):
                        file_type = '模型相关'
                    elif any(k in file_lower for k in ['data', 'dataset', 'loader']):
                        file_type = '数据处理'
                    elif any(k in file_lower for k in ['train', 'main']):
                        file_type = '训练脚本'
                    elif any(k in file_lower for k in ['config', 'yaml', 'json']):
                        file_type = '配置文件'
                    else:
                        file_type = '其他'
                    
                    if file_type not in file_by_type:
                        file_by_type[file_type] = []
                    file_by_type[file_type].append(path)
                
                for file_type, paths in file_by_type.items():
                    context_parts.append(f"- {file_type}: {', '.join(paths[:3])}")
                
                change_context = '\n'.join(context_parts)
                
                try:
                    from .agent_llm import AgentsLLM
                    
                    llm = AgentsLLM(
                        provider=llm_config.get('llm_provider'),
                        api_key=llm_config.get('llm_api_key'),
                        base_url=llm_config.get('llm_base_url'),
                        model=llm_config.get('llm_model'),
                        temperature=0.7
                    )
                    
                    # 根据时间范围调整提示词
                    time_context = "昨天相比前天" if since_days == 1 else (
                        "本月相比上月" if since_days >= 28 else "本周相比上周"
                    )
                    
                    messages = [
                        {
                            "role": "system",
                            "content": "你是一个技术 Leader，需要审查代码变更并给出具体的技术细节总结，用于团队汇报和技术复盘。避免空话套话，要具体、可执行、有技术深度。"
                        },
                        {
                            "role": "user",
                            "content": f"请总结{time_context}的代码工作（3-5 条要点，每条具体说明技术实现）：\n\n{change_context}\n\n要求：\n1. 具体说明改了/新增了哪些文件的什么功能（不要泛泛而谈）\n2. 关键技术点：用了什么技术/框架/算法\n3. 解决了什么具体问题（不是'提升可复现性'这种空话）\n4. 如果是重构，说明具体的重构手段\n5. 如果有性能优化，给出具体指标\n\n示例格式：\n• 新增 `code_tracker.py` - 实现基于 Git 和文件 mtime 的双模式变更追踪\n• 重构 `exporter.py` - 引入 ExperimentExporter 类统一历史数据导出接口\n• 优化 `cli.py` - 增加 daily/weekly/monthly 快捷命令，减少用户参数输入"
                        }
                    ]
                    
                    summary_chunks = []
                    for chunk in llm.think(messages, temperature=0.5):
                        summary_chunks.append(chunk)
                    
                    lines.append("".join(summary_chunks) + "\n")
                    
                except Exception as e:
                    lines.append(f"*AI 总结失败: {e}*\n")
        else:
            lines.append("\n*最近没有代码变更*\n")
    
    return "".join(lines)

