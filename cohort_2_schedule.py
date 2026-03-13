"""
Cohort 2 scheduling: one anchor session (most people) + two other sessions (different days).
Each student attends 2 sessions total; company holds 3 sessions; no two on the same day.
Uses cohort_2_candidates.csv and cohort_2_form_results.csv (availability from form).
"""
from pathlib import Path

import pandas as pd

from load_form_data import parse_days, parse_name_to_last_first, WEEKDAYS, APPLICANT_COL

DATA_DIR = Path(__file__).resolve().parent / "data"
COHORT_2_CANDIDATES = DATA_DIR / "cohort_2_candidates.csv"
COHORT_2_FORM_RESULTS = DATA_DIR / "cohort_2_form_results.csv"

# Cohort 2 form has 6 availability columns (multi-line headers)
COHORT2_SLOT_COLS = [
    "Availability & Access\nWhich times generally work best for you? (Select all that apply) [9am-10am (PT) / 12pm-1pm (ET)]",
    "Availability & Access\nWhich times generally work best for you? (Select all that apply) [10am-11am (PT) / 1pm-2pm (ET)]",
    "Availability & Access\nWhich times generally work best for you? (Select all that apply) [11am-noon (PT) / 2pm-3pm (ET)]",
    "Availability & Access\nWhich times generally work best for you? (Select all that apply) [noon-1pm (PT) / 3pm-4pm (ET)]",
    "Availability & Access\nWhich times generally work best for you? (Select all that apply) [1pm-2pm (PT) / 4pm-5pm (ET)]",
    "Availability & Access\nWhich times generally work best for you? (Select all that apply) [Flexible]",
]
COHORT2_FLEXIBLE_COL = COHORT2_SLOT_COLS[-1]
COHORT2_SLOT_LABELS = {
    COHORT2_SLOT_COLS[0]: "9am–10am PT / 12pm–1pm ET",
    COHORT2_SLOT_COLS[1]: "10am–11am PT / 1pm–2pm ET",
    COHORT2_SLOT_COLS[2]: "11am–noon PT / 2pm–3pm ET",
    COHORT2_SLOT_COLS[3]: "noon–1pm PT / 3pm–4pm ET",
    COHORT2_SLOT_COLS[4]: "1pm–2pm PT / 4pm–5pm ET",
    COHORT2_SLOT_COLS[5]: "Flexible",
}


def _available_for_slot_cohort2(
    row: pd.Series,
    slot_col: str,
    day: str,
    treat_flexible_as_any_slot: bool = True,
) -> bool:
    """True if this row is available for (slot_col, day). Uses parse_days on the cell."""
    if slot_col not in row.index:
        return False
    slot_days = parse_days(row[slot_col])
    if treat_flexible_as_any_slot and COHORT2_FLEXIBLE_COL in row.index and slot_col != COHORT2_FLEXIBLE_COL:
        slot_days = slot_days | parse_days(row[COHORT2_FLEXIBLE_COL])
    return day in slot_days


def load_cohort_2_merged() -> pd.DataFrame:
    """
    Load cohort_2_candidates and cohort_2_form_results; merge by normalized name.
    When a column exists in both, form_results is prioritized (incoming change from form).
    """
    cand = pd.read_csv(COHORT_2_CANDIDATES, encoding="utf-8")
    form = pd.read_csv(COHORT_2_FORM_RESULTS, encoding="utf-8")
    cand["_name"] = cand["APPLICANT"].map(
        lambda x: parse_name_to_last_first(str(x).strip()) if pd.notna(x) else ""
    )
    name_col = "Name (First, Last)" if "Name (First, Last)" in form.columns else "APPLICANT"
    form["_name"] = form[name_col].map(
        lambda x: parse_name_to_last_first(str(x).strip()) if pd.notna(x) else ""
    )
    # Merge by name; form (left) keeps its column names, cand gets _cand suffix on conflicts.
    merged = form.merge(cand, on="_name", how="inner", suffixes=("", "_cand"))
    # Prioritize form_results: drop cand duplicate columns so only form's value remains.
    for col in list(merged.columns):
        if col.endswith("_cand"):
            base = col[:-5]  # len("_cand") == 5
            if base in merged.columns:
                merged = merged.drop(columns=[col])
    return merged


