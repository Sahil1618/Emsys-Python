import datetime

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable, Footer, Header, Input, Label, RichLog, Select

from wbes.runner import resolve_qca_list, run_fetch_workflow


class WBESTuiApp(App):
    """Textual TUI for fetching GRID-INDIA WBES daily energy schedules."""

    TITLE = "GRID-INDIA / POSOCO WBES Energy Fetch Engine"
    SUB_TITLE = "Qualified Coordinating Agency (QCA) System Dashboard"
    BINDINGS = [
        ("q", "quit", "Quit App"),
        ("f", "fetch", "Fetch Schedule"),
    ]

    CSS = """
    Screen {
        background: #0f172a;
    }

    #left-panel {
        width: 35%;
        border-right: tall #334155;
        padding: 1 2;
        background: #1e293b;
        height: 100%;
    }

    #right-panel {
        width: 65%;
        padding: 1 2;
        height: 100%;
    }

    .field-label {
        color: #94a3b8;
        margin-top: 1;
        margin-bottom: 0;
        text-style: bold;
    }

    #btn-fetch {
        margin-top: 2;
        width: 100%;
        background: #0284c7;
        color: white;
        text-style: bold;
        border: none;
    }

    #btn-fetch:hover {
        background: #0ea5e9;
    }

    #status-lbl {
        color: #38bdf8;
        text-style: bold;
        margin-bottom: 1;
        background: #1e293b;
        padding: 1;
        border: solid #334155;
    }

    RichLog {
        background: #020617;
        border: solid #1e293b;
        color: #f8fafc;
        height: 100%;
    }

    DataTable {
        background: #020617;
        border: solid #1e293b;
        height: 100%;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="left-panel"):
                yield Label("Step 1: Select Target QCA", classes="field-label")
                yield Select(
                    options=[
                        ("EESPL_QCA_BKN (Bikaner Region)", "EESPL_QCA_BKN"),
                        ("EESPL_QCA_BHDL (Bhadla Region)", "EESPL_QCA_BHDL"),
                        ("EMSYS_QCA_BHDL_2 (Bhadla Region 2)", "EMSYS_QCA_BHDL_2"),
                        ("EESPL_QCA_BKN2 (Bikaner Region 2)", "EESPL_QCA_BKN2"),
                        ("Fetch All 4 QCAs Sequentially", "ALL"),
                    ],
                    value="EESPL_QCA_BKN",
                    id="qca-select",
                )

                yield Label("Step 2: Choose Scheduling Date", classes="field-label")
                today_dt = datetime.date.today()
                today_str = today_dt.strftime("%d-%m-%Y")
                tomorrow_str = (today_dt + datetime.timedelta(days=1)).strftime("%d-%m-%Y")
                yesterday_str = (today_dt - datetime.timedelta(days=1)).strftime("%d-%m-%Y")

                yield Select(
                    options=[
                        (f"Today ({today_str})", "today"),
                        (f"Tomorrow ({tomorrow_str})", "tomorrow"),
                        (f"Yesterday ({yesterday_str})", "yesterday"),
                        ("Custom Date (Manually enter)", "custom"),
                    ],
                    value="today",
                    id="date-select",
                )

                yield Label("Custom Target Date (DD-MM-YYYY)", classes="field-label")
                yield Input(value=today_str, placeholder="DD-MM-YYYY", id="date-input", disabled=True)

                yield Label("Step 3: Select Revision Number", classes="field-label")
                yield Input(value="-1", placeholder="-1", id="rev-input")

                yield Button("Fetch Schedules [F]", id="btn-fetch", variant="primary")

            with Vertical(id="right-panel"):
                yield Label("System Status: Ready", id="status-lbl")
                yield DataTable(id="results-table")
                yield RichLog(id="diagnostics-log", highlight=True, markup=True)
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#results-table", DataTable)
        table.add_columns("QCA", "Plant", "Type", "Seller", "Buyer", "Daily Total (MW)")
        log_widget = self.query_one("#diagnostics-log", RichLog)
        self.call_from_thread(setattr, log_widget.styles, "height", "0%")

    @on(Select.Changed, "#date-select")
    def on_date_change(self, event: Select.Changed) -> None:
        inp = self.query_one("#date-input", Input)
        today_dt = datetime.date.today()
        today_str = today_dt.strftime("%d-%m-%Y")
        tomorrow_str = (today_dt + datetime.timedelta(days=1)).strftime("%d-%m-%Y")
        yesterday_str = (today_dt - datetime.timedelta(days=1)).strftime("%d-%m-%Y")

        if event.value == "custom":
            inp.disabled = False
        else:
            inp.disabled = True
            if event.value == "today":
                inp.value = today_str
            elif event.value == "tomorrow":
                inp.value = tomorrow_str
            elif event.value == "yesterday":
                inp.value = yesterday_str

    @on(Button.Pressed, "#btn-fetch")
    def action_fetch(self) -> None:
        self.run_worker(self.fetch_task, thread=True)

    def update_status(self, text: str) -> None:
        lbl = self.query_one("#status-lbl", Label)
        self.call_from_thread(setattr, lbl, "renderable", text)

    def write_log(self, text: str) -> None:
        log_widget = self.query_one("#diagnostics-log", RichLog)
        self.call_from_thread(log_widget.write, text)

    def fetch_task(self) -> None:
        qca_val = self.query_one("#qca-select", Select).value
        date_shortcut = self.query_one("#date-select", Select).value
        date_val = self.query_one("#date-input", Input).value
        rev_val = self.query_one("#rev-input", Input).value

        if date_shortcut == "custom":
            parts = date_val.split("-")
            if len(parts) != 3 or not all(p.isdigit() for p in parts) or len(date_val) != 10:
                self.update_status("[bold red]ERROR: Invalid date format. Use DD-MM-YYYY[/bold red]")
                return

        table = self.query_one("#results-table", DataTable)
        log_widget = self.query_one("#diagnostics-log", RichLog)

        self.call_from_thread(table.clear)
        self.call_from_thread(log_widget.clear)
        self.call_from_thread(setattr, table.styles, "height", "100%")
        self.call_from_thread(setattr, log_widget.styles, "height", "0%")

        self.update_status("Fetching data from GRID-INDIA Gateway...")
        success_count = 0
        failure_count = 0
        ip_blocked = False

        def on_row(row: dict) -> None:
            self.call_from_thread(
                table.add_row,
                row["qca"],
                row["plant"],
                row["type"],
                row["seller"],
                row["buyer"],
                f"{row['daily_total_mw']:,.2f}",
            )

        results = run_fetch_workflow(
            resolve_qca_list(qca_val),
            date_val,
            rev_val,
            on_status=self.update_status,
            on_log=self.write_log,
            on_row=on_row,
            stop_on_ip_block=True,
            show_tables=False,
        )

        for res in results:
            if res["status"] == "SUCCESS":
                success_count += 1
            else:
                failure_count += 1
                if res.get("error") == "IP_WHITELIST_BLOCKED":
                    ip_blocked = True

        if ip_blocked:
            self.call_from_thread(setattr, table.styles, "height", "0%")
            self.call_from_thread(setattr, log_widget.styles, "height", "100%")
            return

        self.update_status(f"Completed! Success: {success_count}, Failed: {failure_count}")
