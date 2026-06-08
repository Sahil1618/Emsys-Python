# GRID-INDIA / POSOCO WBES Energy Fetch Engine

Python utility to download **WBES (Web-Based Energy Scheduling)** daily energy schedules from the GRID-INDIA / POSOCO gateway for Qualified Coordinating Agencies (QCAs). It resolves plant lists from an Excel master sheet, authenticates per QCA, saves structured JSON on disk, and presents results in the terminal.

## What it does

1. Loads QCA credentials from `.env` (or bootstraps them from the Excel master sheet).
2. Reads plant acronyms for the selected QCA from `PLANT NAMES ALL QCA (4).xlsx`.
3. Calls `GetUtilityExternalSharedData` on the POSOCO gateway.
4. Saves the full API response as JSON, indexed in a manifest.
5. Shows a summary table (plant, schedule type, seller, buyer, daily MW total).
6. Optional **watch mode** polls the server every 15 minutes, saves snapshots, and logs what changed.

## How data arrives from the server

This is a **pull API**, not a push feed. Nothing streams to your machine automatically.

```
Your PC  --POST-->  gateway.grid-india.in/POSOCO/.../GetUtilityExternalSharedData
         <--JSON--  Full day schedule for Date + plant list + revision
```

| Request field | Meaning |
|---------------|---------|
| `Date` | Scheduling day (`DD-MM-YYYY`) |
| `SchdRevNo` | `-1` = **latest revision** (use this for live polling) |
| `UserName` | QCA integration user from `.env` |
| `UtilAcronymList` | Plant acronyms from Excel |

| Response area | Meaning |
|---------------|---------|
| `ResponseStatus.Code` | `WBES200` = success |
| `ResponseBody.FullSchdRevisionNo` | Integer revision; **increments when the grid publishes a new schedule version** |
| `ResponseBody.GroupWiseDataList[]` | One entry per plant |
| `FullschdList[]` | Schedule rows (type, seller, buyer, approval) |
| `FullScheduleData` → `SchdAmount` | **96 numbers** = MW for each **15-minute block** (00:00–23:45) |

Power plants update WBES on the grid side; your job is to **poll** often enough and compare responses. The 96 slots are the day’s curve in one response; **revisions** and **slot value changes** are how you detect “new information” between polls.

### Inspect saved data (no API call)

After at least one successful fetch:

```bash
python wbes_fetcher.py --inspect
```

Or open any file under `wbes_schedules/<QCA>/<date>/` in a text editor — files are the raw server JSON.

## Prerequisites

| Requirement | Details |
|-------------|---------|
| Python | 3.10+ recommended |
| Network | Outbound HTTPS to `gateway.grid-india.in` |
| IP whitelist | Your public IP must be registered with GRID-INDIA/POSOCO for the API key |
| Excel master | `PLANT NAMES ALL QCA (4).xlsx` in the project root (plant list + optional credential bootstrap) |
| Credentials | `.env` with per-QCA `USERNAME`, `PASSWORD`, and `API_KEY` |

Reference API collection: `WBES-INTEGRATION-GENERIC.json` (Postman).

## Installation

```bash
cd "c:\Users\Sudhanshu Desktop\Downloads\new project"
pip install -r requirements.txt
```

## Configuration (`.env`)

If `.env` is missing or empty and the Excel file is present, the tool auto-generates `.env` from rows 19–21 of the master sheet.

Example structure:

```env
BASE_URL=https://gateway.grid-india.in/POSOCO
DEFAULT_QCA=EESPL_QCA_BKN

EESPL_QCA_BKN_USERNAME=your_user
EESPL_QCA_BKN_PASSWORD=your_password
EESPL_QCA_BKN_API_KEY=your_api_key
# ... repeat for EESPL_QCA_BHDL, EMSYS_QCA_BHDL_2, EESPL_QCA_BKN2
```

**Do not commit `.env` to version control.** It contains live credentials.

### Supported QCAs

| QCA key | Region |
|---------|--------|
| `EESPL_QCA_BKN` | Bikaner |
| `EESPL_QCA_BHDL` | Bhadla |
| `EMSYS_QCA_BHDL_2` | Bhadla 2 |
| `EESPL_QCA_BKN2` | Bikaner 2 |

## How to run

### 1. Interactive console menu (default)

```bash
python wbes_fetcher.py
```

Arrow-key prompts for QCA, date (`DD-MM-YYYY`), and revision (`-1` = latest).

### 2. Full-screen TUI (Textual)

```bash
python wbes_fetcher.py --tui
```

Press **F** to fetch or **Q** to quit.

### 3. Non-interactive CLI (automation / scripts)

```bash
# Single QCA, today's date, latest revision
python wbes_fetcher.py -q EESPL_QCA_BKN -d today -r -1 -n

# All four QCAs for a specific date
python wbes_fetcher.py -q ALL -d 22-05-2026 -r -1 -n

# Relative dates
python wbes_fetcher.py -q EESPL_QCA_BHDL -d tomorrow -n
python wbes_fetcher.py -q EESPL_QCA_BKN2 -d yesterday -n
```

