import datetime
import sys

import questionary
from rich.console import Console
from rich.panel import Panel

from wbes.config import QCA_LABELS, QCAS
from wbes.runner import print_run_summary, resolve_qca_list, run_fetch_workflow

console = Console()

custom_style = questionary.Style([
    ("qmark", "fg:#06b6d4 bold"),
    ("question", "fg:#f8fafc bold"),
    ("answer", "fg:#22d3ee bold"),
    ("pointer", "fg:#06b6d4 bold"),
    ("highlighted", "fg:#06b6d4 bold"),
    ("selected", "fg:#10b981 bold"),
    ("separator", "fg:#475569"),
    ("instruction", "fg:#94a3b8 italic"),
])


def run_interactive_terminal_menu(today_str: str, tomorrow_str: str, yesterday_str: str) -> None:
    """Arrow-key console menu (questionary + rich)."""
    console.print("\n")
    console.print(
        Panel.fit(
            "    [bold cyan]=== GRID-INDIA / POSOCO WBES ENERGY FETCH ENGINE ===[/bold cyan]    \n"
            "[dim]       Interactive Dynamic Power Scheduling Interface - v1.2       [/dim]",
            border_style="cyan",
            subtitle="[bold white]Qualified Coordinating Agency (QCA) System (Console Menu)[/bold white]",
        )
    )

    qca_choices = [
        questionary.Choice(QCA_LABELS[q], value=q) for q in QCAS
    ] + [questionary.Choice("[ FETCH ALL 4 QCAS SEQUENTIALLY ]", value="ALL")]

    qca_choice = questionary.select(
        "Step 1: Select the Target QCA to fetch schedules for:",
        choices=qca_choices,
        style=custom_style,
    ).ask()

    if not qca_choice:
        console.print("[yellow]Operation cancelled by user.[/yellow]")
        sys.exit(0)

    date_choice = questionary.select(
        "Step 2: Choose the Target Scheduling Date:",
        choices=[
            questionary.Choice(f"Today ({today_str})", value=today_str),
            questionary.Choice(f"Tomorrow ({tomorrow_str})", value=tomorrow_str),
            questionary.Choice(f"Yesterday ({yesterday_str})", value=yesterday_str),
            questionary.Choice("Custom Date (Manually enter DD-MM-YYYY)", value="custom"),
        ],
        style=custom_style,
    ).ask()

    if date_choice == "custom":
        date_str = questionary.text(
            "Enter target date (Format: DD-MM-YYYY):",
            default=today_str,
            validate=lambda val: (
                len(val) == 10
                and val[2] == "-"
                and val[5] == "-"
                and val.replace("-", "").isdigit()
            )
            or "Please enter a valid date in DD-MM-YYYY format.",
            style=custom_style,
        ).ask()
    else:
        date_str = date_choice

    if not date_str:
        console.print("[yellow]Operation cancelled by user.[/yellow]")
        sys.exit(0)

    rev_choice = questionary.select(
        "Step 3: Select Schedule Revision Mode:",
        choices=[
            questionary.Choice("Latest Revision Available (Default: -1)", value="-1"),
            questionary.Choice("Custom Revision Number (e.g. 0, 1, 2)", value="custom"),
        ],
        style=custom_style,
    ).ask()

    if rev_choice == "custom":
        rev_str = questionary.text(
            "Enter custom revision integer:",
            default="0",
            validate=lambda val: val.lstrip("-").isdigit() or "Please enter an integer number.",
            style=custom_style,
        ).ask()
    else:
        rev_str = "-1"

    if not rev_str:
        console.print("[yellow]Operation cancelled by user.[/yellow]")
        sys.exit(0)

    qcas_to_run = resolve_qca_list(qca_choice)
    console.print(
        f"\n[bold green]>> Initiating energy schedule fetch for {len(qcas_to_run)} "
        f"QCA(s) for Date: {date_str}...[/bold green]\n"
    )

    results = run_fetch_workflow(qcas_to_run, date_str, rev_str)
    print_run_summary(results)
