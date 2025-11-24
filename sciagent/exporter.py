"""实验数据导出模块 - 用于生成周报、消融表格等"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from .ui import print_success, print_error, print_info, console
from .code_tracker import generate_code_change_summary


class ExperimentExporter:
    """实验数据导出器"""
    
    def __init__(self, state_dir: Path):
        """
        初始化导出器
        
        Args:
            state_dir: SciAgent 状态目录
        """
        self.state_dir = state_dir
        self.history_file = state_dir / "history.json"
        self.runs_dir = state_dir / "runs"
    
    def load_history(self) -> List[Dict[str, Any]]:
        """加载历史记录"""
        if not self.history_file.exists():
            return []
        
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('runs', [])
        except Exception as e:
            print_error(f"加载历史记录失败: {e}")
            return []
    
    def load_run_details(self, run_id: str) -> Optional[Dict[str, Any]]:
        """加载运行详细信息"""
        run_record_file = self.runs_dir / run_id / "run_record.json"
        if not run_record_file.exists():
            return None
        
        try:
            with open(run_record_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None
    
    def filter_runs(
        self,
        runs: List[Dict[str, Any]],
        name_pattern: Optional[str] = None,
        since_days: Optional[int] = None,
        metadata_filter: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """
        筛选运行记录
        
        Args:
            runs: 运行记录列表
            name_pattern: 名称模式（包含匹配）
            since_days: 最近几天内
            metadata_filter: 元数据筛选条件
            
        Returns:
            筛选后的运行记录
        """
        filtered = runs
        
        # 按名称筛选
        if name_pattern:
            filtered = [r for r in filtered if name_pattern in r.get('name', '')]
        
        # 按时间筛选
        if since_days is not None:
            # 使用 UTC 时间作为基准（因为记录的时间通常是 UTC）
            cutoff = datetime.utcnow() - timedelta(days=since_days)
            
            def is_within_timeframe(run):
                # 优先使用 start_time，fallback 到 ended_at（兼容旧格式）
                time_str = run.get('start_time') or run.get('ended_at', '')
                if not time_str:  # 跳过空字符串或 None
                    return False
                try:
                    # 去掉时区信息，统一用 naive datetime 比较
                    # 1. 去掉尾部的 'Z'（UTC 标识）
                    time_str = time_str.rstrip('Z')
                    
                    # 2. 去掉 '+XX:XX' 或 '-XX:XX' 时区偏移
                    # 找到 'T' 后面的第一个 '+' 或最后一个 '-'（时区标记）
                    if 'T' in time_str:
                        date_time_parts = time_str.split('T')
                        time_part = date_time_parts[1]
                        # 去掉时区偏移
                        if '+' in time_part:
                            time_part = time_part.split('+')[0]
                        elif time_part.count('-') > 0:
                            # 时间部分不应该有 '-'，如果有就是时区
                            time_part = time_part.split('-')[0]
                        time_str = f"{date_time_parts[0]}T{time_part}"
                    
                    # 3. 处理小数秒（保留最多6位）
                    if '.' in time_str:
                        base, frac = time_str.rsplit('.', 1)
                        time_str = f"{base}.{frac[:6]}"
                    
                    run_time = datetime.fromisoformat(time_str)
                    return run_time >= cutoff
                except (ValueError, TypeError):
                    # 时间格式错误，跳过这条记录
                    return False
            
            filtered = [r for r in filtered if is_within_timeframe(r)]
        
        # 按元数据筛选
        if metadata_filter:
            def matches_metadata(run):
                run_metadata = run.get('metadata', {})
                return all(
                    run_metadata.get(k) == v 
                    for k, v in metadata_filter.items()
                )
            filtered = [r for r in filtered if matches_metadata(r)]
        
        return filtered
    
    def generate_summary(
        self,
        since_days: int = 7,
        name_pattern: Optional[str] = None,
        include_code_changes: bool = True,
        use_ai_for_code: bool = False,
        llm_config: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        生成周报摘要
        
        Args:
            since_days: 最近几天（默认7天）
            name_pattern: 名称筛选
            
        Returns:
            Markdown 格式的摘要
        """
        runs = self.load_history()
        
        # 筛选
        filtered = self.filter_runs(runs, name_pattern=name_pattern, since_days=since_days)
        
        if not filtered:
            return f"# 实验摘要\n\n最近 {since_days} 天内没有实验记录。\n"
        
        # 排序（按时间）
        filtered.sort(key=lambda r: r.get('start_time', ''), reverse=True)
        
        # 生成摘要
        lines = []
        lines.append(f"# 实验摘要（最近 {since_days} 天）\n")
        lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        
        # 代码变更部分（如果启用）
        if include_code_changes:
            try:
                # 获取工作目录（从 state_dir 推导）
                workdir = self.state_dir.parent
                code_summary = generate_code_change_summary(
                    workdir,
                    since_days=since_days,
                    use_ai=use_ai_for_code,
                    llm_config=llm_config
                )
                lines.append("\n" + code_summary + "\n")
                lines.append("---\n")
            except Exception as e:
                print_info(f"代码变更追踪跳过: {e}")
        
        lines.append(f"\n**实验数量**: {len(filtered)} 个\n")
        
        # 统计（兼容 completed 和 succeeded）
        completed = sum(1 for r in filtered if r.get('status') in ['completed', 'succeeded'])
        failed = sum(1 for r in filtered if r.get('status') == 'failed')
        
        lines.append(f"**完成**: {completed} 个 | **失败**: {failed} 个\n")
        lines.append("\n---\n")
        
        # 详细列表
        lines.append("\n## 实验列表\n")
        
        for i, run in enumerate(filtered, 1):
            name = run.get('name', 'unnamed')
            run_id = run.get('run_id', 'N/A')[:12]
            status = run.get('status', 'unknown')
            # 优先使用 start_time，fallback 到 ended_at
            start_time = run.get('start_time') or run.get('ended_at', 'N/A')
            primary_metric = run.get('primary_metric_value', 'N/A')
            
            status_emoji = "✅" if status in ['completed', 'succeeded'] else "❌" if status == "failed" else "⏸️"
            
            lines.append(f"\n### {i}. {name} {status_emoji}\n")
            lines.append(f"- **ID**: `{run_id}`\n")
            lines.append(f"- **时间**: {start_time}\n")
            lines.append(f"- **状态**: {status}\n")
            
            if primary_metric != 'N/A':
                metric_name = run.get('primary_metric', 'metric')
                lines.append(f"- **{metric_name}**: {primary_metric}\n")
            
            # 元数据
            metadata = run.get('metadata', {})
            if metadata:
                lines.append(f"- **配置**: {', '.join(f'{k}={v}' for k, v in metadata.items())}\n")
            
            # 指标
            metrics = run.get('metrics', {})
            if metrics:
                metrics_str = ', '.join(f'{k}={v:.4f}' if isinstance(v, float) else f'{k}={v}' 
                                       for k, v in metrics.items())
                lines.append(f"- **指标**: {metrics_str}\n")
        
        # 最佳结果
        if completed > 0:
            lines.append("\n---\n")
            lines.append("\n## 最佳结果\n")
            
            completed_runs = [r for r in filtered if r.get('status') in ['completed', 'succeeded']]
            if completed_runs:
                # 找到最佳
                best = max(
                    completed_runs, 
                    key=lambda r: r.get('primary_metric_value', float('-inf'))
                )
                
                lines.append(f"\n- **实验**: {best.get('name')}\n")
                
                # 智能显示指标
                metric_name = best.get('primary_metric')
                metric_value = best.get('primary_metric_value')
                
                if metric_name and metric_value is not None:
                    # 有主要指标，直接显示
                    lines.append(f"- **{metric_name}**: {metric_value}\n")
                else:
                    # 没有主要指标，从 metrics 中智能选择
                    metrics = best.get('metrics', {})
                    if metrics:
                        # 按优先级查找常见指标
                        for common_metric in ['accuracy', 'final_accuracy', 'f1_score', 'f1', 'auc', 'loss', 'final_loss']:
                            if common_metric in metrics:
                                value = metrics[common_metric]
                                if isinstance(value, float):
                                    lines.append(f"- **{common_metric}**: {value:.6f}\n")
                                else:
                                    lines.append(f"- **{common_metric}**: {value}\n")
                                break
                        else:
                            # 没有常见指标，显示第一个
                            first_key = list(metrics.keys())[0]
                            value = metrics[first_key]
                            if isinstance(value, float):
                                lines.append(f"- **{first_key}**: {value:.6f}\n")
                            else:
                                lines.append(f"- **{first_key}**: {value}\n")
                
                best_metadata = best.get('metadata', {})
                if best_metadata:
                    lines.append(f"- **配置**: {', '.join(f'{k}={v}' for k, v in best_metadata.items())}\n")
        
        # AI 生成的"本周概览"和"下周计划"（如果启用 AI）
        if use_ai_for_code and llm_config and llm_config.get('llm_api_key'):
            lines.append("\n---\n")
            
            # 动态调整标题
            if since_days == 1:
                overview_title = "今日工作概览"
            elif since_days >= 28:
                overview_title = "本月工作概览"
            else:
                overview_title = "本周工作概览"
            
            lines.append(f"\n## 🎯 {overview_title}\n")
            
            try:
                from .agent_llm import AgentsLLM
                from .code_tracker import CodeChangeTracker
                
                llm = AgentsLLM(
                    provider=llm_config.get('llm_provider'),
                    api_key=llm_config.get('llm_api_key'),
                    base_url=llm_config.get('llm_base_url'),
                    model=llm_config.get('llm_model'),
                    temperature=0.7
                )
                
                # 构造详细的实验上下文
                time_period = "今天" if since_days == 1 else f"最近 {since_days} 天"
                summary_context = f"## {time_period}实验情况\n"
                summary_context += f"实验数量：{len(filtered)} 个（完成 {completed} 个，失败 {failed} 个）\n"
                
                # 获取最佳结果和指标
                if completed > 0:
                    # 智能获取最佳指标
                    best_metric_name = best.get('primary_metric')
                    best_metric_value = best.get('primary_metric_value')
                    
                    if not best_metric_name or best_metric_value is None:
                        # 从 metrics 中智能选择
                        metrics = best.get('metrics', {})
                        for common in ['accuracy', 'final_accuracy', 'f1_score', 'f1', 'auc']:
                            if common in metrics:
                                best_metric_name = common
                                best_metric_value = metrics[common]
                                break
                    
                    if best_metric_name and best_metric_value is not None:
                        summary_context += f"\n最佳结果：{best.get('name')} - {best_metric_name}={best_metric_value}\n"
                    else:
                        summary_context += f"\n最佳结果：{best.get('name')}\n"
                
                # 添加详细的实验信息（包括参数和指标）
                summary_context += "\n实验详情（前5个）：\n"
                for i, run in enumerate(filtered[:5], 1):
                    summary_context += f"\n{i}. {run.get('name')} [{run.get('status')}]\n"
                    
                    # 添加实际的指标（重要！让 AI 看到真实数据）
                    metrics = run.get('metrics', {})
                    if metrics:
                        # 优先显示常见指标
                        important_metrics = {}
                        for key in ['accuracy', 'final_accuracy', 'loss', 'final_loss', 'f1_score', 'auc']:
                            if key in metrics:
                                important_metrics[key] = metrics[key]
                        
                        # 如果有重要指标，显示它们
                        if important_metrics:
                            metric_str = ', '.join(f"{k}={v:.4f}" if isinstance(v, float) else f"{k}={v}" 
                                                  for k, v in important_metrics.items())
                            summary_context += f"   指标: {metric_str}\n"
                        else:
                            # 否则显示前3个指标
                            metric_str = ', '.join(f"{k}={v:.4f}" if isinstance(v, float) else f"{k}={v}" 
                                                  for k, v in list(metrics.items())[:3])
                            summary_context += f"   指标: {metric_str}\n"
                    
                    # 添加关键参数
                    metadata = run.get('metadata', {})
                    if metadata:
                        param_str = ', '.join(f"{k}={v}" for k, v in list(metadata.items())[:3])
                        summary_context += f"   参数: {param_str}\n"
                
                # 如果有多个完成的实验，添加关键指标对比
                if completed > 1:
                    completed_runs = [r for r in filtered if r.get('status') in ['completed', 'succeeded']][:5]
                    if completed_runs:
                        # 找出所有实验中存在的常见指标
                        summary_context += f"\n关键指标对比：\n"
                        for metric_name in ['final_accuracy', 'accuracy', 'final_loss', 'loss']:
                            values = []
                            for run in completed_runs:
                                metrics = run.get('metrics', {})
                                if metric_name in metrics:
                                    values.append((run.get('name'), metrics[metric_name]))
                            
                            if values:
                                summary_context += f"\n{metric_name}:\n"
                                for name, value in values[:3]:
                                    val_str = f"{value:.4f}" if isinstance(value, float) else str(value)
                                    summary_context += f"  - {name}: {val_str}\n"
                                break  # 只显示第一个找到的关键指标
                
                # 添加代码变更信息（如果有）
                if include_code_changes:
                    workdir = self.state_dir.parent
                    tracker = CodeChangeTracker(workdir)
                    git_changes = tracker.get_git_changes(since_days)
                    
                    if git_changes and git_changes['has_changes']:
                        summary_context += f"\n## 代码变更情况\n"
                        summary_context += f"提交数量：{len(git_changes['commits'])} 个\n"
                        summary_context += "提交信息：\n"
                        for commit in git_changes['commits'][:5]:
                            summary_context += f"- {commit['message']}\n"
                        
                        if git_changes['changed_files']:
                            summary_context += "\n修改的文件类型：\n"
                            for cat_info in git_changes['changed_files'][:3]:
                                summary_context += f"- {cat_info['category']}: {len(cat_info['files'])} 个文件\n"
                
                # 根据时间范围调整提示词
                time_comparison = "今天相比昨天" if since_days == 1 else (
                    "本月相比上月" if since_days >= 28 else "本周相比上周"
                )
                
                if include_code_changes and git_changes and git_changes['has_changes']:
                    overview_prompt = f"请用 2-3 句话总结{time_comparison}的工作进展和关键成果（包括代码改进和实验结果）："
                else:
                    overview_prompt = f"请用 2-3 句话总结{time_comparison}的工作进展和关键成果："
                
                messages = [
                    {
                        "role": "system",
                        "content": """你是实验数据分析专家。**严格要求**：
1. 必须详细分析提供的实际指标数据（accuracy, loss等）
2. 必须对比不同实验的配置和效果
3. 引用具体数值必须来自提供的数据，不要编造
4. 如果看到多组实验，分析参数对结果的影响"""
                    },
                    {
                        "role": "user",
                        "content": f"""{overview_prompt}

**实际数据**：
{summary_context}

**总结要求**（200-300字，3-4段）：

**第1段：整体概况**
- 实验数量、完成/失败情况
- 最佳结果及其配置（引用实际指标值）

**第2段：参数影响分析**
- 分析不同参数配置对结果的影响
- 对比具体实验（如"实验X（lr=A）得到accuracy=B，实验Y（lr=C）得到accuracy=D"）
- 找出规律或趋势

**第3段：关键发现**
- 哪些参数配置效果好
- 哪些参数配置效果差
- 最优配置的特征

**必须做到**：
- ✅ 引用至少3个具体的指标数值
- ✅ 对比至少2组实验
- ✅ 分析参数对结果的影响
- ✅ 指出最佳和最差配置

**禁止**：
- ❌ 说"所有实验均为hack"这种无意义的话
- ❌ 说"缺乏数据无法分析"（数据已提供）
- ❌ 编造未出现的数字
- ❌ 只说"完成了X个实验"而不分析结果

请用3-4个自然段详细总结："""
                    }
                ]
                
                overview_chunks = []
                for chunk in llm.think(messages, temperature=0.7):
                    overview_chunks.append(chunk)
                
                lines.append("".join(overview_chunks) + "\n")
                
                # 生成下周/明日/下月计划（根据时间范围）
                if since_days == 1:
                    next_period = "明天"
                elif since_days >= 28:  # 月度报告
                    next_period = "下月"
                else:  # 周报或其他
                    next_period = "下周"
                
                lines.append(f"\n## 📋 {next_period}计划建议\n")
                
                plan_prompt = f"根据以下实验情况，请给出 3 条具体的{next_period}工作建议（每条一句话）："
                
                plan_messages = [
                    {
                        "role": "system",
                        "content": """你是实验规划助手。**严格要求**：
1. 建议必须基于实际实验结果和参数配置
2. 分析哪些参数有效、哪些无效，针对性提出改进
3. 给出具体的参数值范围建议
4. 建议要具体、可执行、有明确目标"""
                    },
                    {
                        "role": "user",
                        "content": f"""{plan_prompt}

**实际数据**：
{summary_context}

**建议要求**（3-5条）：

**基于以下分析提出建议**：
1. 哪些参数配置效果好？为什么？
2. 哪些参数配置效果差？应该避免什么？
3. 还有哪些参数范围值得尝试？
4. 如何在最佳配置附近进一步优化？

**格式要求**：
- 每条建议包含：具体动作 + 具体参数值 + 预期目标
- 例如："测试 batch_size=128（当前最佳64的2倍），验证是否能进一步提升 final_accuracy"
- 例如："降低 lr 至 0.005-0.01 范围（当前0.09过大），减少训练不稳定性"

**必须做到**：
- ✅ 引用实际尝试过的参数值
- ✅ 基于实验结果给出针对性建议
- ✅ 说明为什么这样调整（基于观察到的现象）
- ✅ 给出具体的数值建议

**禁止**：
- ❌ 建议"在hack参数附近搜索"这种无意义的话
- ❌ 说"测试hack的轻微扰动"
- ❌ 不基于实际结果的空泛建议

请用bullet list格式输出（3-5条具体建议）："""
                    }
                ]
                
                plan_chunks = []
                for chunk in llm.think(plan_messages, temperature=0.8):
                    plan_chunks.append(chunk)
                
                lines.append("".join(plan_chunks) + "\n")
                
            except Exception as e:
                lines.append(f"*AI 总结生成失败: {e}*\n")
        
        return "".join(lines)
    
    def generate_table(
        self,
        name_pattern: Optional[str] = None,
        columns: Optional[List[str]] = None,
        format: str = 'markdown'
    ) -> str:
        """
        生成消融表格
        
        Args:
            name_pattern: 名称筛选（如 'ablation_'）
            columns: 要显示的列（元数据键或指标键）
            format: 输出格式 ('markdown' 或 'latex')
            
        Returns:
            表格字符串
        """
        runs = self.load_history()
        
        # 筛选
        filtered = self.filter_runs(runs, name_pattern=name_pattern)
        
        if not filtered:
            return "没有匹配的实验记录。\n"
        
        # 自动检测列（如果未指定）
        if not columns:
            # 收集所有元数据和指标的键
            all_keys = set()
            for run in filtered:
                all_keys.update(run.get('metadata', {}).keys())
                all_keys.update(run.get('metrics', {}).keys())
            columns = sorted(all_keys)
        
        # 生成表格
        if format == 'latex':
            return self._generate_latex_table(filtered, columns)
        else:
            return self._generate_markdown_table(filtered, columns)
    
    def _generate_markdown_table(
        self,
        runs: List[Dict[str, Any]],
        columns: List[str]
    ) -> str:
        """生成 Markdown 表格"""
        lines = []
        
        # 表头
        header = ['实验名称'] + columns
        lines.append('| ' + ' | '.join(header) + ' |')
        lines.append('|' + '|'.join(['---'] * len(header)) + '|')
        
        # 数据行
        for run in runs:
            name = run.get('name', 'unnamed')
            metadata = run.get('metadata', {})
            metrics = run.get('metrics', {})
            
            row = [name]
            for col in columns:
                # 先从元数据找，再从指标找
                value = metadata.get(col) or metrics.get(col, '-')
                if isinstance(value, float):
                    value = f"{value:.4f}"
                row.append(str(value))
            
            lines.append('| ' + ' | '.join(row) + ' |')
        
        return '\n'.join(lines)
    
    def _generate_latex_table(
        self,
        runs: List[Dict[str, Any]],
        columns: List[str]
    ) -> str:
        """生成 LaTeX 表格"""
        lines = []
        
        # 表格开始
        col_format = 'l' + 'c' * len(columns)
        lines.append('\\begin{table}[h]')
        lines.append('\\centering')
        lines.append(f'\\begin{{tabular}}{{{col_format}}}')
        lines.append('\\hline')
        
        # 表头
        header = ['实验名称'] + columns
        lines.append(' & '.join(header) + ' \\\\')
        lines.append('\\hline')
        
        # 数据行
        for run in runs:
            name = run.get('name', 'unnamed').replace('_', '\\_')
            metadata = run.get('metadata', {})
            metrics = run.get('metrics', {})
            
            row = [name]
            for col in columns:
                value = metadata.get(col) or metrics.get(col, '-')
                if isinstance(value, float):
                    value = f"{value:.4f}"
                row.append(str(value))
            
            lines.append(' & '.join(row) + ' \\\\')
        
        lines.append('\\hline')
        lines.append('\\end{tabular}')
        lines.append('\\caption{实验结果对比}')
        lines.append('\\label{tab:results}')
        lines.append('\\end{table}')
        
        return '\n'.join(lines)


