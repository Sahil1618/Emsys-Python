import datetime
import json

from wbes.config import LOG_PATH


def append_fetch_log(qca_name: str, result: dict) -> None:
    """Append an error entry to wbes_fetcher.log without printing to console."""
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as log_file:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_file.write(
                f"[{timestamp}] QCA: {qca_name} | ERROR: {result.get('status')} | "
                f"Msg: {result.get('message')} | Res: {json.dumps(result)}\n"
            )
    except OSError:
        pass
