"""Export WBES schedule rows to a block-wise Excel file."""

import os
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side, numbers
from openpyxl.utils import get_column_letter

# ── colour palette ────────────────────────────────────────────────────────────
_HEADER_BG   = "1F4E79"   # dark blue  – title / meta headers
_AS_BG       = "E2EFDA"   # light green – AS rows
_OA_BG       = "FCE4D6"   # light orange – OA_REMC rows
_BLOCK_HDR   = "BDD7EE"   # light blue – block column headers
_META_HDR    = "2E75B6"   # mid blue – meta column headers
_TOTAL_BG    = "FFF2CC"   # yellow – Daily Total column
_WHITE       = "FFFFFF"

# ── block time labels B1…B96 ─────────────────────────────────────────────────
def _block_labels() -> list[str]:
    labels = []
    for b in range(96):
        hh, mm   = divmod(b * 15, 60)
        ehh, emm = divmod((b + 1) * 15, 60)
        labels.append(f"B{b+1}\n{hh:02d}:{mm:02d}-{ehh:02d}:{emm:02d}")
    return labels

_BLOCK_LABELS = _block_labels()

_thin  = Side(style="thin",   color="BFBFBF")
_thick = Side(style="medium", color="595959")
_BORDER      = Border(left=_thin, right=_thin, top=_thin, bottom=_thin)
_RIGHT_THICK = Border(left=_thin, right=_thick, top=_thin, bottom=_thin)

def _cell(ws, row, col, value="", bold=False, fg="000000", bg=None,
          align="left", wrap=False, border=None, num_fmt=None):
    c = ws.cell(row=row, column=col, value=value)
    c.font      = Font(name="Arial", bold=bold, color=fg, size=9)
    c.alignment = Alignment(horizontal=align, vertical="center",
                            wrap_text=wrap)
    if bg:
        c.fill = PatternFill("solid", start_color=bg)
    if border:
        c.border = border
    if num_fmt:
        c.number_format = num_fmt
    return c


