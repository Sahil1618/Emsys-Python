# import json

# from rich.console import Console
# from rich.panel import Panel
# from rich.table import Table

# from wbes.schedule_parser import iter_schedule_rows

# console = Console()


# def display_schedule_results(qca_name: str, date_str: str, data: dict) -> None:
#     """Render schedule rows in a Rich CLI table."""
#     rows = list(iter_schedule_rows(data, qca_name))
#     if not rows:
#         console.print(
#             "[yellow][!] Warning: The request was successful, but no power "
#             "schedule groups were returned by the grid.[/yellow]"
#         )
#         return

#     revision = rows[0].get("revision", "NA")
#     table = Table(
#         title=f"WBES Energy Schedules | {qca_name} ({date_str}) | Rev {revision}",
#         title_style="bold cyan",
#         border_style="blue",
#         show_header=True,
#     )
#     table.add_column("Plant Acronym", style="bold green")
#     table.add_column("Schedule Type", style="magenta")
#     table.add_column("Seller", style="blue")
#     table.add_column("Buyer", style="blue")
#     table.add_column("Approval No", style="dim white")
#     table.add_column("Daily Total (MW)", justify="right", style="bold yellow")

#     for row in rows:
#         table.add_row(
#             row["plant"],
#             row["type"],
#             row["seller"],
#             row["buyer"],
#             row["approval"],
#             f"{row['daily_total_mw']:,.2f}",
#         )

#     console.print("\n")
#     console.print(table)
#     console.print("\n")


# def log_and_display_error(qca_name: str, result: dict) -> None:
#     """Show a Rich error panel and append to wbes_fetcher.log."""
#     status = result.get("status")
#     message = result.get("message", "An unexpected error occurred.")

#     panel_title = f"[bold red][ERROR] FETCH ERROR ({status}) | QCA: {qca_name}[/bold red]"
#     diagnostic_content = f"[bold white]{message}[/bold white]\n\n"

#     if status == "IP_WHITELIST_BLOCKED":
#         diagnostic_content += f"[bold cyan][!] GATEWAY DIAGNOSTICS:[/bold cyan]\n{result.get('diagnostics')}\n\n"
#         if result.get("raw_response"):
#             diagnostic_content += f"[dim]Raw Gateway Output: {result.get('raw_response')}[/dim]"

#     elif status == "API_LEVEL_ERROR":
#         diagnostic_content += (
#             f"[bold yellow]GRID-INDIA Error Code:[/bold yellow] {result.get('code')}\n"
#             f"[bold yellow]Details:[/bold yellow] {json.dumps(result.get('details'))}"
#         )

#     elif "raw_response" in result:
#         diagnostic_content += f"[dim]Raw Response: {result.get('raw_response')[:250]}[/dim]"

#     console.print(Panel(diagnostic_content, title=panel_title, border_style="red"))

#     from wbes.logging_util import append_fetch_log

#     append_fetch_log(qca_name, result)


import json

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from wbes.schedule_parser import iter_schedule_rows

console = Console()

# 96 block time labels  B1 00:00-00:15 ... B96 23:45-24:00
_BLOCK_LABELS = []
for _b in range(96):
    _hh, _mm = divmod(_b * 15, 60)
    _ehh, _emm = divmod((_b + 1) * 15, 60)
    _BLOCK_LABELS.append(
        f"B{_b + 1}\n{_hh:02d}:{_mm:02d}-{_ehh:02d}:{_emm:02d}"
    )


def display_schedule_results(
    qca_name: str,
    date_str: str,
    data: dict,
    show_blocks: bool = True,
) -> None:
    """
    Render schedule rows in a Rich CLI table.

    Parameters
    ----------
    show_blocks : bool
        True  → block-wise table (B1–B96 columns) like the Excel output.
        False → summary table (Daily Total only), original behaviour.
    """
    rows = list(iter_schedule_rows(data, qca_name))
    if not rows:
        console.print(
            "[yellow][!] Warning: The request was successful, but no power "
            "schedule groups were returned by the grid.[/yellow]"
        )
        return

    revision = rows[0].get("revision", "NA")

    if show_blocks:
        _display_blockwise(qca_name, date_str, revision, rows)
    else:
        _display_summary(qca_name, date_str, revision, rows)


# ---------------------------------------------------------------------------
# Block-wise table  (matches the Excel layout)
# ---------------------------------------------------------------------------

