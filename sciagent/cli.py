"""CLI entrypoint for SciAgent."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List

from .config_loader import load_config_sources
from .guardian import RunGuardian
from .models import RunSpec
from .setup import run_init_wizard
from .analyzer import analyze_run_from_file
from .exporter import export_summary, export_table
from .ui import (
    print_banner,
    print_success,
    print_error,
    print_info,
    print_table,
    print_markdown,
    console,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="🔬 SciAgent - 科学实验运行守护与配置管理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command")

    # init 命令 - 交互式配置向导
    init_parser = subparsers.add_parser(
        "init",
        help="运行交互式配置向导",
        description="通过交互式界面配置 SciAgent"
    )
    init_parser.set_defaults(func=_init_command)

    # setup 命令 - init 的别名
    setup_parser = subparsers.add_parser(
        "setup",
        help="运行配置向导 (同 init)",
        description="通过交互式界面配置 SciAgent"
    )
    setup_parser.set_defaults(func=_init_command)

    # history 命令 - 查看历史运行
    history_parser = subparsers.add_parser(
        "history",
        help="查看历史运行记录",
        description="显示之前的运行历史"
    )
    history_parser.add_argument(
        "--workdir",
        default=".",
        help="工作目录路径"
    )
    history_parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="显示的最大记录数"
    )
    history_parser.set_defaults(func=_history_command)

    # analyze 命令 - AI 分析实验结果
    analyze_parser = subparsers.add_parser(
        "analyze",
        help="AI 实验复盘和下一步调参建议",
        description="让 AI 帮你做一次实验复盘，诊断问题并提供具体的下一步调参建议"
    )
    analyze_parser.add_argument(
        "--run-id",
        help="要分析的运行 ID"
    )
    analyze_parser.add_argument(
        "--last",
        action="store_true",
        help="分析最近一次成功的实验（默认行为）"
    )
    analyze_parser.add_argument(
        "--workdir",
        default=".",
        help="工作目录路径"
    )
    analyze_parser.add_argument(
        "--no-ai",
        action="store_true",
        help="禁用 AI 分析，使用基础分析"
    )
    analyze_parser.add_argument(
        "--output",
        help="保存分析报告到文件"
    )
    analyze_parser.set_defaults(func=_analyze_command)

    # summary 命令 - 生成实验摘要（周报）
    summary_parser = subparsers.add_parser(
        "summary",
        help="生成实验与代码摘要（用于周报、导师汇报、项目总结）",
        description="生成指定时间范围内的实验摘要，包含代码变更，可直接用于周报和论文准备"
    )
    summary_parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="统计最近几天的实验（默认7天）"
    )
    summary_parser.add_argument(
        "--name",
        help="筛选名称包含指定文本的实验"
    )
    summary_parser.add_argument(
        "--workdir",
        default=".",
        help="工作目录路径"
    )
    summary_parser.add_argument(
        "--output",
        help="保存摘要到文件"
    )
    summary_parser.add_argument(
        "--no-code",
        action="store_true",
        help="不包含代码变更摘要"
    )
    summary_parser.add_argument(
        "--ai-code",
        action="store_true",
        help="使用 AI 总结代码变更"
    )
    summary_parser.set_defaults(func=_summary_command)

    # table 命令 - 生成消融表格
    table_parser = subparsers.add_parser(
        "table",
        help="生成消融对比表（用于论文、实验对比分析）",
        description="从多次实验中生成消融对比表，支持 Markdown 和 LaTeX 格式，可直接用于论文写作"
    )
    table_parser.add_argument(
        "--name",
        help="筛选名称包含指定文本的实验（如 'ablation_'）"
    )
    table_parser.add_argument(
        "--columns",
        help="指定表格列（逗号分隔，如 'lr,batch_size,val_acc'）"
    )
    table_parser.add_argument(
        "--format",
        choices=["markdown", "latex"],
        default="markdown",
        help="输出格式（默认 markdown）"
    )
    table_parser.add_argument(
        "--workdir",
        default=".",
        help="工作目录路径"
    )
    table_parser.add_argument(
        "--output",
        help="保存表格到文件"
    )
    table_parser.set_defaults(func=_table_command)

    # daily 命令 - 快捷生成日报（summary 的别名）
    daily_parser = subparsers.add_parser(
        "daily",
        help="快捷生成今日工作日志（含代码变更和实验结果）",
        description="一键生成今天的工作日志，等同于 'sciagent summary --days 1 --ai-code'"
    )
    daily_parser.add_argument(
        "--output",
        help="保存日志到文件"
    )
    daily_parser.add_argument(
        "--workdir",
        default=".",
        help="工作目录路径"
    )
    daily_parser.set_defaults(func=_daily_command)

    # weekly 命令 - 快捷生成周报（summary 的别名）
    weekly_parser = subparsers.add_parser(
        "weekly",
        help="快捷生成本周工作周报（含代码变更和实验结果）",
        description="一键生成最近7天的完整周报，等同于 'sciagent summary --days 7 --ai-code'"
    )
    weekly_parser.add_argument(
        "--output",
        help="保存周报到文件"
    )
    weekly_parser.add_argument(
        "--workdir",
        default=".",
        help="工作目录路径"
    )
    weekly_parser.set_defaults(func=_weekly_command)

    # monthly 命令 - 快捷生成月报（summary 的别名）
    monthly_parser = subparsers.add_parser(
        "monthly",
        help="快捷生成本月工作月报（含代码变更和实验结果）",
        description="一键生成最近30天的完整月报，等同于 'sciagent summary --days 30 --ai-code'"
    )
    monthly_parser.add_argument(
        "--output",
        help="保存月报到文件"
    )
    monthly_parser.add_argument(
        "--workdir",
        default=".",
        help="工作目录路径"
    )
    monthly_parser.set_defaults(func=_monthly_command)

    # ablation 命令 - 快捷生成消融表（table 的别名）
    ablation_parser = subparsers.add_parser(
        "ablation",
        help="快捷生成消融对比表（自动筛选 ablation 实验）",
        description="一键生成消融实验对比表，等同于 'sciagent table --name ablation'"
    )
    ablation_parser.add_argument(
        "--format",
        choices=["markdown", "latex"],
        default="markdown",
        help="输出格式（默认 markdown）"
    )
    ablation_parser.add_argument(
        "--output",
        help="保存表格到文件"
    )
    ablation_parser.add_argument(
        "--workdir",
        default=".",
        help="工作目录路径"
    )
    ablation_parser.set_defaults(func=_ablation_command)

    # run 命令 - 执行训练运行
    run_parser = subparsers.add_parser("run", help="启动守护运行")
    run_parser.add_argument("command", nargs=argparse.REMAINDER, help="要执行的命令（如：python train.py --lr 0.001）")
    run_parser.add_argument("--workdir", default=".", help="Working directory for the command")
    run_parser.add_argument("--name", default=None, help="Human friendly run name")
    run_parser.add_argument(
        "--config-file",
        action="append",
        dest="config_files",
        help="Config file(s) that should be fingerprinted",
    )
    run_parser.add_argument(
        "--metadata",
        action="append",
        help="Free-form key=value pairs that describe the run",
    )
    run_parser.add_argument(
        "--metric",
        action="append",
        help="Metric key=value pairs to log when the command finishes",
    )
    run_parser.add_argument(
        "--metrics-file",
        default=None,
        help="Optional JSON file containing metrics to ingest",
    )
    run_parser.add_argument(
        "--primary-metric",
        default=None,
        help="Metric name used when diffing against history",
    )
    run_parser.add_argument(
        "--state-dir",
        default=None,
        help="Override location for SciAgent state (defaults to <workdir>/.sciagent)",
    )
    run_parser.add_argument(
        "--suggestions",
        type=int,
        default=3,
        help="How many suggestion bullets to include in the report",
    )
    run_parser.set_defaults(func=_run_command)

    return parser


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    
    # 如果没有提供命令，显示横幅和帮助
    if not hasattr(args, "func"):
        print_banner()
        console.print("[dim]使用 'sciagent init' 开始交互式配置[/dim]\n")
        parser.print_help()
        return 1
    
    return args.func(args)


def _init_command(args: argparse.Namespace) -> int:
    """运行初始化向导"""
    return run_init_wizard()


def _analyze_command(args: argparse.Namespace) -> int:
    """AI 分析实验结果"""
    workdir = Path(args.workdir).expanduser().resolve()
    state_dir = workdir / ".sciagent"
    
    if not state_dir.exists():
        print_error(f"未找到 SciAgent 状态目录: {state_dir}")
        print_info("使用 'sciagent run' 开始第一次运行。")
        return 1
    
    # 确定要分析的运行 ID
    runs_dir = state_dir / "runs"
    if not runs_dir.exists() or not list(runs_dir.iterdir()):
        print_error("未找到任何运行记录。")
        return 1
    
    if args.run_id:
        run_id = args.run_id
        run_dir = runs_dir / run_id
        if not run_dir.exists():
            print_error(f"未找到运行 ID: {run_id}")
            return 1
    else:
        # 使用最新的运行
        run_dirs = sorted(runs_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
        run_dir = run_dirs[0]
        run_id = run_dir.name
    
    run_record_file = run_dir / "run_record.json"
    if not run_record_file.exists():
        print_error(f"未找到运行记录文件: {run_record_file}")
        return 1
    
    history_file = state_dir / "history.json"
    config_file = workdir / ".sciagent.json"
    
    console.print()
    print_info(f"分析运行: {run_id[:12]}...")
    
    # 检查 AI 配置
    if not args.no_ai:
        has_ai_config = False
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    if config.get('enable_ai') and config.get('llm_api_key'):
                        has_ai_config = True
                        print_info(f"✓ 使用 AI 分析 (提供商: {config.get('llm_provider', 'auto')})")
            except Exception:
                pass
        
        if not has_ai_config:
            print_info("⚠️  未检测到 AI 配置，将使用基础分析")
            console.print()
            
            # 引导用户配置 AI
            try:
                import questionary
                if questionary.confirm(
                    "是否现在配置 AI 功能以获得更智能的分析？",
                    default=False
                ).ask():
                    console.print()
                    print_info("正在启动 AI 配置向导...")
                    console.print()
                    # 调用配置向导
                    from .setup import InteractiveSetup
                    setup = InteractiveSetup(workdir)
                    llm_config = setup._configure_llm_api()
                    
                    # 保存配置
                    if llm_config.get('enabled'):
                        existing_config = {}
                        if config_file.exists():
                            with open(config_file, 'r', encoding='utf-8') as f:
                                existing_config = json.load(f)
                        
                        existing_config.update(llm_config)
                        with open(config_file, 'w', encoding='utf-8') as f:
                            json.dump(existing_config, f, indent=2, ensure_ascii=False)
                        
                        console.print()
                        print_success("✓ AI 配置已保存，继续分析...")
                        has_ai_config = True
                    else:
                        console.print()
                        print_info("继续使用基础分析...")
            except ImportError:
                print_info("💡 运行 'sciagent init' 配置 AI 功能获得更智能的分析")
            except KeyboardInterrupt:
                console.print()
                print_info("已取消，继续使用基础分析...")
            except Exception:
                console.print()
                print_info("配置过程中断，继续使用基础分析...")
    
    console.print()
    
    try:
        # 分析运行
        analysis = analyze_run_from_file(
            run_record_file,
            history_file if history_file.exists() else None,
            enable_ai=not args.no_ai,
            config_path=config_file if config_file.exists() else None
        )
        
        console.print()
        print_success("✓ 分析完成！")
        console.print()
        
        # 显示分析结果
        print_markdown(analysis)
        
        # 自动保存到文件
        if args.output:
            output_path = Path(args.output).expanduser().resolve()
        else:
            # 默认保存到 reports 目录
            reports_dir = state_dir / "reports"
            reports_dir.mkdir(parents=True, exist_ok=True)
            date_str = datetime.now().strftime("%Y%m%d")
            run_id_short = run_id[:12] if len(run_id) >= 12 else run_id
            output_path = reports_dir / f"analysis_{run_id_short}_{date_str}.md"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(analysis)
        console.print()
        print_success(f"✓ 分析报告已保存到: {output_path}")
        
        console.print()
        
    except Exception as e:
        print_error(f"✗ 分析失败: {e}")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        return 1
    
    return 0


def _daily_command(args: argparse.Namespace) -> int:
    """快捷生成日报（daily 命令）"""
    # 构造 summary 命令的参数
    class DailyArgs:
        def __init__(self):
            self.workdir = args.workdir
            self.days = 1
            self.name = None
            # 如果没有指定输出文件，自动生成到 reports 目录
            if args.output:
                self.output = args.output
            else:
                workdir = Path(args.workdir).expanduser().resolve()
                reports_dir = workdir / ".sciagent" / "reports"
                reports_dir.mkdir(parents=True, exist_ok=True)
                date_str = datetime.now().strftime("%Y%m%d")
                self.output = str(reports_dir / f"daily_{date_str}.md")
            self.no_code = False
            self.ai_code = True  # 默认启用 AI 总结
    
    return _summary_command(DailyArgs())


def _weekly_command(args: argparse.Namespace) -> int:
    """快捷生成周报（weekly 命令）"""
    # 构造 summary 命令的参数
    class WeeklyArgs:
        def __init__(self):
            self.workdir = args.workdir
            self.days = 7
            self.name = None
            # 如果没有指定输出文件，自动生成到 reports 目录
            if args.output:
                self.output = args.output
            else:
                workdir = Path(args.workdir).expanduser().resolve()
                reports_dir = workdir / ".sciagent" / "reports"
                reports_dir.mkdir(parents=True, exist_ok=True)
                date_str = datetime.now().strftime("%Y%m%d")
                self.output = str(reports_dir / f"weekly_{date_str}.md")
            self.no_code = False
            self.ai_code = True  # 默认启用 AI 总结
    
    return _summary_command(WeeklyArgs())


def _monthly_command(args: argparse.Namespace) -> int:
    """快捷生成月报（monthly 命令）"""
    # 构造 summary 命令的参数
    class MonthlyArgs:
        def __init__(self):
            self.workdir = args.workdir
            self.days = 30
            self.name = None
            # 如果没有指定输出文件，自动生成到 reports 目录
            if args.output:
                self.output = args.output
            else:
                workdir = Path(args.workdir).expanduser().resolve()
                reports_dir = workdir / ".sciagent" / "reports"
                reports_dir.mkdir(parents=True, exist_ok=True)
                date_str = datetime.now().strftime("%Y%m%d")
                self.output = str(reports_dir / f"monthly_{date_str}.md")
            self.no_code = False
            self.ai_code = True  # 默认启用 AI 总结
    
    return _summary_command(MonthlyArgs())


def _ablation_command(args: argparse.Namespace) -> int:
    """快捷生成消融表（ablation 命令）"""
    # 构造 table 命令的参数
    class AblationArgs:
        def __init__(self):
            self.workdir = args.workdir
            self.name = "ablation"  # 默认筛选 ablation
            self.columns = None
            self.format = args.format
            self.output = args.output
    
    return _table_command(AblationArgs())


def _summary_command(args: argparse.Namespace) -> int:
    """生成实验摘要（周报）"""
    workdir = Path(args.workdir).expanduser().resolve()
    state_dir = workdir / ".sciagent"
    
    if not state_dir.exists():
        print_error(f"未找到 SciAgent 状态目录: {state_dir}")
        print_info("💡 提示：先用 'sciagent run' 跑一次实验，或用 'sciagent init' 初始化项目")
        return 1
    
    console.print()
    if args.no_code:
        print_info(f"生成最近 {args.days} 天的实验摘要...")
    else:
        print_info(f"生成最近 {args.days} 天的实验摘要（含代码变更）...")
    console.print()
    
    try:
        # 读取 LLM 配置（如果使用 AI）
        llm_config = None
        if args.ai_code:
            config_file = workdir / ".sciagent.json"
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    if config.get('enable_ai'):
                        llm_config = {
                            k: v for k, v in config.items() 
                            if k.startswith('llm_')
                        }
        
        output_file = Path(args.output).expanduser().resolve() if args.output else None
        
        summary = export_summary(
            state_dir,
            since_days=args.days,
            name_pattern=args.name,
            output_file=output_file,
            include_code_changes=not args.no_code,
            use_ai_for_code=args.ai_code,
            llm_config=llm_config
        )
        
        # 显示摘要
        console.print()
        print_markdown(summary)
        console.print()
        
    except Exception as e:
        print_error(f"生成摘要失败: {e}")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        return 1
    
    return 0


def _table_command(args: argparse.Namespace) -> int:
    """生成消融表格"""
    workdir = Path(args.workdir).expanduser().resolve()
    state_dir = workdir / ".sciagent"
    
    if not state_dir.exists():
        print_error(f"未找到 SciAgent 状态目录: {state_dir}")
        return 1
    
    console.print()
    print_info("生成实验对比表格...")
    console.print()
    
    try:
        columns = args.columns.split(',') if args.columns else None
        
        # 自动生成输出文件路径
        if args.output:
            output_file = Path(args.output).expanduser().resolve()
        else:
            # 默认保存到 reports 目录
            reports_dir = state_dir / "reports"
            reports_dir.mkdir(parents=True, exist_ok=True)
            date_str = datetime.now().strftime("%Y%m%d")
            name_part = args.name if args.name else "all"
            output_file = reports_dir / f"table_{name_part}_{date_str}.md"
        
        table = export_table(
            state_dir,
            name_pattern=args.name,
            columns=columns,
            format=args.format,
            output_file=output_file
        )
        
        # 显示表格
        console.print()
        console.print(table)
        console.print()
        
    except Exception as e:
        print_error(f"生成表格失败: {e}")
        return 1
    
    return 0


def _history_command(args: argparse.Namespace) -> int:
    """显示历史运行记录"""
    workdir = Path(args.workdir).expanduser().resolve()
    state_dir = workdir / ".sciagent"
    history_file = state_dir / "history.json"
    
    if not history_file.exists():
        print_error(f"未找到历史记录文件: {history_file}")
        print_info("使用 'sciagent run' 开始第一次运行。")
        return 1
    
    try:
        with open(history_file, "r", encoding="utf-8") as f:
            history_data = json.load(f)
        
        runs = history_data.get("runs", [])
        
        if not runs:
            print_info("还没有运行记录。")
            return 0
        
        # 限制显示数量
        runs = runs[-args.limit:]
        
        console.print()
        print_success(f"找到 {len(runs)} 条运行记录:")
        console.print()
        
        # 准备表格数据
        rows = []
        for run in runs:
            run_id = run.get("run_id", "N/A")[:8]
            name = run.get("name", "unnamed")
            status = run.get("status", "unknown")
            # 优先使用 start_time，fallback 到 ended_at
            timestamp = run.get("start_time") or run.get("ended_at", "N/A")
            # 如果有时间戳，格式化一下（去掉 Z 和微秒）
            if timestamp != "N/A":
                try:
                    # 简化时间显示：只保留到秒
                    timestamp = timestamp.replace('Z', '').split('.')[0]
                except:
                    pass
            primary_metric = run.get("primary_metric_value", "N/A")
            
            # 格式化状态（兼容多种状态值）
            if status in ["completed", "succeeded"]:
                status_display = "[green]✓ 完成[/green]"
            elif status == "failed":
                status_display = "[red]✗ 失败[/red]"
            else:
                status_display = "[yellow]○ 运行中[/yellow]"
            
            rows.append([run_id, name, status_display, str(primary_metric), timestamp])
        
        print_table(
            "历史运行记录",
            ["Run ID", "名称", "状态", "主要指标", "开始时间"],
            rows
        )
        
        console.print()
        
    except json.JSONDecodeError:
        print_error("历史记录文件格式错误。")
        return 1
    except Exception as e:
        print_error(f"读取历史记录失败: {e}")
        return 1
    
    return 0


def _run_command(args: argparse.Namespace) -> int:
    """执行训练运行"""
    # 将命令列表转换为字符串
    if isinstance(args.command, list):
        command_str = " ".join(args.command)
    else:
        command_str = args.command
    
    if not command_str or not command_str.strip():
        print_error("错误：未指定要执行的命令")
        print_info("用法：sciagent run python train.py --lr 0.001")
        return 1
    
    workdir = Path(args.workdir).expanduser().resolve()
    state_dir = Path(args.state_dir).expanduser().resolve() if args.state_dir else workdir / ".sciagent"
    
    # 检查是否存在配置文件
    config_json = workdir / ".sciagent.json"
    if config_json.exists():
        try:
            with open(config_json, "r", encoding="utf-8") as f:
                saved_config = json.load(f)
            
            print_info(f"使用保存的配置: {config_json}")
            
            # 如果没有提供项目名称，从配置文件中读取
            if not args.name and "project_name" in saved_config:
                args.name = saved_config["project_name"]
            
            # 注意：primary_metric 现在会自动从 metrics.json 中检测，无需手动配置
        
        except Exception as e:
            print_error(f"读取配置文件失败: {e}")
    
    config_sources = load_config_sources(args.config_files)
    
    try:
        metadata = _parse_key_value_pairs(args.metadata)
        metrics = _parse_numeric_pairs(args.metric)
    except ValueError as exc:
        print_error(f"{exc}")
        return 2
    
    metrics_file = Path(args.metrics_file).expanduser().resolve() if args.metrics_file else None
    
    spec = RunSpec(
        command=command_str,
        workdir=workdir,
        name=args.name,
        state_dir=state_dir,
        config_sources=config_sources,
        metadata=metadata,
        metrics=metrics,
        metrics_file=metrics_file,
        primary_metric=args.primary_metric,
        suggestion_count=max(0, args.suggestions),
    )
    
    console.print()
    print_info(f"启动运行: {command_str}")
    print_info(f"工作目录: {workdir}")
    console.print()
    
    guardian = RunGuardian(spec)
    result = guardian.execute()
    
    console.print()
    
    if result == 0:
        print_success("✓ 运行完成！")
        console.print()
        
        # 给出下一步提示
        print_info("💡 下一步操作：")
        console.print("  • 查看历史记录: [cyan]sciagent history[/cyan]")
        console.print("  • AI 分析本次实验: [cyan]sciagent analyze --last[/cyan]")
        console.print("  • 生成今日日志: [cyan]sciagent daily[/cyan]")
        console.print("  • 生成本周周报: [cyan]sciagent weekly[/cyan]")
        console.print()
    else:
        print_error("✗ 运行失败")
        console.print()
        print_info("💡 可以查看详细日志来排查问题")
        console.print()
    
    return result


def _parse_key_value_pairs(pairs: Iterable[str] | None) -> Dict[str, str]:
    result: Dict[str, str] = {}
    if not pairs:
        return result
    for item in pairs:
        key, value = _split_pair(item)
        result[key] = value
    return result


def _parse_numeric_pairs(pairs: Iterable[str] | None) -> Dict[str, float]:
    result: Dict[str, float] = {}
    if not pairs:
        return result
    for item in pairs:
        key, value = _split_pair(item)
        try:
            result[key] = float(value)
        except ValueError:
            continue
    return result


def _split_pair(payload: str) -> tuple[str, str]:
    if "=" not in payload:
        raise ValueError(f"Expected key=value format, got: {payload}")
    key, value = payload.split("=", 1)
    if not key:
        raise ValueError(f"Invalid key for pair: {payload}")
    return key, value


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
