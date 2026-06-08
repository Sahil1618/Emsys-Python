# #!/usr/bin/env python3
# """
# GRID-INDIA / POSOCO WBES Energy Fetch Engine — entry point.

# Run: python wbes_fetcher.py
# See README.md for full usage.
# """

# import argparse
# import datetime
# import sys

# # Graceful dependency check for external libraries
# try:
#     from rich.console import Console
# except ImportError as err:
#     print("\n" + "=" * 60)
#     print("[-] DEPENDENCY ERROR DETECTED")
#     print("=" * 60)
#     print(f"Missing library: {err.name}")
#     print("To install all required libraries, please run this command in your terminal:")
#     print("  pip install -r requirements.txt")
#     print("=" * 60 + "\n")
#     sys.exit(1)

# console = Console()


# def _check_optional_deps() -> None:
#     try:
#         import dotenv  # noqa: F401
#         import openpyxl  # noqa: F401
#         import questionary  # noqa: F401
#         import requests  # noqa: F401
#     except ImportError as err:
#         print("\n" + "=" * 60)
#         print("[-] DEPENDENCY ERROR DETECTED")
#         print("=" * 60)
#         print(f"Missing library: {err.name}")
#         print("  pip install -r requirements.txt")
#         print("=" * 60 + "\n")
#         sys.exit(1)


# def resolve_date_string(date_input: str, today_str: str, tomorrow_str: str, yesterday_str: str) -> str:
#     if date_input.lower() == "today":
#         return today_str
#     if date_input.lower() == "tomorrow":
#         return tomorrow_str
#     if date_input.lower() == "yesterday":
#         return yesterday_str
#     return date_input


# def main() -> None:
#     _check_optional_deps()

#     from wbes.config import QCAS
#     from wbes.interactive_menu import run_interactive_terminal_menu
#     from wbes.runner import print_run_summary, resolve_qca_list, run_fetch_workflow

#     parser = argparse.ArgumentParser(description="GRID-INDIA / POSOCO WBES Energy Fetch Engine")
#     parser.add_argument(
#         "-q",
#         "--qca",
#         choices=[*QCAS, "ALL"],
#         help="Target QCA to fetch schedules for",
#     )
#     parser.add_argument(
#         "-d",
#         "--date",
#         help="Target scheduling date (DD-MM-YYYY, or today/tomorrow/yesterday)",
#     )
#     parser.add_argument("-r", "--rev", help="Schedule revision number (default: -1)")
#     parser.add_argument(
#         "-n",
#         "--non-interactive",
#         action="store_true",
#         help="Run without interactive prompts",
#     )
#     parser.add_argument(
#         "-t",
#         "--tui",
#         action="store_true",
#         help="Launch full-screen Textual TUI App",
#     )
#     parser.add_argument(
#         "-w",
#         "--watch",
#         action="store_true",
#         help="Poll the server on a schedule (default every 15 min) until Ctrl+C",
#     )
#     parser.add_argument(
#         "--interval-minutes",
#         type=int,
#         default=15,
#         metavar="N",
#         help="Minutes between polls in watch mode (default: 15)",
#     )
#     parser.add_argument(
#         "--no-align",
#         action="store_true",
#         help="Do not align watch polls to clock :00/:15/:30/:45",
#     )
#     parser.add_argument(
#         "--cycles",
#         type=int,
#         default=None,
#         metavar="N",
#         help="Stop watch mode after N poll cycles (default: run until Ctrl+C)",
#     )
#     parser.add_argument(
#         "--inspect",
#         action="store_true",
#         help="Show structure of saved WBES JSON (from last fetch); no API call",
#     )

#     args = parser.parse_args()

#     if args.inspect:
#         from wbes.inspect import inspect_saved_data

#         inspect_saved_data()
#         return

#     today_dt = datetime.date.today()
#     today_str = today_dt.strftime("%d-%m-%Y")
#     tomorrow_str = (today_dt + datetime.timedelta(days=1)).strftime("%d-%m-%Y")
#     yesterday_str = (today_dt - datetime.timedelta(days=1)).strftime("%d-%m-%Y")

#     if args.watch:
#         from wbes.watch import run_watch_loop

#         qca_choice = args.qca if args.qca is not None else "ALL"
#         date_input = args.date if args.date is not None else today_str
#         date_str = resolve_date_string(date_input, today_str, tomorrow_str, yesterday_str)
#         run_watch_loop(
#             qca_choice,
#             date_str,
#             interval_minutes=max(1, args.interval_minutes),
#             align_to_clock=not args.no_align,
#             max_cycles=args.cycles,
#         )
#         return

#     is_non_interactive = args.non_interactive or (
#         args.qca is not None or args.date is not None or args.rev is not None
#     )