def best_availability_counts(cohort_df: pd.DataFrame) -> list[tuple[str, str, int]]:
    """Return list of (day, slot_label, count) sorted by count descending."""
    slot_cols = [c for c in COHORT2_SLOT_COLS if c in cohort_df.columns]
    out = []
    for slot_col in slot_cols:
        label = COHORT2_SLOT_LABELS.get(slot_col, slot_col)
        for day in WEEKDAYS:
            count = sum(
                1 for _, row in cohort_df.iterrows()
                if _available_for_slot_cohort2(row, slot_col, day, True)
            )
            if count > 0:
                out.append((day, label, count))
    out.sort(key=lambda x: -x[2])
    return out


def find_anchor_and_two_sessions(
    cohort_df: pd.DataFrame,
    *,
    treat_flexible_as_any_slot: bool = True,
) -> dict | None:
    """
    Pick anchor = (day, slot) with max availability; pick 2 other (day, slot) on other days.
    Each person attends anchor + one of the other two (balanced). Exclude anyone who can only do 1 session.
    Returns dict with anchor_day, anchor_slot_col, anchor_label, session_2_*, session_3_*,
    anchor_df, session_2_df, session_3_df, person_to_second_session, cohort_df, excluded_df.
    """
    if cohort_df.empty:
        return None
    # Count available per (day, slot)
    slot_cols = [c for c in COHORT2_SLOT_COLS if c in cohort_df.columns]
    if not slot_cols:
        return None
    best_anchor = None
    best_count = 0
    for slot_col in slot_cols:
        for day in WEEKDAYS:
            count = sum(
                1 for _, row in cohort_df.iterrows()
                if _available_for_slot_cohort2(row, slot_col, day, treat_flexible_as_any_slot)
            )
            if count > best_count:
                best_count = count
                best_anchor = (day, slot_col)
    if best_anchor is None:
        return None
    anchor_day, anchor_slot_col = best_anchor
    anchor_label = f"{anchor_day} at {COHORT2_SLOT_LABELS.get(anchor_slot_col, anchor_slot_col)}"

    # People who can attend the anchor
    anchor_mask = cohort_df.apply(
        lambda row: _available_for_slot_cohort2(row, anchor_slot_col, anchor_day, treat_flexible_as_any_slot),
        axis=1,
    )
    anchor_df = cohort_df.loc[anchor_mask].copy()
    if len(anchor_df) == 0:
        return None

    # Other (day, slot) options: day != anchor_day
    other_options: list[tuple[str, str, int]] = []
    for slot_col in slot_cols:
        for day in WEEKDAYS:
            if day == anchor_day:
                continue
            count = sum(
                1 for _, row in anchor_df.iterrows()
                if _available_for_slot_cohort2(row, slot_col, day, treat_flexible_as_any_slot)
            )
            if count > 0:
                other_options.append((day, slot_col, count))
    other_options.sort(key=lambda x: -x[2])

    # Pick session_2 and session_3: two different days (best coverage)
    session_2 = None
    session_3 = None
    seen_days = set()
    for day, slot_col, _ in other_options:
        if day in seen_days:
            continue
        if session_2 is None:
            session_2 = (day, slot_col)
            seen_days.add(day)
        elif session_3 is None:
            session_3 = (day, slot_col)
            seen_days.add(day)
            break
    if session_2 is None or session_3 is None:
        return None

    day_2, slot_2 = session_2
    day_3, slot_3 = session_3
    label_2 = f"{day_2} at {COHORT2_SLOT_LABELS.get(slot_2, slot_2)}"
    label_3 = f"{day_3} at {COHORT2_SLOT_LABELS.get(slot_3, slot_3)}"

    # For each anchor attendee: can they do session_2 and/or session_3?
    person_to_options: dict[int, list[str]] = {}  # idx -> ["day_2", "day_3"] or ["day_2"] or ["day_3"]
    excluded = []
    for idx in anchor_df.index:
        row = anchor_df.loc[idx]
        opts = []
        if _available_for_slot_cohort2(row, slot_2, day_2, treat_flexible_as_any_slot):
            opts.append("session_2")
        if _available_for_slot_cohort2(row, slot_3, day_3, treat_flexible_as_any_slot):
            opts.append("session_3")
        if len(opts) < 1:
            excluded.append(idx)
        else:
            person_to_options[idx] = opts

    cohort_valid = anchor_df.drop(index=excluded, errors="ignore")
    if len(cohort_valid) == 0:
        return None

    # Assign each to anchor + session_2 or session_3 (balance)
    count_2 = 0
    count_3 = 0
    person_to_second: dict[int, str] = {}  # idx -> "session_2" | "session_3"
    for idx in cohort_valid.index:
        opts = person_to_options[idx]
        if len(opts) == 1:
            choice = opts[0]
        else:
            choice = "session_2" if count_2 <= count_3 else "session_3"
        person_to_second[idx] = choice
        if choice == "session_2":
            count_2 += 1
        else:
            count_3 += 1

    idx_2 = [i for i, c in person_to_second.items() if c == "session_2"]
    idx_3 = [i for i, c in person_to_second.items() if c == "session_3"]
    session_2_df = cohort_valid.loc[idx_2]
    session_3_df = cohort_valid.loc[idx_3]
    excluded_df = anchor_df.loc[excluded] if excluded else pd.DataFrame()

    return {
        "anchor_day": anchor_day,
        "anchor_slot_col": anchor_slot_col,
        "anchor_label": anchor_label,
        "session_2_day": day_2,
        "session_2_slot_col": slot_2,
        "session_2_label": label_2,
        "session_3_day": day_3,
        "session_3_slot_col": slot_3,
        "session_3_label": label_3,
        "anchor_df": anchor_df,
        "session_2_df": session_2_df,
        "session_3_df": session_3_df,
        "person_to_second_session": person_to_second,
        "cohort_df": cohort_valid,
        "excluded_df": excluded_df,
        "not_anchor_df": cohort_df.loc[~anchor_mask],
    }


