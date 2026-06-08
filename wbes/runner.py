import os
from typing import Callable

from rich.console import Console
from rich.status import Status

from wbes.api_client import fetch_wbes_schedule
from wbes.config import QCAS, SCHEDULES_ROOT
from wbes.display import display_schedule_results, log_and_display_error
from wbes.excel_resolver import resolve_plants_from_excel
from wbes.storage import save_schedule

console = Console()


def resolve_qca_list(qca_choice: str) -> list[str]:
    if qca_choice == "ALL":
        return list(QCAS)
    return [qca_choice]


def run_fetch_workflow(
    qcas: list[str],
    date_str: str,
    rev_str: str,
    *,
    on_status: Callable[[str], None] | None = None,
    on_log: Callable[[str], None] | None = None,
    on_row: Callable[[dict], None] | None = None,
    stop_on_ip_block: bool = False,
    show_tables: bool = True,
) -> list[dict]:
    """
    Shared fetch pipeline used by CLI, questionary menu, and TUI.

    Returns a list of per-QCA result summaries.
    """
    os.makedirs(SCHEDULES_ROOT, exist_ok=True)
    results = []

    def status(msg: str) -> None:
        if on_status:
            on_status(msg)

    def log(msg: str) -> None:
        if on_log:
            on_log(msg)

    for qca in qcas:
        status(f"Processing QCA: {qca}...")
        console.print(f"[bold cyan]>> [Processing {qca}][/bold cyan]")

        try:
            plants = resolve_plants_from_excel(qca)
            msg = f"[cyan]QCA {qca}[/cyan]: Resolved {len(plants)} plants from Excel."
            log(msg)
            console.print(f"  -> Dynamically matched [green]{len(plants)}[/green] power plants from Excel.")
        except Exception as exc:
            log(f"[red]Excel Error for {qca}[/red]: {exc}")
            console.print(f"  [red][ERROR] Excel Parsing Error:[/red] {exc}")
            results.append({"qca": qca, "status": "FAILED", "error": "EXCEL_ERROR"})
            continue

        with Status(
            f"[bold yellow]Connecting to GRID-INDIA Gateway for {qca}...[/bold yellow]",
            console=console,
        ):
            result = fetch_wbes_schedule(qca, date_str, rev_str, plants)

        if result["status"] == "SUCCESS":
            data = result["data"]
            file_path = save_schedule(qca, date_str, data)
            log(f"[green]SUCCESS[/green]: Downloaded {qca} Schedule.")
            log(f"  -> File: {file_path}")
            console.print("  [bold green] -> Schedule successfully downloaded![/bold green]")
            console.print(f"  [FILE] Organized file saved to: [cyan]{file_path}[/cyan]")

            if show_tables:
                display_schedule_results(qca, date_str, data)

            if on_row:
                from wbes.schedule_parser import iter_schedule_rows

                for row in iter_schedule_rows(data, qca):
                    on_row(row)

            results.append({"qca": qca, "status": "SUCCESS", "file_saved": file_path})
        else:
            log(f"[bold red]FAILED[/bold red]: QCA {qca} - {result['status']}")
            log(f"  Reason: {result.get('message', 'Unknown error')}")

            if result["status"] == "IP_WHITELIST_BLOCKED" and on_log:
                log("\n[bold red]" + "=" * 50)
                log("   IP WHITELIST BLOCK DETECTED")
                log("=" * 50 + "[/bold red]\n")
                log(f"[bold white]{result.get('message')}[/bold white]\n")
                log("[bold cyan]GATEWAY DIAGNOSTICS:[/bold cyan]")
                log(result.get("diagnostics", ""))
                if result.get("raw_response"):
                    log(f"\n[dim]Raw Gateway Output: {result.get('raw_response')}[/dim]")
                log("\n[bold red]" + "=" * 50 + "[/bold red]\n")

            if on_log is None:
                log_and_display_error(qca, result)
            else:
                from wbes.logging_util import append_fetch_log

                append_fetch_log(qca, result)

            results.append({"qca": qca, "status": "FAILED", "error": result.get("status")})

            if stop_on_ip_block and result["status"] == "IP_WHITELIST_BLOCKED":
                status(f"[bold red]IP Whitelist Blocked ({qca})[/bold red]")
                break

    return results


def print_run_summary(results: list[dict]) -> None:
    console.print("=" * 60)
    console.print("[bold cyan]>>> RUN COMPLETED -- SUMMARY OF RESULTS[/bold cyan]")
    console.print("=" * 60)
    for res in results:
        icon = "[OK]" if res["status"] == "SUCCESS" else "[ERR]"
        if res["status"] == "SUCCESS":
            status_text = "[green]SUCCESS[/green]"
        else:
            status_text = f"[red]FAILED ({res.get('error')})[/red]"
        console.print(f" {icon} {res['qca']}: {status_text}")
    console.print("=" * 60)
    console.print("[dim]Log files written to wbes_fetcher.log. Exiting gracefully.[/dim]\n")
