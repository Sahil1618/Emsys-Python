import datetime
import json
import os

from wbes.config import LATEST_SCHEDULE_PATH, MANIFEST_PATH, SCHEDULES_ROOT


def _qca_date_dir(qca: str, date_str: str) -> str:
    safe_date = date_str.replace("/", "-")
    path = os.path.join(SCHEDULES_ROOT, qca, safe_date)
    os.makedirs(path, exist_ok=True)
    return path


def schedule_file_path(qca: str, date_str: str, revision) -> str:
    """Latest revision file: wbes_schedules/<QCA>/<date>/schedule_rev_<n>.json"""
    return os.path.join(_qca_date_dir(qca, date_str), f"schedule_rev_{revision}.json")


def snapshot_dir(qca: str, date_str: str) -> str:
    path = os.path.join(_qca_date_dir(qca, date_str), "snapshots")
    os.makedirs(path, exist_ok=True)
    return path


def save_poll_snapshot(qca: str, date_str: str, data: dict, polled_at: datetime.datetime) -> str:
    """Timestamped copy of each poll (never overwritten by revision file)."""
    stamp = polled_at.strftime("%Y%m%d_%H%M%S")
    revision = data.get("ResponseBody", {}).get("FullSchdRevisionNo", "unknown")
    file_path = os.path.join(snapshot_dir(qca, date_str), f"poll_{stamp}_rev_{revision}.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return file_path.replace("\\", "/")


def append_change_log(qca: str, date_str: str, change_report: dict, polled_at: datetime.datetime) -> None:
    log_path = os.path.join(_qca_date_dir(qca, date_str), "changes.jsonl")
    entry = {
        "polled_at": polled_at.isoformat(timespec="seconds"),
        "summary": change_report,
    }
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def load_watch_state(path: str) -> dict:
    if not os.path.exists(path):
        return {"by_qca": {}}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"by_qca": {}}


def save_watch_state(path: str, state: dict) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def save_schedule(qca: str, date_str: str, data: dict) -> str:
    """Persist API response JSON and update manifest + latest pointer."""
    actual_rev = data.get("ResponseBody", {}).get("FullSchdRevisionNo", "unknown")
    file_path = schedule_file_path(qca, date_str, actual_rev)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    _update_manifest(qca, date_str, actual_rev, file_path)
    _update_latest_schedule(qca, date_str, actual_rev, file_path, data)
    return file_path


def _update_manifest(qca: str, date_str: str, revision, file_path: str) -> None:
    os.makedirs(SCHEDULES_ROOT, exist_ok=True)
    manifest = {"entries": []}
    if os.path.exists(MANIFEST_PATH):
        try:
            with open(MANIFEST_PATH, encoding="utf-8") as f:
                manifest = json.load(f)
        except (json.JSONDecodeError, OSError):
            manifest = {"entries": []}

    entry = {
        "qca": qca,
        "date": date_str,
        "revision": revision,
        "path": file_path.replace("\\", "/"),
        "saved_at": datetime.datetime.now().isoformat(timespec="seconds"),
    }
    manifest.setdefault("entries", []).append(entry)

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)


def _update_latest_schedule(
    qca: str, date_str: str, revision, file_path: str, data: dict
) -> None:
    """
    Maintain wbes_latest_schedule.json as a map keyed by QCA so multi-QCA runs
    do not overwrite each other.
    """
    latest = {"by_qca": {}, "last_updated": None}
    if os.path.exists(LATEST_SCHEDULE_PATH):
        try:
            with open(LATEST_SCHEDULE_PATH, encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict) and "by_qca" in loaded:
                latest = loaded
            elif isinstance(loaded, dict) and "ResponseBody" in loaded:
                latest = {"by_qca": {}, "last_updated": None}
        except (json.JSONDecodeError, OSError):
            pass

    latest["by_qca"][qca] = {
        "date": date_str,
        "revision": revision,
        "file": file_path.replace("\\", "/"),
        "data": data,
    }
    latest["last_updated"] = datetime.datetime.now().isoformat(timespec="seconds")

    with open(LATEST_SCHEDULE_PATH, "w", encoding="utf-8") as f:
        json.dump(latest, f, indent=2)
