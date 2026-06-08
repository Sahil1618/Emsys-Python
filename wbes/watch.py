# import datetime
# import json
# import os
# import time

# from rich.console import Console

# from wbes.config import SCHEDULES_ROOT
# from wbes.reconcile import compare_schedules, format_change_summary
# from wbes.runner import resolve_qca_list, run_fetch_workflow
# from wbes.storage import append_change_log, save_poll_snapshot, save_watch_state, load_watch_state

# console = Console()
# WATCH_STATE_PATH = os.path.join(SCHEDULES_ROOT, "watch_state.json")


# def seconds_until_next_tick(interval_minutes: int, align_to_clock: bool) -> float:
#     """Sleep duration until the next poll (aligned to :00/:15/:30/:45 when enabled)."""
#     if not align_to_clock:
#         return interval_minutes * 60

#     now = datetime.datetime.now()
#     step = interval_minutes
#     minute_slot = (now.minute // step + 1) * step
#     if minute_slot >= 60:
#         next_run = (now + datetime.timedelta(hours=1)).replace(minute=0, second=5, microsecond=0)
#     else:
#         next_run = now.replace(minute=minute_slot, second=5, microsecond=0)

#     delta = (next_run - now).total_seconds()
#     return max(delta, 1.0)


# def _state_for_qca(state: dict, qca: str, date_str: str) -> dict | None:
#     entry = state.get("by_qca", {}).get(qca)
#     if not entry or entry.get("date") != date_str:
#         return None
#     path = entry.get("last_snapshot")
#     if not path or not os.path.exists(path):
#         return entry.get("last_data")
#     try:
#         with open(path, encoding="utf-8") as f:
#             return json.load(f)
#     except (json.JSONDecodeError, OSError):
#         return entry.get("last_data")


# def run_poll_cycle(
#     qcas: list[str],
#     date_str: str,
#     *,
#     quiet: bool = False,
# ) -> dict:
#     """Fetch latest revision (-1) for each QCA, snapshot, reconcile, and update state."""
#     state = load_watch_state(WATCH_STATE_PATH)
#     cycle_report = {"polled_at": datetime.datetime.now().isoformat(timespec="seconds"), "qcas": {}}

#     results = run_fetch_workflow(
#         qcas,
#         date_str,
#         "-1",
#         show_tables=not quiet,
#     )

#     for res in results:
#         qca = res["qca"]
#         if res["status"] != "SUCCESS":
#             cycle_report["qcas"][qca] = {"status": "FAILED", "error": res.get("error")}
#             continue

#         data_path = res.get("file_saved")
#         try:
#             with open(data_path, encoding="utf-8") as f:
#                 current_data = json.load(f)
#         except (json.JSONDecodeError, OSError) as exc:
#             cycle_report["qcas"][qca] = {"status": "FAILED", "error": f"read_saved: {exc}"}
#             continue

#         previous_data = _state_for_qca(state, qca, date_str)
#         change_report = compare_schedules(previous_data, current_data)
#         summary = format_change_summary(change_report)

#         polled_at = datetime.datetime.now()
#         snapshot_path = save_poll_snapshot(qca, date_str, current_data, polled_at)
#         append_change_log(qca, date_str, change_report, polled_at)

#         state.setdefault("by_qca", {})[qca] = {
#             "date": date_str,
#             "revision": change_report.get("revision_current"),
#             "last_snapshot": snapshot_path,
#             "last_polled_at": polled_at.isoformat(timespec="seconds"),
#             "last_summary": summary,
#         }

#         cycle_report["qcas"][qca] = {
#             "status": "SUCCESS",
#             "snapshot": snapshot_path,
#             "summary": summary,
#             "has_changes": change_report.get("has_changes"),
#             "revision": change_report.get("revision_current"),
#         }

#         if not quiet or change_report.get("has_changes"):
#             icon = "[yellow]CHANGE[/yellow]" if change_report.get("has_changes") else "[dim]same[/dim]"
#             console.print(f"  {qca}: {icon} {summary}")

#     save_watch_state(WATCH_STATE_PATH, state)
#     return cycle_report


# def run_watch_loop(
#     qca_choice: str,
#     date_str: str,
#     *,
#     interval_minutes: int = 15,
#     align_to_clock: bool = True,
#     max_cycles: int | None = None,
#     quiet: bool = False,
# ) -> None:
#     """
#     Poll GRID-INDIA on a fixed interval until interrupted (Ctrl+C).

