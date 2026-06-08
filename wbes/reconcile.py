"""Compare two WBES API responses to detect revision and schedule changes."""

from wbes.schedule_parser import extract_schd_amounts


def _schedule_key(group_acronym: str, sched: dict) -> str:
    return "|".join(
        [
            group_acronym or "",
            sched.get("EnergyScheduleTypeName", ""),
            sched.get("SellerAcronym", ""),
            sched.get("BuyerAcronym", ""),
            str(sched.get("ApprovalNo", "")),
        ]
    )


def build_schedule_index(data: dict) -> dict:
    """Map schedule key -> metadata including 96-slot MW list."""
    rb = data.get("ResponseBody", {}) or {}
    index = {}
    for group in rb.get("GroupWiseDataList", []) or []:
        acronym = group.get("Acronym", "")
        for sched in group.get("FullschdList", []) or []:
            key = _schedule_key(acronym, sched)
            amounts = extract_schd_amounts(sched)
            index[key] = {
                "plant": acronym,
                "type": sched.get("EnergyScheduleTypeName"),
                "seller": sched.get("SellerAcronym"),
                "buyer": sched.get("BuyerAcronym"),
                "approval": sched.get("ApprovalNo"),
                "slots": amounts,
                "slot_count": len(amounts),
                "daily_total_mw": sum(amounts) if amounts else 0.0,
            }
    return {
        "revision": rb.get("FullSchdRevisionNo"),
        "schedules": index,
    }


def compare_schedules(previous: dict | None, current: dict) -> dict:
    """
    Diff two successful API payloads.

    Returns a report with revision_change, added/removed keys, and per-slot deltas.
    """
    prev_idx = build_schedule_index(previous) if previous else {"revision": None, "schedules": {}}
    curr_idx = build_schedule_index(current)

    prev_rev = prev_idx["revision"]
    curr_rev = curr_idx["revision"]
    prev_keys = set(prev_idx["schedules"])
    curr_keys = set(curr_idx["schedules"])

    slot_changes = []
    for key in sorted(curr_keys & prev_keys):
        prev_slots = prev_idx["schedules"][key]["slots"]
        curr_slots = curr_idx["schedules"][key]["slots"]
        max_len = max(len(prev_slots), len(curr_slots))
        changed_intervals = []
        for i in range(max_len):
            old_v = prev_slots[i] if i < len(prev_slots) else None
            new_v = curr_slots[i] if i < len(curr_slots) else None
            if old_v != new_v:
                changed_intervals.append(
                    {
                        "interval": i + 1,
                        "block": _interval_to_hhmm(i),
                        "old_mw": old_v,
                        "new_mw": new_v,
                    }
                )
        if changed_intervals:
            slot_changes.append(
                {
                    "key": key,
                    "plant": curr_idx["schedules"][key]["plant"],
                    "type": curr_idx["schedules"][key]["type"],
                    "changed_intervals": len(changed_intervals),
                    "intervals": changed_intervals[:20],
                    "truncated": len(changed_intervals) > 20,
                }
            )

    return {
        "revision_previous": prev_rev,
        "revision_current": curr_rev,
        "revision_changed": prev_rev is not None and prev_rev != curr_rev,
        "is_first_fetch": previous is None,
        "added_schedules": sorted(curr_keys - prev_keys),
        "removed_schedules": sorted(prev_keys - curr_keys),
        "slot_changes": slot_changes,
        "has_changes": previous is None
        or prev_rev != curr_rev
        or bool(curr_keys - prev_keys)
        or bool(prev_keys - curr_keys)
        or bool(slot_changes),
    }


def _interval_to_hhmm(interval_index: int) -> str:
    """Map 0-based 15-minute index to HH:MM (interval 0 -> 00:00)."""
    total_minutes = interval_index * 15
    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{hours:02d}:{minutes:02d}"


def format_change_summary(report: dict) -> str:
    """Human-readable one-line summary for console/logging."""
    if report.get("is_first_fetch"):
        return f"baseline snapshot (revision {report.get('revision_current')})"

    parts = []
    if report.get("revision_changed"):
        parts.append(
            f"revision {report.get('revision_previous')} -> {report.get('revision_current')}"
        )
    if report.get("added_schedules"):
        parts.append(f"+{len(report['added_schedules'])} schedule(s)")
    if report.get("removed_schedules"):
        parts.append(f"-{len(report['removed_schedules'])} schedule(s)")
    if report.get("slot_changes"):
        parts.append(f"{len(report['slot_changes'])} schedule(s) with slot MW changes")
    return ", ".join(parts) if parts else "no changes detected"