def _name_offer(row: pd.Series) -> str:
    """Format name and optional OFFER for display."""
    name = row.get(APPLICANT_COL, row.get("Name (First, Last)", row.get("_name", "?")))
    if pd.isna(name):
        name = row.get("_name", "?")
    email = row.get("EMAIL", row.get("Email Address", ""))
    offer = row.get("OFFER", "")
    s = str(name).strip()
    if email and pd.notna(email):
        s += f" — {email}"
    if offer and pd.notna(offer):
        s += f" ({offer})"
    return s


def format_two_sessions_report(result: dict | None, cohort_name: str = "Cohort 2") -> str:
    """Human-readable report for the 3-session schedule (anchor + 2 others)."""
    if result is None:
        return f"{cohort_name}: No valid schedule found.\n"
    # Anchor attendee list = only people in the schedule (cohort_df), so anchor count = Session 2 + Session 3
    scheduled_anchor_df = result["cohort_df"]
    lines = [
        f"Two sessions per person — {cohort_name}",
        "=" * 50,
        "",
        "Company holds 3 sessions (no two on the same day). Each student attends the anchor + one other session.",
        "",
        f"Anchor session (everyone in cohort): {result['anchor_label']}",
        f"  Attendees: {len(scheduled_anchor_df)} people",
        "",
    ]
    for _, row in scheduled_anchor_df.iterrows():
        lines.append(f"  - {_name_offer(row)}")
    lines.append("")
    lines.append(f"Session 2: {result['session_2_label']}")
    lines.append(f"  Attendees: {len(result['session_2_df'])} people")
    lines.append("")
    for _, row in result["session_2_df"].iterrows():
        lines.append(f"  - {_name_offer(row)}")
    lines.append("")
    lines.append(f"Session 3: {result['session_3_label']}")
    lines.append(f"  Attendees: {len(result['session_3_df'])} people")
    lines.append("")
    for _, row in result["session_3_df"].iterrows():
        lines.append(f"  - {_name_offer(row)}")
    lines.append("")
    lines.append("Per-person schedule (anchor + one other):")
    lines.append("-" * 40)
    for idx in result.get("person_to_second_session", {}):
        row = result["cohort_df"].loc[idx]
        sec = result["person_to_second_session"][idx]
        other_label = result["session_2_label"] if sec == "session_2" else result["session_3_label"]
        lines.append(f"  {_name_offer(row)}:  {result['anchor_label']}, {other_label}")
    if len(result.get("excluded_df", pd.DataFrame())) > 0:
        lines.append("")
        lines.append("Excluded (can only attend one session):")
        for _, row in result["excluded_df"].iterrows():
            lines.append(f"  - {_name_offer(row)}")
    if len(result.get("not_anchor_df", pd.DataFrame())) > 0:
        lines.append("")
        lines.append("Not available for anchor session:")
        for _, row in result["not_anchor_df"].iterrows():
            lines.append(f"  - {_name_offer(row)}")
    return "\n".join(lines)