#     Always uses SchdRevNo=-1 (latest revision). Each cycle saves a timestamped
#     snapshot and appends detected changes to changes.jsonl.
#     """
#     qcas = resolve_qca_list(qca_choice)
#     os.makedirs(SCHEDULES_ROOT, exist_ok=True)

#     console.print(
#         f"\n[bold cyan]WBES watch mode started[/bold cyan]\n"
#         f"  QCAs: [green]{', '.join(qcas)}[/green]\n"
#         f"  Date: [green]{date_str}[/green] | Revision: [green]-1 (latest)[/green]\n"
#         f"  Interval: [green]{interval_minutes} minutes[/green] | "
#         f"Align to clock: [green]{align_to_clock}[/green]\n"
#         f"  Snapshots: [dim]wbes_schedules/<QCA>/<date>/snapshots/[/dim]\n"
#         f"  Change log: [dim]wbes_schedules/<QCA>/<date>/changes.jsonl[/dim]\n"
#         f"  Press Ctrl+C to stop.\n"
#     )

#     cycle = 0
#     try:
#         while True:
#             cycle += 1
#             console.print(
#                 f"\n[bold]--- Poll cycle {cycle} @ "
#                 f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---[/bold]"
#             )
#             run_poll_cycle(qcas, date_str, quiet=quiet)

#             if max_cycles is not None and cycle >= max_cycles:
#                 console.print(f"\n[dim]Completed {max_cycles} cycle(s). Exiting watch mode.[/dim]\n")
#                 break

#             wait_sec = seconds_until_next_tick(interval_minutes, align_to_clock)
#             next_at = datetime.datetime.now() + datetime.timedelta(seconds=wait_sec)
#             console.print(
#                 f"[dim]Next poll in {int(wait_sec)}s (at {next_at.strftime('%H:%M:%S')})[/dim]"
#             )
#             time.sleep(wait_sec)
#     except KeyboardInterrupt:
#         console.print("\n[yellow]Watch mode stopped by user.[/yellow]\n")


import datetime
import json
import os
import time

from rich.console import Console

from wbes.config import SCHEDULES_ROOT
from wbes.reconcile import compare_schedules, format_change_summary
from wbes.runner import resolve_qca_list, run_fetch_workflow
from wbes.storage import append_change_log, save_poll_snapshot, save_watch_state, load_watch_state

console = Console()
WATCH_STATE_PATH = os.path.join(SCHEDULES_ROOT, "watch_state.json")


