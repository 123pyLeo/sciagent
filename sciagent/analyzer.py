"""AI 驱动的实验分析模块"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Any

from .agent_llm import AgentsLLM
from .ui import print_info, print_success, print_error, print_section_header, console


class ExperimentAnalyzer:
    """实验分析器 - 使用 AI 分析实验结果并提供建议"""
    
    def __init__(
        self,
        enable_ai: bool = True,
        llm_config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化分析器
        
        Args:
            enable_ai: 是否启用 AI 分析功能
            llm_config: LLM 配置字典（provider, api_key, model, base_url）
        """
        self.enable_ai = enable_ai
        self.llm: Optional[AgentsLLM] = None
        
        if enable_ai:
            try:
                # 如果提供了配置，使用配置；否则从环境变量读取
                if llm_config:
                    self.llm = AgentsLLM(
                        provider=llm_config.get('llm_provider'),
                        api_key=llm_config.get('llm_api_key'),
                        base_url=llm_config.get('llm_base_url'),
                        model=llm_config.get('llm_model'),
                        temperature=0.7
                    )
                else:
                    self.llm = AgentsLLM(temperature=0.7)
                
                print_success(f"✓ AI 分析已启用 (提供商: {self.llm.provider}, 模型: {self.llm.model})")
            except Exception as e:
                print_error(f"✗ 无法初始化 AI 模型: {e}")
                print_info("ℹ 将使用基础分析功能（不含 AI）")
                print_info("ℹ 提示: 运行 'sciagent init' 配置 AI 功能")
                self.enable_ai = False
    
    def analyze_run(
        self,
        run_record: Dict[str, Any],
        history: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        分析单次运行结果
        
        Args:
            run_record: 运行记录
            history: 历史运行记录（可选）
            
        Returns:
            分析报告文本
        """
        if not self.enable_ai or not self.llm:
            return self._basic_analysis(run_record)
        
        try:
            return self._ai_analysis(run_record, history)
        except Exception as e:
            print_error(f"AI 分析失败: {e}")
            print_info("使用基础分析...")
            return self._basic_analysis(run_record)
    
    def _basic_analysis(self, run_record: Dict[str, Any]) -> str:
        """基础分析（不使用 AI）"""
        analysis = []
        
        # 提取关键信息
        metrics = run_record.get("metrics", {})
        status = run_record.get("status", "unknown")
        
        analysis.append("## 📊 实验分析\n")
        
        # 状态分析
        if status == "completed":
            analysis.append("✅ **运行状态**: 成功完成\n")
        elif status == "failed":
            analysis.append("❌ **运行状态**: 运行失败\n")
        else:
            analysis.append(f"⚠️  **运行状态**: {status}\n")
        
        # 指标分析
        if metrics:
            analysis.append("\n### 指标概览\n")
            for key, value in metrics.items():
                analysis.append(f"- **{key}**: {value}\n")
        
        # 基础建议
        analysis.append("\n### 💡 建议\n")
        analysis.append("1. 检查日志文件了解详细执行情况\n")
        analysis.append("2. 对比历史运行找出性能差异\n")
        analysis.append("3. 考虑调整超参数进行优化\n")
        
        return "".join(analysis)
    
    def _ai_analysis(
        self,
        run_record: Dict[str, Any],
        history: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """AI 驱动的深度分析"""
        print_info("正在使用 AI 分析实验结果...")
        
        # 构建提示词
        prompt = self._build_analysis_prompt(run_record, history)
        
        messages = [
            {
                "role": "system",
                "content": (
                    "你是一个专业的机器学习实验分析专家。"
                    "你需要分析实验结果，找出问题，并提供具体可行的改进建议。"
                    "你的建议应该：\n"
                    "1. 基于实验数据，有理有据\n"
                    "2. 提供具体的参数调整建议\n"
                    "3. 指出可能存在的问题\n"
                    "4. 给出下一步实验方向\n"
                    "请用中文回答，使用 Markdown 格式。"
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        # 流式获取 AI 响应
        analysis_chunks = []
        console.print("\n[cyan]🤖 AI 分析中...[/cyan]\n")
        
        for chunk in self.llm.think(messages):
            analysis_chunks.append(chunk)
        
        console.print()
        
        return "".join(analysis_chunks)
    
    def _build_analysis_prompt(
        self,
        run_record: Dict[str, Any],
        history: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """构建分析提示词"""
        prompt_parts = []
        
        prompt_parts.append("请分析以下实验运行结果：\n\n")
        
        # 基本信息
        prompt_parts.append("## 实验信息\n")
        prompt_parts.append(f"- 运行名称: {run_record.get('name', 'unnamed')}\n")
        prompt_parts.append(f"- 运行状态: {run_record.get('status', 'unknown')}\n")
        prompt_parts.append(f"- 开始时间: {run_record.get('start_time', 'N/A')}\n")
        
        if run_record.get('command'):
            prompt_parts.append(f"- 执行命令: {run_record['command']}\n")
        
        # 配置信息
        if run_record.get('config'):
            prompt_parts.append("\n## 配置参数\n")
            prompt_parts.append("```json\n")
            prompt_parts.append(json.dumps(run_record['config'], indent=2, ensure_ascii=False))
            prompt_parts.append("\n```\n")
        
        # 元数据
        if run_record.get('metadata'):
            prompt_parts.append("\n## 元数据\n")
            for key, value in run_record['metadata'].items():
                prompt_parts.append(f"- {key}: {value}\n")
        
        # 指标
        if run_record.get('metrics'):
            prompt_parts.append("\n## 实验指标\n")
            for key, value in run_record['metrics'].items():
                prompt_parts.append(f"- {key}: {value}\n")
        
        # 历史对比
        if history and len(history) > 0:
            prompt_parts.append("\n## 历史对比\n")
            prompt_parts.append("最近 3 次运行的主要指标对比：\n\n")
            
            for i, hist_run in enumerate(history[-3:], 1):
                hist_metrics = hist_run.get('metrics', {})
                primary_metric = hist_run.get('primary_metric_value', 'N/A')
                prompt_parts.append(
                    f"{i}. {hist_run.get('name', 'unnamed')}: "
                    f"主要指标={primary_metric}\n"
                )
        
        # 分析要求
        prompt_parts.append("\n## 请提供以下分析：\n")
        prompt_parts.append("1. **结果评估**: 评价本次实验的表现如何\n")
        prompt_parts.append("2. **问题诊断**: 指出可能存在的问题（如果有）\n")
        prompt_parts.append("3. **参数调优建议**: 具体说明哪些参数应该如何调整\n")
        prompt_parts.append("4. **下一步实验方向**: 建议接下来应该尝试什么\n")
        
        if history:
            prompt_parts.append("5. **与历史对比**: 相比历史运行有何改进或退步\n")
        
        return "".join(prompt_parts)
    
    def suggest_next_experiments(
        self,
        current_run: Dict[str, Any],
        num_suggestions: int = 3
    ) -> List[Dict[str, str]]:
        """
        建议下一步实验
        
        Args:
            current_run: 当前运行记录
            num_suggestions: 建议数量
            
        Returns:
            实验建议列表
        """
        if not self.enable_ai or not self.llm:
            return self._basic_suggestions(current_run, num_suggestions)
        
        try:
            return self._ai_suggestions(current_run, num_suggestions)
        except Exception as e:
            print_error(f"生成建议失败: {e}")
            return self._basic_suggestions(current_run, num_suggestions)
    
    def _basic_suggestions(
        self,
        current_run: Dict[str, Any],
        num_suggestions: int
    ) -> List[Dict[str, str]]:
        """基础建议（不使用 AI）"""
        suggestions = [
            {
                "title": "调整学习率",
                "description": "尝试降低或提高学习率，观察收敛速度的变化",
                "command_hint": "--lr 0.001 或 --lr 0.0001"
            },
            {
                "title": "增加训练轮数",
                "description": "如果模型还在改进，可以延长训练时间",
                "command_hint": "--epochs 200"
            },
            {
                "title": "调整批次大小",
                "description": "更大的 batch size 可能带来更稳定的训练",
                "command_hint": "--batch-size 64"
            }
        ]
        
        return suggestions[:num_suggestions]
    
    def _ai_suggestions(
        self,
        current_run: Dict[str, Any],
        num_suggestions: int
    ) -> List[Dict[str, str]]:
        """AI 生成的实验建议"""
        print_info("正在生成实验建议...")
        
        prompt = f"""基于以下实验结果，请提供 {num_suggestions} 个具体的下一步实验建议：

实验信息：
- 运行名称: {current_run.get('name', 'unnamed')}
- 运行状态: {current_run.get('status', 'unknown')}
- 指标: {json.dumps(current_run.get('metrics', {}), ensure_ascii=False)}
- 配置: {json.dumps(current_run.get('config', {}), ensure_ascii=False)}

请以 JSON 格式返回建议列表，每个建议包含：
- title: 建议标题
- description: 详细描述
- command_hint: 命令行参数提示

示例格式：
[
  {{
    "title": "调整学习率",
    "description": "当前学习率可能过高，建议降低到 0.0001",
    "command_hint": "--lr 0.0001"
  }}
]

请只返回 JSON 数组，不要有其他文字。"""
        
        messages = [
            {
                "role": "system",
                "content": "你是一个机器学习实验设计专家。请根据实验结果提供具体可行的下一步实验建议。"
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        response_text = "".join(self.llm.think(messages))
        
        # 尝试解析 JSON
        try:
            # 提取 JSON 部分
            import re
            json_match = re.search(r'\[[\s\S]*\]', response_text)
            if json_match:
                suggestions = json.loads(json_match.group())
                return suggestions[:num_suggestions]
        except Exception as e:
            print_error(f"解析建议失败: {e}")
        
        # 如果解析失败，返回基础建议
        return self._basic_suggestions(current_run, num_suggestions)


def analyze_run_from_file(
    run_record_path: Path,
    history_path: Optional[Path] = None,
    enable_ai: bool = True,
    config_path: Optional[Path] = None
) -> str:
    """
    从文件分析运行记录
    
    Args:
        run_record_path: 运行记录文件路径
        history_path: 历史记录文件路径
        enable_ai: 是否启用 AI
        config_path: SciAgent 配置文件路径（包含 LLM 配置）
        
    Returns:
        分析报告
    """
    # 读取运行记录
    with open(run_record_path, 'r', encoding='utf-8') as f:
        run_record = json.load(f)
    
    # 读取历史记录（如果存在）
    history = None
    if history_path and history_path.exists():
        with open(history_path, 'r', encoding='utf-8') as f:
            history_data = json.load(f)
            history = history_data.get('runs', [])
    
    # 读取 LLM 配置（如果存在）
    llm_config = None
    if config_path and config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # 提取 LLM 相关配置
                if any(k.startswith('llm_') for k in config.keys()):
                    llm_config = {
                        k: v for k, v in config.items() 
                        if k.startswith('llm_') or k == 'enable_ai'
                    }
        except Exception:
            pass
    
    # 创建分析器并分析
    analyzer = ExperimentAnalyzer(enable_ai=enable_ai, llm_config=llm_config)
    analysis = analyzer.analyze_run(run_record, history)
    
    return analysis

