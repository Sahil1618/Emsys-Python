
"""Export WBES schedule rows to a plant-wise Excel file (one sheet per plant)."""

import os
from collections import defaultdict
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# ── colour palette ─────────────────────────────────────────────────────────
_HDR_DARK   = "1F4E79"   # dark blue  – title bar
_HDR_MID    = "2E75B6"   # mid blue   – meta field labels
_BLOCK_HDR  = "BDD7EE"   # light blue – block label column
_AS_BG      = "E2EFDA"   # light green – AS schedule rows
_OA_BG      = "FCE4D6"   # light orange – OA_REMC rows
_TOTAL_BG   = "FFF2CC"   # yellow – daily total row
_WHITE      = "FFFFFF"

_thin  = Side(style="thin",   color="BFBFBF")
_thick = Side(style="medium", color="595959")
_BORDER = Border(left=_thin, right=_thin, top=_thin, bottom=_thin)
_BORDER_R = Border(left=_thin, right=_thick, top=_thin, bottom=_thin)


def _c(ws, row, col, value="", bold=False, fg="000000", bg=None,
       align="left", wrap=False, border=None, num_fmt=None, size=9):
    c = ws.cell(row=row, column=col, value=value)
    c.font      = Font(name="Arial", bold=bold, color=fg, size=size)
    c.alignment = Alignment(horizontal=align, vertical="center", wrap_text=wrap)
    if bg:
        c.fill = PatternFill("solid", start_color=bg)
    if border:
        c.border = border
    if num_fmt:
        c.number_format = num_fmt
    return c


def _row_bg(stype: str) -> str:
    if stype == "AS":
        return _AS_BG
    if stype.startswith("OA"):
        return _OA_BG
    return _WHITE


def _build_plant_sheet(ws, plant: str, plant_rows: list[dict],
                       qca_name: str, date_str: str, revision: str) -> None:
    """Write one plant's schedules onto a worksheet (transposed layout)."""

    n_scheds = len(plant_rows)

    # ── Row 1: title ─────────────────────────────────────────────────────
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=1 + n_scheds)
    title = f"{plant}  |  {qca_name}  |  {date_str}  |  Rev {revision}"
    c = ws.cell(row=1, column=1, value=title)
    c.font      = Font(name="Arial", bold=True, color=_WHITE, size=11)
    c.fill      = PatternFill("solid", start_color=_HDR_DARK)
    c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 22

    # ── Rows 2-6: meta header rows ────────────────────────────────────────
    META = [
        ("Schedule Type",  "type"),
        ("Seller",         "seller"),
        ("Buyer",          "buyer"),
        ("Approval No",    "approval"),
    ]
    for r_off, (label, key) in enumerate(META):
        row = 2 + r_off
        ws.row_dimensions[row].height = 16
        _c(ws, row, 1, label, bold=True, fg=_WHITE, bg=_HDR_MID,
           align="center", border=_BORDER)
        for col, srow in enumerate(plant_rows, start=2):
            bg = _row_bg(srow["type"])
            is_last = col == n_scheds + 1
            _c(ws, row, col, srow.get(key, ""), bg=bg,
               align="center", wrap=True,
               border=_BORDER_R if is_last else _BORDER)

    # ── Row 7: Daily Total ────────────────────────────────────────────────
    ws.row_dimensions[7].height = 22
    _c(ws, 7, 1, "Daily Total\n(MW)", bold=True, fg=_WHITE,
       bg=_HDR_DARK, align="center", wrap=True, border=_BORDER)
    for col, srow in enumerate(plant_rows, start=2):
        bg = _row_bg(srow["type"])
        is_last = col == n_scheds + 1
        _c(ws, 7, col, srow.get("daily_total_mw", 0.0),
           bold=True, bg=bg, align="right",
           border=_BORDER_R if is_last else _BORDER,
           num_fmt="#,##0.00")

    # ── Rows 8-103: B1..B96 ──────────────────────────────────────────────
    for b in range(96):
        row = 8 + b
        ws.row_dimensions[row].height = 13
        hh, mm   = divmod(b * 15, 60)
        ehh, emm = divmod((b + 1) * 15, 60)
        label    = f"B{b+1}\n{hh:02d}:{mm:02d}-{ehh:02d}:{emm:02d}"
        _c(ws, row, 1, label, bold=True, fg="000000", bg=_BLOCK_HDR,
           align="center", wrap=True, border=_BORDER)
        for col, srow in enumerate(plant_rows, start=2):
            val = srow.get("blocks", [])[b] if b < len(srow.get("blocks", [])) else 0.0
            bg = _row_bg(srow["type"])
            is_last = col == n_scheds + 1
            _c(ws, row, col, val if val != 0.0 else 0,
               bg=bg, align="right",
               border=_BORDER_R if is_last else _BORDER,
               num_fmt="#,##0.00")

    # ── Column widths & freeze ────────────────────────────────────────────
    ws.column_dimensions["A"].width = 16
    for col in range(2, n_scheds + 2):
        ws.column_dimensions[get_column_letter(col)].width = 14
    ws.freeze_panes = ws.cell(row=8, column=2)