#     if is_non_interactive:
#         qca_choice = args.qca if args.qca is not None else "ALL"
#         date_input = args.date if args.date is not None else today_str
#         date_str = resolve_date_string(date_input, today_str, tomorrow_str, yesterday_str)
#         rev_str = args.rev if args.rev is not None else "-1"

#         console.print("[bold cyan]Running in non-interactive CLI mode.[/bold cyan]")
#         console.print(f"  QCA choice: [green]{qca_choice}[/green]")
#         console.print(f"  Target Date: [green]{date_str}[/green]")
#         console.print(f"  Revision: [green]{rev_str}[/green]")

#         results = run_fetch_workflow(resolve_qca_list(qca_choice), date_str, rev_str)
#         print_run_summary(results)
#         return

#     if args.tui:
#         try:
#             from wbes.tui_app import WBESTuiApp

#             WBESTuiApp().run()
#         except ImportError as err:
#             console.print(
#                 f"[yellow][!] Textual not installed ({err}). "
#                 "Falling back to interactive terminal menu...[/yellow]"
#             )
#             run_interactive_terminal_menu(today_str, tomorrow_str, yesterday_str)
#         except Exception as exc:
#             console.print(
#                 f"[yellow][!] Could not launch Textual TUI: {exc}. "
#                 "Falling back to interactive terminal menu...[/yellow]"
#             )
#             run_interactive_terminal_menu(today_str, tomorrow_str, yesterday_str)
#     else:
#         run_interactive_terminal_menu(today_str, tomorrow_str, yesterday_str)


# if __name__ == "__main__":
#     try:
#         main()
#     except KeyboardInterrupt:
#         console.print("\n[yellow][!] Script interrupted by keyboard. Exiting...[/yellow]\n")
#         sys.exit(0)


#!/usr/bin/env python3
#!/usr/bin/env python3
"""
GRID-INDIA / POSOCO WBES Energy Fetch Engine — entry point.

Run: python wbes_fetcher.py
See README.md for full usage.
"""

import argparse
import datetime
import json
import sys

# Graceful dependency check for external libraries
try:
    from rich.console import Console
except ImportError as err:
    print("\n" + "=" * 60)
    print("[-] DEPENDENCY ERROR DETECTED")
    print("=" * 60)
    print(f"Missing library: {err.name}")
    print("To install all required libraries, please run this command in your terminal:")
    print("  pip install -r requirements.txt")
    print("=" * 60 + "\n")
    sys.exit(1)

console = Console()


def _check_optional_deps() -> None:
    try:
        import dotenv  # noqa: F401
        import openpyxl  # noqa: F401
        import questionary  # noqa: F401
        import requests  # noqa: F401
    except ImportError as err:
        print("\n" + "=" * 60)
        print("[-] DEPENDENCY ERROR DETECTED")
        print("=" * 60)
        print(f"Missing library: {err.name}")
        print("  pip install -r requirements.txt")
        print("=" * 60 + "\n")
        sys.exit(1)


def resolve_date_string(date_input: str, today_str: str, tomorrow_str: str, yesterday_str: str) -> str:
    if date_input.lower() == "today":
        return today_str
    if date_input.lower() == "tomorrow":
        return tomorrow_str
    if date_input.lower() == "yesterday":
        return yesterday_str
    return date_input


def _export_results_to_excel(results: list, date_str: str) -> None:
    """
    Export successful fetch results to block-wise Excel files.
    Reads data from the saved JSON file since runner.py does not
    return the raw API response in the results list.
    """
    try:
        from wbes.excel_exporter import export_schedule_to_excel
        from wbes.schedule_parser import iter_schedule_rows
    except ImportError as err:
        console.print(f"[yellow][!] Excel export skipped — missing module: {err}[/yellow]")
        return

    exported_any = False

    for result in results:
        if result.get("status") != "SUCCESS":
            continue

        qca_name  = result.get("qca")
        file_path = result.get("file_saved")  # e.g. wbes_schedules/EESPL_QCA_BKN/08-06-2026/schedule_rev_100.json

        if not qca_name or not file_path:
            console.print(f"[yellow][!] No saved file path for {qca_name} — Excel skipped.[/yellow]")
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            console.print(f"[red][!] Could not read JSON for {qca_name}: {exc}[/red]")
            continue

        try:
            rows = list(iter_schedule_rows(data, qca_name))
            if not rows:
                console.print(f"[yellow][!] No schedule rows for {qca_name} — Excel skipped.[/yellow]")
                continue

            path = export_schedule_to_excel(rows, qca_name, date_str)
            console.print(f"[bold green][✓] Excel saved:[/bold green] {path}")
            exported_any = True

        except Exception as exc:
            console.print(f"[red][!] Excel export failed for {qca_name}: {exc}[/red]")

    if not exported_any:
        console.print("[yellow][!] No successful fetches — no Excel files generated.[/yellow]")


