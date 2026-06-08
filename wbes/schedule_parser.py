# """Parse WBES API JSON into flat rows for display and export."""


# def extract_schd_amounts(sched: dict) -> list[float]:
#     """Extract the 96-slot SchdAmount list from a schedule entry."""
#     full_sched_data = sched.get("FullScheduleData", {}) or {}
#     for val in full_sched_data.values():
#         if val is not None and isinstance(val, dict) and "SchdAmount" in val:
#             return val.get("SchdAmount", []) or []
#     return []


# def iter_schedule_rows(data: dict, qca_name: str | None = None):
#     """
#     Yield normalized schedule rows from a successful API response.

#     Each row: qca, plant, type, seller, buyer, approval, daily_total_mw, revision.
#     """
#     rb = data.get("ResponseBody", {}) or {}
#     revision = rb.get("FullSchdRevisionNo", "NA")

#     for group in rb.get("GroupWiseDataList", []) or []:
#         acronym = group.get("Acronym")
#         for sched in group.get("FullschdList", []) or []:
#             amounts = extract_schd_amounts(sched)
#             yield {
#                 "qca": qca_name,
#                 "plant": acronym,
#                 "type": sched.get("EnergyScheduleTypeName", "NA"),
#                 "seller": sched.get("SellerAcronym", "NA"),
#                 "buyer": sched.get("BuyerAcronym", "NA"),
#                 "approval": sched.get("ApprovalNo", "NA"),
#                 "daily_total_mw": sum(amounts) if amounts else 0.0,
#                 "revision": revision,
#             }


"""Parse WBES API JSON into flat rows for display and export."""


def extract_schd_amounts(sched: dict) -> list[float]:
    """Extract the 96-slot SchdAmount list from a schedule entry."""
    full_sched_data = sched.get("FullScheduleData", {}) or {}
    for val in full_sched_data.values():
        if val is not None and isinstance(val, dict) and "SchdAmount" in val:
            return val.get("SchdAmount", []) or []
    return []


def iter_schedule_rows(data: dict, qca_name: str | None = None):
    """
    Yield normalized schedule rows from a successful API response.

    Each row: qca, plant, type, seller, buyer, approval,
              daily_total_mw, blocks (list of 96 floats), revision.
    """
    rb = data.get("ResponseBody", {}) or {}
    revision = rb.get("FullSchdRevisionNo", "NA")

    for group in rb.get("GroupWiseDataList", []) or []:
        acronym = group.get("Acronym")
        for sched in group.get("FullschdList", []) or []:
            amounts = extract_schd_amounts(sched)
            # Pad to exactly 96 blocks if API returns fewer
            blocks = [float(x) if x is not None else 0.0 for x in amounts]
            blocks += [0.0] * (96 - len(blocks))

            yield {
                "qca": qca_name,
                "plant": acronym,
                "type": sched.get("EnergyScheduleTypeName", "NA"),
                "seller": sched.get("SellerAcronym", "NA"),
                "buyer": sched.get("BuyerAcronym", "NA"),
                "approval": sched.get("ApprovalNo", "NA"),
                "daily_total_mw": sum(blocks),
                "blocks": blocks,          # ← NEW: all 96 block values
                "revision": revision,
            }