| Flag | Description |
|------|-------------|
| `-q`, `--qca` | QCA name or `ALL` |
| `-d`, `--date` | `DD-MM-YYYY`, or `today` / `tomorrow` / `yesterday` |
| `-r`, `--rev` | Schedule revision integer (`-1` = latest) |
| `-n`, `--non-interactive` | Skip menus (auto-enabled if `-q`, `-d`, or `-r` is passed) |
| `-t`, `--tui` | Launch Textual UI |
| `-w`, `--watch` | Poll continuously until Ctrl+C |
| `--interval-minutes N` | Minutes between polls (default `15`) |
| `--no-align` | Poll every N minutes from start time (not aligned to :00/:15/:30/:45) |
| `--cycles N` | Exit watch mode after N polls |
| `--inspect` | Print structure of last saved JSON |

### 4. Watch mode (15-minute refresh)

Keeps running, fetches **latest revision** (`-1`) on a schedule, saves timestamped snapshots, and appends a change log when MW values or revision change.

```bash
# All QCAs, today, aligned to clock quarters (:00 :15 :30 :45)
python wbes_fetcher.py -w -q ALL -d today -n

# Single QCA, test 3 cycles only
python wbes_fetcher.py -w -q EESPL_QCA_BKN -d today --cycles 3 -n

# Poll every 15 minutes from whenever you started (no clock alignment)
python wbes_fetcher.py -w -q EESPL_QCA_BHDL -d today --no-align -n
```

**Production tip:** Run watch mode in a persistent session (Windows Service, `nssm`, Task Scheduler starting at login, or `pm2`/systemd on Linux) so it survives reboots.

## Output layout (filesystem)

Fetched data is organized under `wbes_schedules/`:

```
wbes_schedules/
├── manifest.json                          # Index of every saved fetch
├── EESPL_QCA_BKN/
│   └── 22-05-2026/
│       ├── schedule_rev_3.json            # Latest revision (overwritten when rev changes)
│       ├── snapshots/
│       │   └── poll_20260522_143005_rev_3.json   # One file per watch poll
│       └── changes.jsonl                  # Line-by-line diff history per poll
├── EESPL_QCA_BHDL/
│   └── ...
├── watch_state.json                       # Last snapshot pointer per QCA (watch mode)
└── ...

wbes_latest_schedule.json                  # Map of latest successful fetch per QCA
wbes_fetcher.log                           # Error / diagnostic log
```

### `manifest.json`

Each successful save appends an entry:

```json
{
  "entries": [
    {
      "qca": "EESPL_QCA_BKN",
      "date": "22-05-2026",
      "revision": 3,
      "path": "wbes_schedules/EESPL_QCA_BKN/22-05-2026/schedule_rev_3.json",
      "saved_at": "2026-05-22T14:30:00"
    }
  ]
}
```

### `wbes_latest_schedule.json`

When fetching multiple QCAs, each QCA keeps its own latest payload under `by_qca` (previously the last QCA overwrote the entire file).

### JSON response shape (API)

Saved files mirror the POSOCO response:

- `ResponseStatus` — `Code` (success: `WBES200`), `Message`
- `ResponseBody.GroupWiseDataList[]` — per plant acronym
  - `FullschdList[]` — schedules with seller/buyer, type, approval
  - `FullScheduleData` — 96 × 15-minute `SchdAmount` blocks

## Project structure

```
wbes_fetcher.py              # CLI entry point
wbes/
  config.py                  # Paths, QCA list, .env bootstrap
  excel_resolver.py          # Plant list from Excel
  api_client.py              # HTTP fetch + retries + diagnostics
  schedule_parser.py         # Normalize API JSON to display rows
  storage.py                 # Save JSON, manifest, latest pointer
  display.py                 # Rich tables and error panels
  runner.py                  # Shared fetch workflow
  interactive_menu.py        # Questionary menu
  tui_app.py                 # Textual UI
  logging_util.py            # File logging helper
requirements.txt
WBES-INTEGRATION-GENERIC.json
PLANT NAMES ALL QCA (4).xlsx   # Required at runtime (not in repo)
.env                           # Local secrets (not in repo)
```

## Troubleshooting

| Symptom | Likely cause | Action |
|---------|--------------|--------|
| `IP_WHITELIST_BLOCKED` | IP not whitelisted | Share your public IP (shown in diagnostics) with GRID-INDIA |
| `CREDENTIALS_REJECTED` | Wrong username/password | Verify `.env` for that QCA |
| `CONFIG_ERROR` | Missing env vars | Run once with Excel present to bootstrap, or edit `.env` |
| `API_LEVEL_ERROR` / non-`WBES200` | Invalid date, revision, or plant list | Check date format `DD-MM-YYYY` and revision |
| Excel parsing error | Missing/wrong sheet or QCA column | Ensure `PLANT NAMES ALL QCA (4).xlsx` matches expected layout |
| TUI fails to start | Textual not installed | `pip install textual` or use default menu without `--tui` |

## Security notes

- Store credentials only in `.env`.
- Add `.env` and `wbes_schedules/` to `.gitignore` if using Git.
- The Postman sample file uses placeholder credentials; replace with your issued values.

## License

Internal utility — confirm usage terms with GRID-INDIA / POSOCO before production deployment.
