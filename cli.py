"""Rich 终端交互界面"""

import random
import sys

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.rule import Rule
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text
from rich.live import Live

from core import (
    CATEGORY_TEMPLATES,
    EXAMPLE_PROMPTS,
    STYLE_PRESETS,
    chat,
    create_executor,
)

console = Console()

BANNER = r"""
 ╔══════════════════════════════════════════════════════╗
 ║   🎮  2D 游戏素材 AI 生成器  ·  Game Asset Studio   ║
 ║        Powered by Qwen + Wanx · LangChain Agent      ║
 ╚══════════════════════════════════════════════════════╝
"""


def show_welcome():
    console.print(BANNER, style="bold cyan")
    console.print(Rule("[dim]快速开始[/dim]"))

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="bold yellow", width=12)
    table.add_column(style="white")
    table.add_row("风格", "、".join(STYLE_PRESETS.keys()))
    table.add_row("分类", "、".join(CATEGORY_TEMPLATES.keys()))
    table.add_row("命令", "[dim]help[/] 帮助  ·  [dim]style[/] 切换风格  ·  [dim]clear[/] 清空记忆  ·  [dim]exit[/] 退出")
    console.print(table)
    console.print()


def show_help():
    console.print(Panel(
        "\n".join([
            "[bold]使用方式[/]",
            "  直接输入描述即可生成，例如：「生成一个持盾的骑士角色」",
            "",
            "[bold]内置命令[/]",
            "  [cyan]help[/]    显示帮助",
            "  [cyan]style[/]   切换画风（像素风/卡通/等距视角…）",
            "  [cyan]cat[/]     切换素材分类（角色/道具/场景…）",
            "  [cyan]random[/]  随机示例提示词",
            "  [cyan]clear[/]   清空对话记忆",
            "  [cyan]exit[/]    退出程序",
        ]),
        title="📖 帮助",
        border_style="blue",
    ))


def pick_style(current: str) -> str:
    styles = list(STYLE_PRESETS.keys())
    console.print("\n[bold]选择画风：[/]")
    for i, s in enumerate(styles, 1):
        mark = " ◀ 当前" if s == current else ""
        console.print(f"  [cyan]{i}[/]. {s}{mark}")
    choice = Prompt.ask("输入编号", default=str(styles.index(current) + 1) if current in styles else "1")
    try:
        return styles[int(choice) - 1]
    except (ValueError, IndexError):
        return current


def pick_category(current: str) -> str:
    cats = ["（无）"] + list(CATEGORY_TEMPLATES.keys())
    console.print("\n[bold]选择素材分类：[/]")
    for i, c in enumerate(cats, 1):
        mark = " ◀ 当前" if c == (current or "（无）") else ""
        console.print(f"  [cyan]{i}[/]. {c}{mark}")
    default = "1"
    if current in cats:
        default = str(cats.index(current) + 1)
    choice = Prompt.ask("输入编号", default=default)
    try:
        selected = cats[int(choice) - 1]
        return "" if selected == "（无）" else selected
    except (ValueError, IndexError):
        return current


def run_cli():
    show_welcome()

    try:
        style = "像素风"
        category = ""
        executor = create_executor(style, category)
    except EnvironmentError as e:
        console.print(Panel(str(e), title="⚠️ 配置错误", border_style="red"))
        sys.exit(1)

    status = Text()
    status.append("画风: ", style="dim")
    status.append(style, style="bold cyan")
    status.append("  │  分类: ", style="dim")
    status.append(category or "通用", style="bold green")
    console.print(Panel(status, title="当前设置", border_style="dim"))

    while True:
        try:
            question = Prompt.ask("\n[bold green]🎨 描述你的素材[/]", console=console)
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]再见！[/]")
            break

        q = question.strip()
        if not q:
            continue

        cmd = q.lower()
        if cmd in ("exit", "退出", "quit", "q"):
            console.print("[dim]再见，祝创作愉快！ 🎮[/]")
            break
        if cmd == "help":
            show_help()
            continue
        if cmd == "style":
            style = pick_style(style)
            executor = create_executor(style, category)
            console.print(f"[green]✓ 已切换画风 → {style}[/]")
            continue
        if cmd == "cat":
            category = pick_category(category)
            executor = create_executor(style, category)
            console.print(f"[green]✓ 已切换分类 → {category or '通用'}[/]")
            continue
        if cmd == "random":
            q = random.choice(EXAMPLE_PROMPTS)
            console.print(f"[dim]随机示例：{q}[/]")
        if cmd == "clear":
            executor = create_executor(style, category)
            console.print("[yellow]✓ 对话记忆已清空[/]")
            continue

        with Live(Spinner("dots", text="[cyan]AI 正在生成素材…[/]"), console=console, refresh_per_second=10):
            try:
                reply, img_url = chat(executor, q)
            except Exception as e:
                reply, img_url = f"生成出错: {e}", None

        console.print()
        console.print(Panel(Markdown(reply), title="🤖 Agent", border_style="green"))

        if img_url:
            console.print(Panel(
                f"[link={img_url}]{img_url}[/link]\n\n[dim]在浏览器中打开链接即可预览/下载[/]",
                title="🖼️  生成结果",
                border_style="magenta",
            ))


if __name__ == "__main__":
    run_cli()
