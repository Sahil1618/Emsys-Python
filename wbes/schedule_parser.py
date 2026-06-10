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

    Only deduplicates at the GROUP level (same Acronym appearing twice
    in GroupWiseDataList). Does NOT deduplicate schedule entries within
    a group — the same buyer can have multiple valid OA_REMC entries.
    """
    rb = data.get("ResponseBody", {}) or {}
    revision = rb.get("FullSchdRevisionNo", "NA")

    seen_plants: set[str] = set()

    for group in rb.get("GroupWiseDataList", []) or []:
        acronym = group.get("Acronym")

        # Drop entire duplicate groups (same Acronym) — their blocks are
        # always identical so keeping the first is sufficient.
        if acronym in seen_plants:
            continue
        seen_plants.add(acronym)

        for sched in group.get("FullschdList", []) or []:
            amounts = extract_schd_amounts(sched)
            blocks  = [float(x) if x is not None else 0.0 for x in amounts]
            blocks += [0.0] * (96 - len(blocks))

            yield {
                "qca":            qca_name,
                "plant":          acronym,
                "type":           sched.get("EnergyScheduleTypeName", "NA"),
                "seller":         sched.get("SellerAcronym", "NA"),
                "buyer":          sched.get("BuyerAcronym", "NA"),
                "approval":       sched.get("ApprovalNo", "NA"),
                "daily_total_mw": sum(blocks),
                "blocks":         blocks,
                "revision":       revision,
            }