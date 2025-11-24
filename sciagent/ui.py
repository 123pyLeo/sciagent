"""美化的终端界面工具模块"""

from __future__ import annotations

from typing import Any, Optional

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text
from rich import box
from rich.markdown import Markdown

console = Console()


def print_banner():
    """打印欢迎横幅"""
    banner_text = """
    ╔═══════════════════════════════════════════╗
    ║                                           ║
    ║            🔬 SciAgent CLI                ║
    ║                                           ║
    ║    科学实验运行守护与配置管理工具          ║
    ║                                           ║
    ╚═══════════════════════════════════════════╝
    """
    console.print(banner_text, style="bold cyan")


def print_section_header(title: str):
    """打印章节标题"""
    console.print()
    console.print(f"[bold blue]{'─' * 50}[/bold blue]")
    console.print(f"[bold white]  {title}[/bold white]")
    console.print(f"[bold blue]{'─' * 50}[/bold blue]")
    console.print()


def print_success(message: str):
    """打印成功消息"""
    console.print(f"[bold green]✓[/bold green] {message}")


def print_error(message: str):
    """打印错误消息"""
    console.print(f"[bold red]✗[/bold red] {message}")


def print_warning(message: str):
    """打印警告消息"""
    console.print(f"[bold yellow]⚠[/bold yellow] {message}")


def print_info(message: str):
    """打印信息消息"""
    console.print(f"[cyan]ℹ[/cyan] {message}")


def print_step(step: int, total: int, message: str):
    """打印步骤消息"""
    console.print(f"[bold magenta][{step}/{total}][/bold magenta] {message}")


def create_info_panel(title: str, content: str, style: str = "blue"):
    """创建信息面板"""
    panel = Panel(
        content,
        title=title,
        border_style=style,
        box=box.ROUNDED,
        padding=(1, 2)
    )
    console.print(panel)


def create_table(title: str, columns: list[str], rows: list[list[str]]) -> Table:
    """创建表格"""
    table = Table(title=title, box=box.ROUNDED, show_header=True, header_style="bold magenta")
    
    for col in columns:
        table.add_column(col)
    
    for row in rows:
        table.add_row(*row)
    
    return table


def print_table(title: str, columns: list[str], rows: list[list[str]]):
    """打印表格"""
    table = create_table(title, columns, rows)
    console.print(table)


def create_progress_spinner(message: str = "处理中..."):
    """创建进度旋转器"""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    )


def print_key_value(key: str, value: Any, key_style: str = "cyan", value_style: str = "white"):
    """打印键值对"""
    console.print(f"[{key_style}]{key}:[/{key_style}] [{value_style}]{value}[/{value_style}]")


def print_markdown(content: str):
    """打印 Markdown 内容"""
    md = Markdown(content)
    console.print(md)


def print_divider():
    """打印分隔线"""
    console.print("[dim]" + "─" * 50 + "[/dim]")


def clear_line():
    """清除当前行"""
    console.print("\r" + " " * 80 + "\r", end="")