def _display_blockwise(
    qca_name: str,
    date_str: str,
    revision: str,
    rows: list[dict],
) -> None:
    """Print one wide table with a column per 15-min block (B1–B96)."""

    table = Table(
        title=f"WBES Block-Wise Schedule  |  {qca_name}  |  {date_str}  |  Rev {revision}",
        title_style="bold cyan",
        border_style="blue",
        show_header=True,
        header_style="bold white",
    )

    # Fixed meta columns
    table.add_column("Plant Acronym",  style="bold green",  no_wrap=True)
    table.add_column("Schedule Type",  style="magenta",     no_wrap=True)
    table.add_column("Seller",         style="blue",        no_wrap=True)
    table.add_column("Buyer",          style="blue",        no_wrap=True)
    table.add_column("Approval No",    style="dim white")
    table.add_column(
        "Daily Total\n(MW)",
        justify="right",
        style="bold yellow",
        no_wrap=True,
    )

    # One column per block
    for label in _BLOCK_LABELS:
        table.add_column(label, justify="right", style="cyan", no_wrap=True)

    for row in rows:
        stype = row["type"]
        # Colour-code schedule type like the Excel (green = AS, orange = OA_REMC)
        if stype == "AS":
            type_style = "[bold green]AS[/bold green]"
        elif stype.startswith("OA"):
            type_style = f"[bold orange1]{stype}[/bold orange1]"
        else:
            type_style = stype

        block_cells = [
            f"{v:,.2f}" if v != 0.0 else "[dim]0.00[/dim]"
            for v in row["blocks"]
        ]

        table.add_row(
            row["plant"],
            type_style,
            row["seller"],
            row["buyer"],
            row["approval"],
            f"{row['daily_total_mw']:,.2f}",
            *block_cells,
        )

    console.print("\n")
    console.print(table)
    console.print("\n")
    console.print(
        f"[dim]  {len(rows)} schedule rows  |  96 blocks (15-min intervals)  "
        f"|  Daily Total = sum of B1–B96[/dim]\n"
    )


# ---------------------------------------------------------------------------
# Summary table  (original behaviour — daily total only)
# ---------------------------------------------------------------------------

def _display_summary(
    qca_name: str,
    date_str: str,
    revision: str,
    rows: list[dict],
) -> None:
    table = Table(
        title=f"WBES Energy Schedules | {qca_name} ({date_str}) | Rev {revision}",
        title_style="bold cyan",
        border_style="blue",
        show_header=True,
    )
    table.add_column("Plant Acronym",   style="bold green")
    table.add_column("Schedule Type",  style="magenta")
    table.add_column("Seller",         style="blue")
    table.add_column("Buyer",          style="blue")
    table.add_column("Approval No",    style="dim white")
    table.add_column("Daily Total (MW)", justify="right", style="bold yellow")

    for row in rows:
        table.add_row(
            row["plant"],
            row["type"],
            row["seller"],
            row["buyer"],
            row["approval"],
            f"{row['daily_total_mw']:,.2f}",
        )

    console.print("\n")
    console.print(table)
    console.print("\n")


# ---------------------------------------------------------------------------
# Error display  (unchanged)
# ---------------------------------------------------------------------------

def log_and_display_error(qca_name: str, result: dict) -> None:
    """Show a Rich error panel and append to wbes_fetcher.log."""
    status = result.get("status")
    message = result.get("message", "An unexpected error occurred.")

    panel_title = (
        f"[bold red][ERROR] FETCH ERROR ({status}) | QCA: {qca_name}[/bold red]"
    )
    diagnostic_content = f"[bold white]{message}[/bold white]\n\n"

    if status == "IP_WHITELIST_BLOCKED":
        diagnostic_content += (
            f"[bold cyan][!] GATEWAY DIAGNOSTICS:[/bold cyan]\n"
            f"{result.get('diagnostics')}\n\n"
        )
        if result.get("raw_response"):
            diagnostic_content += (
                f"[dim]Raw Gateway Output: {result.get('raw_response')}[/dim]"
            )

    elif status == "API_LEVEL_ERROR":
        diagnostic_content += (
            f"[bold yellow]GRID-INDIA Error Code:[/bold yellow] {result.get('code')}\n"
            f"[bold yellow]Details:[/bold yellow] {json.dumps(result.get('details'))}"
        )

    elif "raw_response" in result:
        diagnostic_content += (
            f"[dim]Raw Response: {result.get('raw_response')[:250]}[/dim]"
        )

    console.print(Panel(diagnostic_content, title=panel_title, border_style="red"))

    from wbes.logging_util import append_fetch_log

    append_fetch_log(qca_name, result)