def export_schedule_to_excel(
    rows: list[dict],
    qca_name: str,
    date_str: str,
    output_path: str | None = None,
) -> str:
    """
    Write block-wise schedule rows to Excel — one sheet per plant.

    Parameters
    ----------
    rows        : list of dicts from iter_schedule_rows()
    qca_name    : e.g. "EESPL_QCA_BKN2"
    date_str    : e.g. "08-06-2026"
    output_path : full path; auto-generated if None

    Returns
    -------
    str  path of the saved file
    """
    if not rows:
        raise ValueError("No schedule rows to export.")

    revision = rows[0].get("revision", "NA")

    if output_path is None:
        safe_date = date_str.replace("-", "")
        output_path = os.path.join(
            os.getcwd(),
            f"WBES_BlockWise_{qca_name}_{safe_date}_Rev{revision}.xlsx",
        )

    # Group rows by plant, preserving order
    plant_order = []
    by_plant: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        plant = row["plant"]
        if plant not in by_plant:
            plant_order.append(plant)
        by_plant[plant].append(row)

    wb = Workbook()
    wb.remove(wb.active)  # remove default blank sheet

    # ── One sheet per plant ───────────────────────────────────────────────
    for plant in plant_order:
        # Sheet name: Excel limits to 31 chars, no special chars
        sheet_name = plant[:31].replace("/", "-").replace("\\", "-").replace("*", "").replace("?", "").replace("[", "").replace("]", "").replace(":", "")
        ws = wb.create_sheet(title=sheet_name)
        _build_plant_sheet(ws, plant, by_plant[plant],
                           qca_name, date_str, revision)

    # ── Summary sheet (all plants, daily totals only) ─────────────────────
    ws_sum = wb.create_sheet(title="Summary")
    _build_summary_sheet(ws_sum, plant_order, by_plant,
                         qca_name, date_str, revision)

    wb.save(output_path)
    return output_path


def _build_summary_sheet(ws, plant_order: list, by_plant: dict,
                          qca_name: str, date_str: str, revision: str) -> None:
    """Summary sheet: one row per schedule, daily total + key info."""

    # Title
    ws.merge_cells("A1:F1")
    c = ws.cell(row=1, column=1,
                value=f"Summary  |  {qca_name}  |  {date_str}  |  Rev {revision}")
    c.font      = Font(name="Arial", bold=True, color=_WHITE, size=11)
    c.fill      = PatternFill("solid", start_color=_HDR_DARK)
    c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 22

    # Headers
    headers = ["Plant", "Schedule Type", "Seller", "Buyer", "Approval No", "Daily Total (MW)"]
    for col, h in enumerate(headers, 1):
        _c(ws, 2, col, h, bold=True, fg=_WHITE, bg=_HDR_MID,
           align="center", border=_BORDER)
    ws.row_dimensions[2].height = 18

    # Data
    data_row = 3
    for plant in plant_order:
        for srow in by_plant[plant]:
            bg = _row_bg(srow["type"])
            vals = [
                plant,
                srow.get("type", ""),
                srow.get("seller", ""),
                srow.get("buyer", ""),
                srow.get("approval", ""),
                srow.get("daily_total_mw", 0.0),
            ]
            for col, val in enumerate(vals, 1):
                nf = "#,##0.00" if col == 6 else None
                _c(ws, data_row, col, val, bg=bg, align="right" if col == 6 else "left",
                   border=_BORDER, num_fmt=nf)
            data_row += 1

    # Column widths
    widths = [20, 14, 18, 24, 32, 18]
    for col, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(col)].width = w
    ws.freeze_panes = "A3"