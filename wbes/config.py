import os

import dotenv
from rich.console import Console

console = Console()

EXCEL_PATH = "PLANT NAMES ALL QCA (4).xlsx"
ENV_PATH = ".env"
SCHEDULES_ROOT = "wbes_schedules"
LATEST_SCHEDULE_PATH = "wbes_latest_schedule.json"
LOG_PATH = "wbes_fetcher.log"
MANIFEST_PATH = os.path.join(SCHEDULES_ROOT, "manifest.json")

QCAS = [
    "EESPL_QCA_BKN",
    "EESPL_QCA_BHDL",
    "EMSYS_QCA_BHDL_2",
    "EESPL_QCA_BKN2",
]

QCA_LABELS = {
    "EESPL_QCA_BKN": "EESPL_QCA_BKN (Bikaner Region)",
    "EESPL_QCA_BHDL": "EESPL_QCA_BHDL (Bhadla Region)",
    "EMSYS_QCA_BHDL_2": "EMSYS_QCA_BHDL_2 (Bhadla Region 2)",
    "EESPL_QCA_BKN2": "EESPL_QCA_BKN2 (Bikaner Region 2)",
}


def bootstrap_env_from_excel() -> bool:
    """Create .env from the Excel master sheet when missing or empty."""
    if os.path.exists(ENV_PATH) and os.path.getsize(ENV_PATH) > 0:
        return True

    console.print(
        "[yellow][*] .env configuration file not found or empty. "
        "Bootstrapping credentials from Excel...[/yellow]"
    )
    if not os.path.exists(EXCEL_PATH):
        console.print(
            "[bold red][ERROR] Excel master sheet "
            f"'{EXCEL_PATH}' is also missing![/bold red]"
        )
        console.print(
            "Please place the Excel sheet in this directory or create a .env file manually."
        )
        return False

    try:
        import openpyxl

        wb = openpyxl.load_workbook(EXCEL_PATH, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))

        qca_headers = [rows[0][i] for i in [2, 3, 4, 5]]
        usernames = [rows[19][i] for i in [2, 3, 4, 5]]
        passwords = [rows[20][i] for i in [2, 3, 4, 5]]
        api_keys = [rows[21][i] for i in [2, 3, 4, 5]]

        env_lines = [
            "# ------------------------------------------------------------------------------",
            "# --- GRID-INDIA / POSOCO WBES INTEGRATION CONFIGURATION -----------------------",
            "# ------------------------------------------------------------------------------",
            "BASE_URL=https://gateway.grid-india.in/POSOCO",
            "DEFAULT_QCA=EESPL_QCA_BKN",
            "",
        ]

        for i, qca in enumerate(qca_headers):
            if qca:
                env_lines.append(f"# Credentials for {qca}")
                env_lines.append(f"{qca}_USERNAME={usernames[i]}")
                env_lines.append(f"{qca}_PASSWORD={passwords[i]}")
                env_lines.append(f"{qca}_API_KEY={api_keys[i]}")
                env_lines.append("")

        with open(ENV_PATH, "w", encoding="utf-8") as f:
            f.write("\n".join(env_lines))

        console.print(
            "[bold green][OK] Automatically bootstrapped credentials from Excel "
            "and saved to .env![/bold green]"
        )
        return True

    except Exception as exc:
        console.print(f"[bold red][ERROR] Failed to bootstrap .env from Excel: {exc}[/bold red]")
        return False


def load_environment() -> None:
    bootstrap_env_from_excel()
    dotenv.load_dotenv()


load_environment()
BASE_URL = os.getenv("BASE_URL", "https://gateway.grid-india.in/POSOCO")
