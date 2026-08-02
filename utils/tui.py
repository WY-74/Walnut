from typing import Callable
from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.prompt import Prompt
from pyfiglet import Figlet
from rich.align import Align

console = Console()


def _build_logo(logo_width: int) -> Text:
    figlet = Figlet(font="ansi_shadow", width=logo_width)
    art = figlet.renderText("WALNUT").rstrip("\n")

    colors = ["#D7B899", "#B98D65", "#956843", "#6F4A2D", "#4B2F1C"]
    text = Text()
    for i, line in enumerate(art.splitlines()):
        text.append(line + "\n", style=f"bold {colors[i % len(colors)]}")

    return text


def _build_meta_table(version: str, model: str) -> Table:
    table = Table.grid(padding=(0, 1))
    table.add_column(style="bold #A67C52", width=10)
    table.add_column(style="bold #A1A1AA")

    table.add_row("version:", version, "")
    table.add_row("model:", model, "")

    return table


def run_cli(server: Callable[[str | None, str, bool], None]) -> None:
    def _cli() -> None:
        server()

    _cli()


def show_boot_screen(version: str, model: str) -> Table:
    logo_width = max(90, console.size.width - 10)
    panel_width = min(console.size.width - 2, logo_width + 8)

    body = Group(Align.center(_build_logo(logo_width)), Text(""), _build_meta_table(version, model))
    panel = Panel(body, border_style="#6F4A2D", padding=(1, 4), width=panel_width, expand=False)
    console.print(panel)


def ask_query() -> str:
    return Prompt.ask("[bold white]>[/bold white] Type message or command").strip()


def show_bye() -> None:
    console.print("[bold #8A5A34]WALNUT[/bold #8A5A34]: Bye!")


def show_result(text: str) -> None:
    console.print(f"[bold #8A5A34]WALNUT[/bold #8A5A34]: {text}")


def show_error(err: Exception) -> None:
    console.print(f"[bold red]Error[/bold red]: {err}")