def two_sessions_cohort2_to_dataframe(result: dict | None) -> pd.DataFrame:
    """One row per person: Name, Email, Offer, Meeting 1 (anchor), Meeting 2."""
    if result is None or not result.get("person_to_second_session"):
        return pd.DataFrame(columns=["Name", "Email", "Offer", "Meeting 1", "Meeting 2"])
    rows = []
    for idx in result["person_to_second_session"]:
        row = result["cohort_df"].loc[idx]
        sec = result["person_to_second_session"][idx]
        other_label = result["session_2_label"] if sec == "session_2" else result["session_3_label"]
        rows.append({
            "Name": row.get(APPLICANT_COL, row.get("Name (First, Last)", row.get("_name", "?"))),
            "Email": row.get("EMAIL", row.get("Email Address", "")),
            "Offer": row.get("OFFER", "") if "OFFER" in row.index else "",
            "Meeting 1": result["anchor_label"],
            "Meeting 2": other_label,
        })
    return pd.DataFrame(rows)


def two_sessions_cohort2_by_meeting_to_dataframe(result: dict | None) -> pd.DataFrame:
    """Long format: Meeting, Day & Time, Name, Email, Offer. Anchor list = scheduled cohort only."""
    if result is None:
        return pd.DataFrame(columns=["Meeting", "Day & Time", "Name", "Email", "Offer"])
    rows = []
    for _, row in result["cohort_df"].iterrows():
        rows.append({
            "Meeting": "Anchor (everyone)",
            "Day & Time": result["anchor_label"],
            "Name": row.get(APPLICANT_COL, row.get("Name (First, Last)", "?")),
            "Email": row.get("EMAIL", row.get("Email Address", "")),
            "Offer": row.get("OFFER", "") if "OFFER" in row.index else "",
        })
    for _, row in result["session_2_df"].iterrows():
        rows.append({
            "Meeting": "Session 2",
            "Day & Time": result["session_2_label"],
            "Name": row.get(APPLICANT_COL, row.get("Name (First, Last)", "?")),
            "Email": row.get("EMAIL", row.get("Email Address", "")),
            "Offer": row.get("OFFER", "") if "OFFER" in row.index else "",
        })
    for _, row in result["session_3_df"].iterrows():
        rows.append({
            "Meeting": "Session 3",
            "Day & Time": result["session_3_label"],
            "Name": row.get(APPLICANT_COL, row.get("Name (First, Last)", "?")),
            "Email": row.get("EMAIL", row.get("Email Address", "")),
            "Offer": row.get("OFFER", "") if "OFFER" in row.index else "",
        })
    return pd.DataFrame(rows)