def export_schedule_to_excel(
    rows: list[dict],
    qca_name: str,
    date_str: str,
    output_path: str | None = None,
) -> str:
    """
    Write block-wise schedule rows to an Excel file.

    Parameters
    ----------
    rows        : list of dicts from iter_schedule_rows()
    qca_name    : e.g. "EESPL_QCA_BKN"
    date_str    : e.g. "08-06-2026"
    output_path : full path including filename; auto-generated if None

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

    wb = Workbook()
    ws = wb.active
    ws.title = "Block-Wise (Wide)"
    ws.freeze_panes = "G7"          # freeze meta cols + header rows

    # ── Row 1 : workbook title ────────────────────────────────────────────────
    title_text = (
        f"WBES Block-Wise Schedule  |  {qca_name}  |  {date_str}  |  Rev {revision}"
    )
    n_cols = 6 + 96          # 6 meta + 96 block columns
    ws.merge_cells(start_row=1, start_column=1,
                   end_row=1, end_column=n_cols)
    c = ws.cell(row=1, column=1, value=title_text)
    c.font      = Font(name="Arial", bold=True, color=_WHITE, size=12)
    c.fill      = PatternFill("solid", start_color=_HEADER_BG)
    c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 22

    # ── Rows 2-5 : meta header rows (Plant / Type / Seller / Buyer / Approval) ─
    META_LABELS = [
        "Plant Acronym",
        "Schedule Type",
        "Seller",
        "Buyer",
        "Approval No",
        "Daily Total\n(MW)",
    ]
    for r_offset, label in enumerate(META_LABELS):
        row = 2 + r_offset
        ws.merge_cells(start_row=row, start_column=1,
                       end_row=row, end_column=6)
        c = ws.cell(row=row, column=1, value=label if r_offset == 0 else "")
        # We'll properly fill these in the transposed header below; skip for now

    # ── TRANSPOSE LAYOUT ──────────────────────────────────────────────────────
    # Rows 2-6  = header rows for each meta field
    # Row  7 onwards = one row per schedule entry, columns = blocks B1..B96

    # Row 2: Plant Acronym header + plant names
    # Row 3: Schedule Type header + types
    # Row 4: Seller header + sellers
    # Row 5: Buyer header + buyers
    # Row 6: Approval No header + approvals
    # Row 7: "Daily Total (MW)" label + totals per schedule  (thick border below)
    # Row 8+: B1..B96 labels in col 1, values from col 2 onward

    # Re-do from scratch with proper transposed design:
    ws.delete_rows(1, ws.max_row)   # clear what we tentatively wrote

    # ── Title row ─────────────────────────────────────────────────────────────
    ws.merge_cells(start_row=1, start_column=1,
                   end_row=1, end_column=1 + len(rows))
    c = ws.cell(row=1, column=1, value=title_text)
    c.font      = Font(name="Arial", bold=True, color=_WHITE, size=12)
    c.fill      = PatternFill("solid", start_color=_HEADER_BG)
    c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 22

    # ── Meta header rows 2-6 ──────────────────────────────────────────────────
    META_KEYS  = ["plant", "type", "seller", "buyer", "approval"]
    META_NAMES = ["Plant Acronym", "Schedule Type", "Seller", "Buyer", "Approval No"]

    for r_off, (key, name) in enumerate(zip(META_KEYS, META_NAMES)):
        row = 2 + r_off
        ws.row_dimensions[row].height = 18
        # Column A: field label
        _cell(ws, row, 1, name, bold=True, fg=_WHITE, bg=_HEADER_BG,
              align="center", border=_BORDER)
        # Columns 2..N: values per schedule
        for col, srow in enumerate(rows, start=2):
            val = srow.get(key, "")
            # Colour by schedule type
            stype = srow.get("type", "")
            bg = _AS_BG if stype == "AS" else (_OA_BG if stype.startswith("OA") else _WHITE)
            is_last = (col == len(rows) + 1)
            _cell(ws, row, col, val, fg="000000", bg=bg,
                  align="center", wrap=True,
                  border=_RIGHT_THICK if is_last else _BORDER)

    # ── Row 7: Daily Total ────────────────────────────────────────────────────
    row = 7
    ws.row_dimensions[row].height = 28
    _cell(ws, row, 1, "Daily Total\n(MW)", bold=True, fg=_WHITE,
          bg=_HEADER_BG, align="center", wrap=True, border=_BORDER)
    for col, srow in enumerate(rows, start=2):
        stype = srow.get("type", "")
        bg = _AS_BG if stype == "AS" else (_OA_BG if stype.startswith("OA") else _WHITE)
        is_last = (col == len(rows) + 1)
        _cell(ws, row, col, srow.get("daily_total_mw", 0.0),
              bold=True, bg=bg, align="right",
              border=_RIGHT_THICK if is_last else _BORDER,
              num_fmt="#,##0.00")

    # ── Rows 8-103: B1..B96 ───────────────────────────────────────────────────
    for b_idx in range(96):
        row = 8 + b_idx
        ws.row_dimensions[row].height = 14
        # Column A: block label
        hh, mm   = divmod(b_idx * 15, 60)
        ehh, emm = divmod((b_idx + 1) * 15, 60)
        label    = f"B{b_idx+1}\n{hh:02d}:{mm:02d}-{ehh:02d}:{emm:02d}"
        _cell(ws, row, 1, label, bold=True, fg=_WHITE, bg=_BLOCK_HDR,
              align="center", wrap=True, border=_BORDER)
        # Values per schedule
        for col, srow in enumerate(rows, start=2):
            val = srow.get("blocks", [])[b_idx] if b_idx < len(srow.get("blocks", [])) else 0.0
            stype = srow.get("type", "")
            bg = _AS_BG if stype == "AS" else (_OA_BG if stype.startswith("OA") else _WHITE)
            is_last = (col == len(rows) + 1)
            _cell(ws, row, col, val if val != 0.0 else 0,
                  bg=bg, align="right",
                  border=_RIGHT_THICK if is_last else _BORDER,
                  num_fmt="#,##0.00")

    # ── Column widths ─────────────────────────────────────────────────────────
    ws.column_dimensions["A"].width = 16       # block label col
    for col in range(2, len(rows) + 2):
        ws.column_dimensions[get_column_letter(col)].width = 11

    # ── Freeze: col A + header rows 1-7 ──────────────────────────────────────
    ws.freeze_panes = ws.cell(row=8, column=2)

    wb.save(output_path)
    return output_path