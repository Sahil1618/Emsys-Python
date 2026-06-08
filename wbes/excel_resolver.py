import os

import openpyxl

from wbes.config import EXCEL_PATH


def resolve_plants_from_excel(qca_name: str) -> list[str]:
    """Return active plant acronyms for the given QCA from the Excel master sheet."""
    if not os.path.exists(EXCEL_PATH):
        raise FileNotFoundError(f"Master Excel file '{EXCEL_PATH}' not found.")

    wb = openpyxl.load_workbook(EXCEL_PATH, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))

    header = rows[0]
    col_idx = -1
    for i, val in enumerate(header):
        if val == qca_name:
            col_idx = i
            break

    if col_idx == -1:
        raise ValueError(f"QCA name '{qca_name}' not found in Excel headers.")

    plants = []
    for r in range(1, 19):
        val = rows[r][col_idx]
        if val is not None and str(val).strip() != "" and str(val).lower() != "username":
            plants.append(str(val).strip())

    return plants