def main() -> None:
    _check_optional_deps()

    from wbes.config import QCAS
    from wbes.interactive_menu import run_interactive_terminal_menu
    from wbes.runner import print_run_summary, resolve_qca_list, run_fetch_workflow

    parser = argparse.ArgumentParser(description="GRID-INDIA / POSOCO WBES Energy Fetch Engine")
    parser.add_argument(
        "-q",
        "--qca",
        choices=[*QCAS, "ALL"],
        help="Target QCA to fetch schedules for",
    )
    parser.add_argument(
        "-d",
        "--date",
        help="Target scheduling date (DD-MM-YYYY, or today/tomorrow/yesterday)",
    )
    parser.add_argument("-r", "--rev", help="Schedule revision number (default: -1)")
    parser.add_argument(
        "-n",
        "--non-interactive",
        action="store_true",
        help="Run without interactive prompts",
    )
    parser.add_argument(
        "-t",
        "--tui",
        action="store_true",
        help="Launch full-screen Textual TUI App",
    )
    parser.add_argument(
        "-w",
        "--watch",
        action="store_true",
        help="Poll the server on a schedule (default every 15 min) until Ctrl+C",
    )
    parser.add_argument(
        "--interval-minutes",
        type=int,
        default=15,
        metavar="N",
        help="Minutes between polls in watch mode (default: 15)",
    )
    parser.add_argument(
        "--no-align",
        action="store_true",
        help="Do not align watch polls to clock :00/:15/:30/:45",
    )
    parser.add_argument(
        "--cycles",
        type=int,
        default=None,
        metavar="N",
        help="Stop watch mode after N poll cycles (default: run until Ctrl+C)",
    )
    parser.add_argument(
        "--inspect",
        action="store_true",
        help="Show structure of saved WBES JSON (from last fetch); no API call",
    )
    parser.add_argument(
        "--no-excel",
        action="store_true",
        help="Disable automatic Excel export after fetch",
    )

    args = parser.parse_args()

    if args.inspect:
        from wbes.inspect import inspect_saved_data

        inspect_saved_data()
        return

    today_dt      = datetime.date.today()
    today_str     = today_dt.strftime("%d-%m-%Y")
    tomorrow_str  = (today_dt + datetime.timedelta(days=1)).strftime("%d-%m-%Y")
    yesterday_str = (today_dt - datetime.timedelta(days=1)).strftime("%d-%m-%Y")

    excel_enabled = not args.no_excel

    if args.watch:
        from wbes.watch import run_watch_loop

        qca_choice = args.qca if args.qca is not None else "ALL"
        date_input = args.date if args.date is not None else today_str
        date_str   = resolve_date_string(date_input, today_str, tomorrow_str, yesterday_str)
        run_watch_loop(
            qca_choice,
            date_str,
            interval_minutes=max(1, args.interval_minutes),
            align_to_clock=not args.no_align,
            max_cycles=args.cycles,
            export_excel= not args.no_excel,
        )
        return

    is_non_interactive = args.non_interactive or (
        args.qca is not None or args.date is not None or args.rev is not None
    )

    if is_non_interactive:
        qca_choice = args.qca if args.qca is not None else "ALL"
        date_input = args.date if args.date is not None else today_str
        date_str   = resolve_date_string(date_input, today_str, tomorrow_str, yesterday_str)
        rev_str    = args.rev if args.rev is not None else "-1"

        console.print("[bold cyan]Running in non-interactive CLI mode.[/bold cyan]")
        console.print(f"  QCA choice:  [green]{qca_choice}[/green]")
        console.print(f"  Target Date: [green]{date_str}[/green]")
        console.print(f"  Revision:    [green]{rev_str}[/green]")

        results = run_fetch_workflow(resolve_qca_list(qca_choice), date_str, rev_str)
        print_run_summary(results)

        # ── Excel export ──────────────────────────────────────────────────────
        if excel_enabled:
            console.print("\n[bold cyan]Exporting to Excel...[/bold cyan]")
            _export_results_to_excel(results, date_str)

        return

    if args.tui:
        try:
            from wbes.tui_app import WBESTuiApp

            WBESTuiApp().run()
        except ImportError as err:
            console.print(
                f"[yellow][!] Textual not installed ({err}). "
                "Falling back to interactive terminal menu...[/yellow]"
            )
            run_interactive_terminal_menu(today_str, tomorrow_str, yesterday_str)
        except Exception as exc:
            console.print(
                f"[yellow][!] Could not launch Textual TUI: {exc}. "
                "Falling back to interactive terminal menu...[/yellow]"
            )
            run_interactive_terminal_menu(today_str, tomorrow_str, yesterday_str)
    else:
        run_interactive_terminal_menu(today_str, tomorrow_str, yesterday_str)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow][!] Script interrupted by keyboard. Exiting...[/yellow]\n")
        sys.exit(0)