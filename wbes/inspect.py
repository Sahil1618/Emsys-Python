"""Inspect saved WBES JSON structure without calling the live API."""

import json
import os

from rich.console import Console
from rich.panel import Panel
from rich.tree import Tree

from wbes.config import LATEST_SCHEDULE_PATH, SCHEDULES_ROOT
from wbes.schedule_parser import extract_schd_amounts

console = Console()


def _sample_from_latest() -> tuple[str | None, dict | None]:
    if not os.path.exists(LATEST_SCHEDULE_PATH):
        return None, None
    try:
        with open(LATEST_SCHEDULE_PATH, encoding="utf-8") as f:
            wrapper = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None, None

    if isinstance(wrapper, dict) and "by_qca" in wrapper:
        for qca, entry in wrapper.get("by_qca", {}).items():
            data = entry.get("data")
            if data:
                return qca, data
            path = entry.get("file")
            if path and os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    return qca, json.load(f)
    if isinstance(wrapper, dict) and "ResponseBody" in wrapper:
        return "unknown", wrapper
    return None, None


def _sample_from_snapshots() -> tuple[str | None, dict | None]:
    if not os.path.isdir(SCHEDULES_ROOT):
        return None, None
    newest = None
    newest_path = None
    newest_qca = None
    for qca in os.listdir(SCHEDULES_ROOT):
        qca_path = os.path.join(SCHEDULES_ROOT, qca)
        if not os.path.isdir(qca_path):
            continue
        for date_dir in os.listdir(qca_path):
            snap_dir = os.path.join(qca_path, date_dir, "snapshots")
            if not os.path.isdir(snap_dir):
                continue
            for name in os.listdir(snap_dir):
                if not name.endswith(".json"):
                    continue
                full = os.path.join(snap_dir, name)
                if newest is None or os.path.getmtime(full) > newest:
                    newest = os.path.getmtime(full)
                    newest_path = full
                    newest_qca = qca
    if newest_path:
        with open(newest_path, encoding="utf-8") as f:
            return newest_qca, json.load(f)
    return None, None


def inspect_saved_data() -> None:
    """Print how server data is structured in the last saved response."""
    qca, data = _sample_from_latest()
    if data is None:
        qca, data = _sample_from_snapshots()
    if data is None:
        console.print(
            "[yellow]No saved WBES data found. Run a fetch first:[/yellow]\n"
            "  python wbes_fetcher.py -q EESPL_QCA_BKN -d today -r -1 -n\n"
        )
        return

    rb = data.get("ResponseBody", {}) or {}
    status = data.get("ResponseStatus", {}) or {}
    groups = rb.get("GroupWiseDataList", []) or []

    tree = Tree(f"[bold cyan]WBES response[/bold cyan] (sample QCA: {qca})")
    tree.add(f"ResponseStatus.Code = [green]{status.get('Code')}[/green]")
    tree.add(f"ResponseStatus.Message = {status.get('Message')}")
    tree.add(f"ResponseBody.FullSchdRevisionNo = [yellow]{rb.get('FullSchdRevisionNo')}[/yellow]")
    tree.add(f"ResponseBody.GroupWiseDataList = {len(groups)} plant group(s)")

    if groups:
        g0 = groups[0]
        plant_node = tree.add(f"GroupWiseDataList[0].Acronym = {g0.get('Acronym')}")
        schedules = g0.get("FullschdList", []) or []
        plant_node.add(f"FullschdList = {len(schedules)} schedule row(s)")
        if schedules:
            s0 = schedules[0]
            sched_node = plant_node.add("FullschdList[0] fields")
            for field in ("EnergyScheduleTypeName", "SellerAcronym", "BuyerAcronym", "ApprovalNo"):
                sched_node.add(f"{field} = {s0.get(field)}")
            amounts = extract_schd_amounts(s0)
            sched_node.add(
                f"FullScheduleData → SchdAmount = [bold]{len(amounts)}[/bold] values "
                f"(15-min blocks for the day)"
            )
            if amounts:
                sched_node.add(f"  slot[0] (00:00) = {amounts[0]} MW")
                sched_node.add(f"  slot[1] (00:15) = {amounts[1]} MW")
                sched_node.add(f"  ... slot[95] (23:45) = {amounts[-1]} MW")

    console.print()
    console.print(
        Panel(
            tree,
            title="[bold]How data arrives from the server[/bold]",
            subtitle="Pull model: one POST returns full-day schedule JSON (not streamed)",
            border_style="cyan",
        )
    )
    console.print(
        "\n[dim]The server does not push updates to you. Plants publish on their schedule; "
        "you poll with SchdRevNo=-1 to read the latest revision. "
        "Use --watch to poll every 15 minutes and log changes.[/dim]\n"
    )