def export_summary(
    state_dir: Path,
    since_days: int = 7,
    name_pattern: Optional[str] = None,
    output_file: Optional[Path] = None,
    include_code_changes: bool = True,
    use_ai_for_code: bool = False,
    llm_config: Optional[Dict[str, Any]] = None
) -> str:
    """
    导出实验摘要
    
    Args:
        state_dir: 状态目录
        since_days: 最近几天
        name_pattern: 名称筛选
        output_file: 输出文件路径
        
    Returns:
        摘要内容
    """
    exporter = ExperimentExporter(state_dir)
    summary = exporter.generate_summary(
        since_days,
        name_pattern,
        include_code_changes=include_code_changes,
        use_ai_for_code=use_ai_for_code,
        llm_config=llm_config
    )
    
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(summary)
        print_success(f"摘要已保存到: {output_file}")
    
    return summary


def export_table(
    state_dir: Path,
    name_pattern: Optional[str] = None,
    columns: Optional[List[str]] = None,
    format: str = 'markdown',
    output_file: Optional[Path] = None
) -> str:
    """
    导出消融表格
    
    Args:
        state_dir: 状态目录
        name_pattern: 名称筛选
        columns: 列名列表
        format: 输出格式
        output_file: 输出文件路径
        
    Returns:
        表格内容
    """
    exporter = ExperimentExporter(state_dir)
    table = exporter.generate_table(name_pattern, columns, format)
    
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(table)
        print_success(f"表格已保存到: {output_file}")
    
    return table