def seconds_until_next_tick(interval_minutes: int, align_to_clock: bool) -> float:
    """Sleep duration until the next poll (aligned to :00/:15/:30/:45 when enabled)."""
    if not align_to_clock:
        return interval_minutes * 60

    now = datetime.datetime.now()
    step = interval_minutes
    minute_slot = (now.minute // step + 1) * step
    if minute_slot >= 60:
        next_run = (now + datetime.timedelta(hours=1)).replace(minute=0, second=5, microsecond=0)
    else:
        next_run = now.replace(minute=minute_slot, second=5, microsecond=0)

    delta = (next_run - now).total_seconds()
    return max(delta, 1.0)


def _state_for_qca(state: dict, qca: str, date_str: str) -> dict | None:
    entry = state.get("by_qca", {}).get(qca)
    if not entry or entry.get("date") != date_str:
        return None
    path = entry.get("last_snapshot")
    if not path or not os.path.exists(path):
        return entry.get("last_data")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return entry.get("last_data")


def _export_to_excel(qca: str, date_str: str, data: dict) -> None:
    """Export a single QCA's schedule data to a block-wise Excel file."""
    try:
        from wbes.excel_exporter import export_schedule_to_excel
        from wbes.schedule_parser import iter_schedule_rows

        rows = list(iter_schedule_rows(data, qca))
        if not rows:
            console.print(f"  [yellow][!] No rows for {qca} — Excel skipped.[/yellow]")
            return

        path = export_schedule_to_excel(rows, qca, date_str)
        console.print(f"  [bold green][✓] Excel saved:[/bold green] {path}")

    except Exception as exc:
        console.print(f"  [red][!] Excel export failed for {qca}: {exc}[/red]")


def run_poll_cycle(
    qcas: list[str],
    date_str: str,
    *,
    quiet: bool = False,
    export_excel: bool = True,
) -> dict:
    """Fetch latest revision (-1) for each QCA, snapshot, reconcile, and update state."""
    state = load_watch_state(WATCH_STATE_PATH)
    cycle_report = {"polled_at": datetime.datetime.now().isoformat(timespec="seconds"), "qcas": {}}

    results = run_fetch_workflow(
        qcas,
        date_str,
        "-1",
        show_tables=not quiet,
    )

    for res in results:
        qca = res["qca"]
        if res["status"] != "SUCCESS":
            cycle_report["qcas"][qca] = {"status": "FAILED", "error": res.get("error")}
            continue

        data_path = res.get("file_saved")
        try:
            with open(data_path, encoding="utf-8") as f:
                current_data = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            cycle_report["qcas"][qca] = {"status": "FAILED", "error": f"read_saved: {exc}"}
            continue

        previous_data = _state_for_qca(state, qca, date_str)
        change_report = compare_schedules(previous_data, current_data)
        summary = format_change_summary(change_report)

        polled_at = datetime.datetime.now()
        snapshot_path = save_poll_snapshot(qca, date_str, current_data, polled_at)
        append_change_log(qca, date_str, change_report, polled_at)

        state.setdefault("by_qca", {})[qca] = {
            "date": date_str,
            "revision": change_report.get("revision_current"),
            "last_snapshot": snapshot_path,
            "last_polled_at": polled_at.isoformat(timespec="seconds"),
            "last_summary": summary,
        }

        cycle_report["qcas"][qca] = {
            "status": "SUCCESS",
            "snapshot": snapshot_path,
            "summary": summary,
            "has_changes": change_report.get("has_changes"),
            "revision": change_report.get("revision_current"),
        }

        if not quiet or change_report.get("has_changes"):
            icon = "[yellow]CHANGE[/yellow]" if change_report.get("has_changes") else "[dim]same[/dim]"
            console.print(f"  {qca}: {icon} {summary}")

        # ── Excel export ──────────────────────────────────────────────────────
        if export_excel:
            _export_to_excel(qca, date_str, current_data)

    save_watch_state(WATCH_STATE_PATH, state)
    return cycle_report


def run_watch_loop(
    qca_choice: str,
    date_str: str,
    *,
    interval_minutes: int = 15,
    align_to_clock: bool = True,
    max_cycles: int | None = None,
    quiet: bool = False,
    export_excel: bool = True,
) -> None:
    """
    Poll GRID-INDIA on a fixed interval until interrupted (Ctrl+C).

    Always uses SchdRevNo=-1 (latest revision). Each cycle saves a timestamped
    snapshot, appends detected changes to changes.jsonl, and exports to Excel.
    """
    qcas = resolve_qca_list(qca_choice)
    os.makedirs(SCHEDULES_ROOT, exist_ok=True)

    console.print(
        f"\n[bold cyan]WBES watch mode started[/bold cyan]\n"
        f"  QCAs: [green]{', '.join(qcas)}[/green]\n"
        f"  Date: [green]{date_str}[/green] | Revision: [green]-1 (latest)[/green]\n"
        f"  Interval: [green]{interval_minutes} minutes[/green] | "
        f"Align to clock: [green]{align_to_clock}[/green]\n"
        f"  Excel export: [green]{'enabled' if export_excel else 'disabled'}[/green]\n"
        f"  Snapshots: [dim]wbes_schedules/<QCA>/<date>/snapshots/[/dim]\n"
        f"  Change log: [dim]wbes_schedules/<QCA>/<date>/changes.jsonl[/dim]\n"
        f"  Press Ctrl+C to stop.\n"
    )

    cycle = 0
    try:
        while True:
            cycle += 1
            console.print(
                f"\n[bold]--- Poll cycle {cycle} @ "
                f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---[/bold]"
            )
            run_poll_cycle(qcas, date_str, quiet=quiet, export_excel=export_excel)

            if max_cycles is not None and cycle >= max_cycles:
                console.print(f"\n[dim]Completed {max_cycles} cycle(s). Exiting watch mode.[/dim]\n")
                break

            wait_sec = seconds_until_next_tick(interval_minutes, align_to_clock)
            next_at = datetime.datetime.now() + datetime.timedelta(seconds=wait_sec)
            console.print(
                f"[dim]Next poll in {int(wait_sec)}s (at {next_at.strftime('%H:%M:%S')})[/dim]"
            )
            time.sleep(wait_sec)
    except KeyboardInterrupt:
        console.print("\n[yellow]Watch mode stopped by user.[/yellow]\n")