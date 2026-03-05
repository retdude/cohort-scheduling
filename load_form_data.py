"""
Load form results and candidates CSVs into pandas DataFrames; merge by name for scheduling.

- Names are normalized to "Last, First"; asterisks (accessibility markers) are stripped.
- Merge: form_results is the base; when a column exists in both, form_results wins.
- Two cohort DataFrames: cohort A (March 16–27 or Either), cohort B (March 30–April 10 or Either).

Columns KEPT (needed for finding a common day/time):
  - name, APPLICANT, EMAIL Address, EMAIL (candidates), COHORT, Location (City, State)
  - Times_9am-11am_PT, Times_11am-1pm_PT, Times_1pm-3pm_PT, Times_Flexible
  - Additional details (free-text constraints)
  - FORM FILLED, OFFER, NOTES (from candidates)

Columns EXCLUDED (not needed for scheduling):
  - Timestamp
  - Access accommodations, format preference, collaboration interest, future contact, allyship
"""
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent / "data"
FORM_CSV = DATA_DIR / "form_results.csv"
CANDIDATES_CSV = DATA_DIR / "candidates.csv"

# Name column may be "APPLICANT" or "Name (First, Last)"
APPLICANT_COL = "APPLICANT"
NAME_FIRST_LAST_COL = "Name (First, Last)"

# Form COHORT values used for cohort splitting
COHORT_MARCH_16_27 = "March 16 - 27 2026"
COHORT_MARCH_30_APRIL_10 = "March 30 - April 10 2026"
COHORT_EITHER = "Either"

# Columns to exclude from merged/cohort DFs (not needed for scheduling)
COLUMNS_TO_EXCLUDE = [
    "Timestamp",
    "Do you need any access accommodations for virtual focus group participation? (Select all that apply)",
    "What format do you prefer for participation? (Click all that work for you)",
    "Would you be interested in ongoing collaboration, advisory, or mentorship opportunities?",
    "Whether or not you are selected for this immediate position, are you comfortable being contacted for future opportunities or co-creation sessions?",
    "Allyship refers to active support for disability inclusion, by both disabled and non-disabled individuals. How would you identify yourself?",
]

# Short name for the long "additional details" column (keep for scheduling constraints)
ADDITIONAL_DETAILS_COL = "Are there any additional details about the times you are available that you feel are important to communicate, such as being available for part of the times listed but not fully? If not, skip to the next question."

# Time-slot columns used to find common availability (order preserved for reporting)
TIME_SLOT_COLUMNS = [
    "Times_9am-11am_PT",
    "Times_11am-1pm_PT",
    "Times_1pm-3pm_PT",
    "Times_Flexible",
]
WEEKDAYS = {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday"}

SLOT_LABELS = {
    "Times_9am-11am_PT": "9am–11am PT / 12pm–2pm ET",
    "Times_11am-1pm_PT": "11am–1pm PT / 2pm–4pm ET",
    "Times_1pm-3pm_PT": "1pm–3pm PT / 4pm–6pm ET",
    "Times_Flexible": "Flexible",
}

OFFER_FIRST_CHOICE = "1st choice"

# Three-meeting model: one full-cohort day + two split days
ANCHOR_DAY = "Friday"
ANCHOR_SLOT_COL = "Times_9am-11am_PT"


def parse_name_to_last_first(raw: str) -> str:
    """
    Parse a name string to "Last, First" format for linking.
    - Strips leading/trailing whitespace and asterisks (accessibility markers).
    - If input contains ", ", treat as "First, Last" -> "Last, First".
    - If input is "First Last" (no comma), treat last word as last name -> "Last, First".
    """
    if pd.isna(raw) or not isinstance(raw, str):
        return raw
    s = raw.strip().strip("*").strip()
    if not s:
        return raw
    if ", " in s:
        parts = [p.strip() for p in s.split(", ", 1)]
        if len(parts) == 2:
            first, last = parts[0], parts[1]
            return f"{last}, {first}"
    parts = s.split()
    if len(parts) >= 2:
        last = parts[-1]
        first = " ".join(parts[:-1])
        return f"{last}, {first}"
    return s


def _name_column(df: pd.DataFrame):
    """Return the applicant/name column in df."""
    if APPLICANT_COL in df.columns:
        return APPLICANT_COL
    if NAME_FIRST_LAST_COL in df.columns:
        return NAME_FIRST_LAST_COL
    raise KeyError("No APPLICANT or 'Name (First, Last)' column found.")


def load_form_results() -> pd.DataFrame:
    """Load form_results.csv and add normalized name column."""
    df = pd.read_csv(FORM_CSV, encoding="utf-8")
    name_col = _name_column(df)
    df["name"] = df[name_col].map(parse_name_to_last_first)
    return df


def load_candidates() -> pd.DataFrame:
    """Load candidates.csv and add normalized name column for joining."""
    df = pd.read_csv(CANDIDATES_CSV, encoding="utf-8")
    df["name"] = df["APPLICANT"].map(parse_name_to_last_first)
    return df


def load_merged(
    *,
    prioritize_form: bool = True,
    drop_excluded_columns: bool = True,
) -> pd.DataFrame:
    """
    Load form_results and candidates, merge on name (form_results as base).
    When both have a column with the same name, form_results wins if prioritize_form is True.
    Drops columns not needed for scheduling if drop_excluded_columns is True.
    """
    form = load_form_results()
    candidates = load_candidates()

    # Bring in only candidate-only columns (prioritize form for COHORT, email, etc.)
    candidate_only = [c for c in candidates.columns if c not in form.columns and c != "name"]
    merge_cols = ["name"] + candidate_only

    merged = form.merge(candidates[merge_cols], on="name", how="left")

    if drop_excluded_columns:
        to_drop = [c for c in COLUMNS_TO_EXCLUDE if c in merged.columns]
        merged = merged.drop(columns=to_drop, errors="ignore")

    return merged


def get_cohort_a(merged: pd.DataFrame | None = None) -> pd.DataFrame:
    """
    People in March 16 - 27 2026 OR Either (with only scheduling-relevant columns).
    """
    if merged is None:
        merged = load_merged()
    out = merged[
        merged["COHORT"].isin([COHORT_MARCH_16_27, COHORT_EITHER])
    ].copy()
    return out


def get_cohort_b(merged: pd.DataFrame | None = None) -> pd.DataFrame:
    """
    People in March 30 - April 10 2026 OR Either (with only scheduling-relevant columns).
    """
    if merged is None:
        merged = load_merged()
    out = merged[
        merged["COHORT"].isin([COHORT_MARCH_30_APRIL_10, COHORT_EITHER])
    ].copy()
    return out


def parse_days(cell: str) -> set[str]:
    """
    Parse a time-slot cell into a set of weekday names.
    Ignores empty, N/A, No, and non-day tokens; normalizes to title case.
    """
    if pd.isna(cell) or not isinstance(cell, str):
        return set()
    tokens = [s.strip() for s in cell.split(",") if s.strip()]
    days = set()
    for t in tokens:
        normalized = t.strip().title()
        if normalized in WEEKDAYS:
            days.add(normalized)
    return days


def find_common_slots(
    cohort_df: pd.DataFrame,
    *,
    treat_flexible_as_any_slot: bool = True,
) -> dict[str, list[str]]:
    """
    Find (day, time_slot) combinations where everybody in the cohort is available.

    For each time slot, returns the list of days that appear in every person's
    response for that slot. If treat_flexible_as_any_slot is True, a person
    is considered available for a given slot on day D if D is in that slot's
    column OR in Times_Flexible.

    Returns:
        Dict mapping each time-slot column name to a sorted list of common days
        (empty list if no day works for everyone).
    """
    result = {}
    flex_col = "Times_Flexible"
    has_flex = flex_col in cohort_df.columns

    for slot_col in TIME_SLOT_COLUMNS:
        if slot_col not in cohort_df.columns:
            result[slot_col] = []
            continue
        common = None
        for _, row in cohort_df.iterrows():
            slot_days = parse_days(row[slot_col])
            if treat_flexible_as_any_slot and has_flex and slot_col != flex_col:
                slot_days = slot_days | parse_days(row[flex_col])
            if common is None:
                common = slot_days
            else:
                common = common & slot_days
        result[slot_col] = sorted(common) if common else []

    return result


def format_common_slots_report(
    cohort_name: str,
    common_slots: dict[str, list[str]],
    cohort_size: int,
) -> str:
    """Produce a readable report of common (day, time) options."""
    lines = [
        f"=== {cohort_name} (n={cohort_size}) ===",
        "Days when EVERYONE is available for each time slot:",
        "",
    ]
    for slot_col in TIME_SLOT_COLUMNS:
        label = SLOT_LABELS.get(slot_col, slot_col)
        days = common_slots.get(slot_col, [])
        if days:
            lines.append(f"  {label}: {', '.join(days)}")
        else:
            lines.append(f"  {label}: (none)")
    lines.append("")
    return "\n".join(lines)


def find_best_effort_slots(
    cohort_df: pd.DataFrame,
    *,
    treat_flexible_as_any_slot: bool = True,
    top_n: int = 10,
) -> list[tuple[str, str, int]]:
    """
    When no (day, slot) works for everyone, return the best options by head count.

    Returns a list of (slot_label, day, count) sorted by count descending,
    where count = number of people in the cohort available that day in that slot.
    """
    flex_col = "Times_Flexible"
    candidates: list[tuple[str, str, int]] = []

    for slot_col in TIME_SLOT_COLUMNS:
        if slot_col not in cohort_df.columns:
            continue
        label = SLOT_LABELS.get(slot_col, slot_col)
        for day in WEEKDAYS:
            count = 0
            for _, row in cohort_df.iterrows():
                slot_days = parse_days(row[slot_col])
                if treat_flexible_as_any_slot and flex_col in cohort_df.columns and slot_col != flex_col:
                    slot_days = slot_days | parse_days(row[flex_col])
                if day in slot_days:
                    count += 1
            if count > 0:
                candidates.append((label, day, count))

    candidates.sort(key=lambda x: -x[2])
    return candidates[:top_n]


def format_best_effort_report(
    cohort_name: str,
    best: list[tuple[str, str, int]],
    cohort_size: int,
) -> str:
    """Format best-effort (day, slot) options when no perfect slot exists."""
    if not best:
        return f"{cohort_name}: No availability data.\n"
    lines = [
        f"--- {cohort_name} (n={cohort_size}): best (day, time) options ---",
        f"{'Time slot':32} | {'Day':9} | Available",
        "-" * 32 + "-+-" + "-" * 9 + "-+----------",
    ]
    for label, day, count in best:
        pct = (count / cohort_size * 100) if cohort_size else 0
        lines.append(f"{label:32} | {day:9} | {count}/{cohort_size} ({pct:.0f}%)")
    lines.append("")
    return "\n".join(lines)


def _available_for_slot(
    row: pd.Series,
    slot_col: str,
    day: str,
    treat_flexible_as_any_slot: bool = True,
) -> bool:
    """True if this row is available for the given (slot_col, day)."""
    slot_days = parse_days(row[slot_col])
    if treat_flexible_as_any_slot and "Times_Flexible" in row.index and slot_col != "Times_Flexible":
        slot_days = slot_days | parse_days(row["Times_Flexible"])
    return day in slot_days


def who_is_missing(
    cohort_df: pd.DataFrame,
    day: str,
    slot_col: str,
    *,
    treat_flexible_as_any_slot: bool = True,
) -> pd.DataFrame:
    """
    Return rows of people in the cohort who are NOT available for the given (day, slot).
    """
    missing = []
    for idx, row in cohort_df.iterrows():
        if not _available_for_slot(row, slot_col, day, treat_flexible_as_any_slot):
            missing.append(row)
    return pd.DataFrame(missing) if missing else pd.DataFrame()


def additional_details_mention_day(details_cell: str, day: str) -> bool:
    """True if the free-text details mention the given day (possible constraint)."""
    if pd.isna(details_cell) or not isinstance(details_cell, str) or not details_cell.strip():
        return False
    text = details_cell.lower()
    return day.lower() in text


def get_recommendation(
    cohort_df: pd.DataFrame,
    cohort_name: str,
    *,
    treat_flexible_as_any_slot: bool = True,
) -> dict:
    """
    Pick a single best (day, slot) for the cohort and return who's missing and any conflict notes.

    Returns a dict with: day, slot_label, slot_col, available_count, total, missing_df,
    conflict_names (list of APPLICANT names whose additional-details mention this day).
    """
    best_list = find_best_effort_slots(
        cohort_df,
        treat_flexible_as_any_slot=treat_flexible_as_any_slot,
        top_n=1,
    )
    if not best_list:
        return {
            "day": None,
            "slot_label": None,
            "slot_col": None,
            "available_count": 0,
            "total": len(cohort_df),
            "missing_df": cohort_df,
            "conflict_names": [],
        }
    slot_label, day, available_count = best_list[0]
    slot_col = next(c for c, l in SLOT_LABELS.items() if l == slot_label)
    missing_df = who_is_missing(cohort_df, day, slot_col, treat_flexible_as_any_slot=treat_flexible_as_any_slot)

    conflict_names = []
    if ADDITIONAL_DETAILS_COL in cohort_df.columns:
        for _, row in cohort_df.iterrows():
            if additional_details_mention_day(row.get(ADDITIONAL_DETAILS_COL), day):
                conflict_names.append(row.get(APPLICANT_COL, row.get("name", "")))

    return {
        "day": day,
        "slot_label": slot_label,
        "slot_col": slot_col,
        "available_count": available_count,
        "total": len(cohort_df),
        "missing_df": missing_df,
        "conflict_names": conflict_names,
    }


def format_recommendation(cohort_name: str, rec: dict) -> str:
    """Format the single recommended (day, time) plus who's missing and conflict notes."""
    if rec.get("day") is None or rec.get("slot_label") is None:
        return f"### Recommendation: {cohort_name}\n  (no availability data)\n"
    lines = [
        f"### Recommendation: {cohort_name}",
        f"  → {rec['day']} at {rec['slot_label']}",
        f"  → {rec['available_count']}/{rec['total']} available",
        "",
    ]
    if rec["missing_df"] is not None and len(rec["missing_df"]) > 0:
        lines.append("  Not available this slot:")
        for _, row in rec["missing_df"].iterrows():
            name = row.get(APPLICANT_COL, row.get(NAME_FIRST_LAST_COL, row.get("name", "?")))
            email = row.get("EMAIL Address", row.get("EMAIL", ""))
            lines.append(f"    - {name}  {email}")
        lines.append("")
    if rec.get("conflict_names"):
        lines.append("  ⚠ Additional-details mention this day (please double-check):")
        for name in rec["conflict_names"]:
            lines.append(f"    - {name}")
        lines.append("")
    return "\n".join(lines)


def build_full_report(
    merged: pd.DataFrame | None = None,
    *,
    first_choice_only: bool = False,
) -> str:
    """Build the complete scheduling report (common slots, best-effort table, recommendations).
    If first_choice_only is True, include only rows where OFFER == '1st choice' (from candidates).
    """
    if merged is None:
        merged = load_merged()
    if first_choice_only and "OFFER" in merged.columns:
        merged = merged[merged["OFFER"] == OFFER_FIRST_CHOICE].copy()
    cohort_a = get_cohort_a(merged)
    cohort_b = get_cohort_b(merged)

    common_a = find_common_slots(cohort_a)
    common_b = find_common_slots(cohort_b)

    rec_a = get_recommendation(cohort_a, "Cohort A (March 16–27 or Either)")
    rec_b = get_recommendation(cohort_b, "Cohort B (March 30–April 10 or Either)")

    parts = [
        "Meeting Time Scheduling Report",
        "=" * 40,
        "",
    ]
    if first_choice_only:
        parts.append("Filter: OFFER = 1st choice only")
        parts.append("")
    parts.extend([
        format_common_slots_report("Cohort A (March 16–27 or Either)", common_a, len(cohort_a)),
        format_common_slots_report("Cohort B (March 30–April 10 or Either)", common_b, len(cohort_b)),
        "--- Best (day, time) options by head count ---",
        "",
    ])
    for cohort_name, cohort_df in [("Cohort A", cohort_a), ("Cohort B", cohort_b)]:
        best = find_best_effort_slots(cohort_df, top_n=8)
        parts.append(format_best_effort_report(cohort_name, best, len(cohort_df)))

    parts.append("--- Recommendations (one slot per cohort) ---")
    parts.append("")
    parts.append(format_recommendation("Cohort A (March 16–27 or Either)", rec_a))
    parts.append(format_recommendation("Cohort B (March 30–April 10 or Either)", rec_b))

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Three meetings per week: EVERY person attends 3 meetings (anchor + 2 other days).
# Company can host more than 3 meetings; each person goes to Fri + 2 of Mon–Thu.
# ---------------------------------------------------------------------------

# Weekday meetings use the same time slot (11am–1pm PT) every day for simplicity.
SPLIT_MEETING_SLOT_COL = "Times_11am-1pm_PT"
WEEKDAYS_NO_FRIDAY = ["Monday", "Tuesday", "Wednesday", "Thursday"]
OFFER_SECOND_CHOICE = "2nd choice"  # Used when including 2nd choice to reach target cohort size.


def cohort_available_for_anchor(cohort_df: pd.DataFrame) -> pd.DataFrame:
    """Restrict to people who can attend the anchor meeting (Friday 9am–11am PT)."""
    return cohort_df[
        cohort_df.apply(
            lambda row: _available_for_slot(row, ANCHOR_SLOT_COL, ANCHOR_DAY),
            axis=1,
        )
    ].copy()


def availability_set_for_day_slot(
    cohort_df: pd.DataFrame,
    day: str,
    slot_col: str,
    *,
    treat_flexible_as_any_slot: bool = True,
) -> set[int]:
    """Return set of row indices (cohort_df.index) of people available for (day, slot_col)."""
    idx_available = set()
    for idx, row in cohort_df.iterrows():
        if _available_for_slot(row, slot_col, day, treat_flexible_as_any_slot):
            idx_available.add(idx)
    return idx_available


def find_three_meeting_partition(
    cohort_df: pd.DataFrame,
    *,
    anchor_day: str = ANCHOR_DAY,
    anchor_slot_col: str = ANCHOR_SLOT_COL,
    treat_flexible_as_any_slot: bool = True,
    prefer_same_slot: bool = True,
) -> dict | None:
    """
    Find two (day, slot) options and a partition of the cohort so that:
    - Everyone attends the anchor (anchor_day at anchor_slot_col).
    - Group 1 attends Meeting 2 at (day2, slot2); Group 2 attends Meeting 3 at (day3, slot3).
    - Group 1 ∪ Group 2 = cohort (after restricting to people who can make the anchor).

    Returns None if no valid partition exists. Otherwise returns:
      anchor_available_df, not_anchor_available_df,
      meeting2_day, meeting2_slot_label, meeting2_slot_col,
      meeting3_day, meeting3_slot_label, meeting3_slot_col,
      group1_df, group2_df, group1_names, group2_names
    """
    # Restrict to people who can make the anchor
    anchor_available = cohort_df[
        cohort_df.apply(
            lambda row: _available_for_slot(row, anchor_slot_col, anchor_day, treat_flexible_as_any_slot),
            axis=1,
        )
    ].copy()
    not_anchor = cohort_df.drop(index=anchor_available.index, errors="ignore")
    cohort = anchor_available
    if len(cohort) == 0:
        return None
    n = len(cohort)
    indices = set(cohort.index)

    # Build availability for each (day, slot) — exclude anchor day/slot for the "other" meetings
    slot_cols = [c for c in TIME_SLOT_COLUMNS if c in cohort.columns and c != "Times_Flexible"]
    options: list[tuple[str, str, set[int]]] = []  # (day, slot_col, set of index)
    for day in WEEKDAYS:
        if day == anchor_day:
            continue
        for slot_col in slot_cols:
            avail = availability_set_for_day_slot(cohort, day, slot_col, treat_flexible_as_any_slot=treat_flexible_as_any_slot)
            if avail:
                options.append((day, slot_col, avail))

    best = None
    best_score: tuple = (-1, -1, -1)  # (same_slot 0/1, balance, coverage)

    for i, (day2, slot2, set2) in enumerate(options):
        for j, (day3, slot3, set3) in enumerate(options):
            if i >= j:
                continue
            # No member attends 2 meetings on the same day: split meetings must be on different days
            if day2 == day3:
                continue
            union = set2 | set3
            coverage = len(union)
            # Require at least one person can be assigned (we allow anchor-only for the rest)
            if coverage == 0:
                continue
            only2 = set2 - set3
            only3 = set3 - set2
            both = set2 & set3
            g1_size_target = (coverage + 1) // 2
            g1 = set(only2)
            for idx in sorted(both):
                if len(g1) < g1_size_target:
                    g1.add(idx)
            g2 = union - g1
            anchor_only = indices - union
            res = {
                "anchor_available_df": anchor_available,
                "not_anchor_available_df": not_anchor,
                "meeting2_day": day2,
                "meeting2_slot_label": SLOT_LABELS.get(slot2, slot2),
                "meeting2_slot_col": slot2,
                "meeting3_day": day3,
                "meeting3_slot_label": SLOT_LABELS.get(slot3, slot3),
                "meeting3_slot_col": slot3,
                "group1_indices": g1,
                "group2_indices": g2,
                "group1_df": cohort.loc[list(g1)],
                "group2_df": cohort.loc[list(g2)],
                "anchor_only_indices": anchor_only,
                "anchor_only_df": cohort.loc[list(anchor_only)] if anchor_only else pd.DataFrame(),
            }
            balance = min(len(g1), len(g2)) if (g1 or g2) else 0
            same_slot = 1 if slot2 == slot3 else 0
            # Prefer: full coverage (no anchor-only), then same slot, then balance
            score = (1 if (anchor_only == set()) else 0, same_slot if prefer_same_slot else 0, balance)
            if best is None or score > best_score:
                best = res
                best_score = score

    if best is None:
        return None
    name_col = APPLICANT_COL if APPLICANT_COL in cohort.columns else "name"
    best["group1_names"] = best["group1_df"][name_col].tolist()
    best["group2_names"] = best["group2_df"][name_col].tolist()
    best["anchor_only_names"] = best["anchor_only_df"][name_col].tolist() if len(best["anchor_only_df"]) > 0 else []
    return best


def is_fittable_for_three_meetings(
    cohort_df: pd.DataFrame,
    *,
    anchor_day: str = ANCHOR_DAY,
    anchor_slot_col: str = ANCHOR_SLOT_COL,
    split_slot_col: str = SPLIT_MEETING_SLOT_COL,
    treat_flexible_as_any_slot: bool = True,
) -> pd.Series:
    """
    Boolean Series (index = cohort_df.index): True if person can attend anchor (Friday)
    and has at least 2 weekdays (Mon–Thu) available for the split slot.
    Used to select who is eligible for the cohort (can't fit 3 meetings -> not considered).
    """
    # Can they make the full-cohort meeting (Friday 9am)?
    can_anchor = cohort_df.apply(
        lambda row: _available_for_slot(row, anchor_slot_col, anchor_day, treat_flexible_as_any_slot),
        axis=1,
    )
    # How many weekdays (Mon–Thu) are they available for the split meetings (11am–1pm)?
    weekday_count = pd.Series(index=cohort_df.index, dtype=int)
    for idx in cohort_df.index:
        row = cohort_df.loc[idx]
        n = sum(
            1
            for day in WEEKDAYS_NO_FRIDAY
            if _available_for_slot(row, split_slot_col, day, treat_flexible_as_any_slot)
        )
        weekday_count[idx] = n
    # Fittable = Friday + at least 2 weekdays (so we can assign them 3 meetings on 3 days).
    return can_anchor & (weekday_count >= 2)


def find_three_meetings_each(
    cohort_df: pd.DataFrame,
    *,
    anchor_day: str = ANCHOR_DAY,
    anchor_slot_col: str = ANCHOR_SLOT_COL,
    split_slot_col: str = SPLIT_MEETING_SLOT_COL,
    treat_flexible_as_any_slot: bool = True,
) -> dict | None:
    """
    Assign each person to 3 meetings per week: anchor (Friday) + 2 other weekdays.
    No one has 2 meetings on the same day. Company hosts 1 + 4 = 5 meetings (Fri + Mon–Thu).
    Each person is assigned to exactly 2 of Mon–Thu (greedy balance).
    """
    # Restrict to people who can make the anchor (Friday 9am). Others go to not_anchor (reported as limited).
    anchor_available = cohort_df[
        cohort_df.apply(
            lambda row: _available_for_slot(row, anchor_slot_col, anchor_day, treat_flexible_as_any_slot),
            axis=1,
        )
    ].copy()
    not_anchor = cohort_df.drop(index=anchor_available.index, errors="ignore")
    cohort = anchor_available
    if len(cohort) == 0:
        return None
    n = len(cohort)
    indices = list(cohort.index)

    # For each person, which weekdays (Mon–Thu) are they available for the split slot (11am–1pm)?
    available_weekdays: dict[int, set[str]] = {}
    for idx in indices:
        row = cohort.loc[idx]
        days = set()
        for day in WEEKDAYS_NO_FRIDAY:
            if _available_for_slot(row, split_slot_col, day, treat_flexible_as_any_slot):
                days.add(day)
        available_weekdays[idx] = days

    # Anyone with < 2 available weekdays cannot get 3 meetings (Fri + 2 others); exclude from assignment.
    limited = [idx for idx in indices if len(available_weekdays[idx]) < 2]
    cohort_valid = cohort.drop(index=limited, errors="ignore")
    if len(cohort_valid) == 0:
        return None
    indices_valid = list(cohort_valid.index)

    # Assign each person to exactly 2 days from their available set.
    # Greedy balance: when assigning a person, pick the 2 days with smallest current counts (and use day name as tiebreaker).
    day_counts: dict[str, int] = {d: 0 for d in WEEKDAYS_NO_FRIDAY}
    person_to_days: dict[int, list[str]] = {}  # each person -> list of 2 days (their weekday meetings)

    for idx in indices_valid:
        avail = available_weekdays[idx]
        sorted_days = sorted(avail, key=lambda d: (day_counts[d], d))
        if len(sorted_days) < 2:
            limited.append(idx)
            continue
        d1, d2 = sorted_days[0], sorted_days[1]
        person_to_days[idx] = [d1, d2]
        day_counts[d1] += 1
        day_counts[d2] += 1

    # Build per-day attendee lists (for report: who attends Monday, Tuesday, etc.).
    day_to_indices: dict[str, list[int]] = {d: [] for d in WEEKDAYS_NO_FRIDAY}
    for idx, days in person_to_days.items():
        for d in days:
            day_to_indices[d].append(idx)

    split_slot_label = SLOT_LABELS.get(split_slot_col, split_slot_col)
    return {
        "anchor_available_df": anchor_available,
        "not_anchor_available_df": not_anchor,
        "cohort_df": cohort,
        "limited_indices": limited,
        "limited_df": cohort.loc[limited] if limited else pd.DataFrame(),
        "split_slot_col": split_slot_col,
        "split_slot_label": split_slot_label,
        "person_to_days": person_to_days,
        "day_to_indices": day_to_indices,
        "day_to_df": {d: cohort.loc[day_to_indices[d]] for d in WEEKDAYS_NO_FRIDAY},
    }


def _row_name_email(row: pd.Series) -> str:
    """Format a row as 'Name — email' for report output."""
    name = row.get(APPLICANT_COL, row.get(NAME_FIRST_LAST_COL, row.get("name", "?")))
    email = row.get("EMAIL Address", row.get("EMAIL", ""))
    if email:
        return f"{name} — {email}"
    return str(name)


def _row_name_email_offer(row: pd.Series) -> str:
    """Format a row as 'Name — email (1st choice)' or '(2nd choice)' when OFFER is present."""
    base = _row_name_email(row)
    offer = row.get("OFFER", None)
    if pd.notna(offer) and offer:
        return f"{base} ({offer})"
    return base


def three_meetings_schedule_to_dataframe(result: dict | None) -> pd.DataFrame:
    """
    Build a DataFrame of the three-meetings schedule for CSV/Google Sheets export.
    Columns: Name, Email, Choice, Meeting 1, Meeting 2, Meeting 3.
    Returns empty DataFrame if result is None.
    """
    if result is None or not result.get("person_to_days"):
        return pd.DataFrame(columns=["Name", "Email", "Choice", "Meeting 1", "Meeting 2", "Meeting 3"])
    cohort = result["cohort_df"]
    person_to_days = result["person_to_days"]
    slot_label = result["split_slot_label"]
    name_col = APPLICANT_COL if APPLICANT_COL in cohort.columns else "name"
    email_col = "EMAIL Address" if "EMAIL Address" in cohort.columns else "EMAIL"
    meeting_1_label = f"Friday 9am–11am PT"
    rows = []
    for idx in person_to_days:
        row = cohort.loc[idx]
        name = row.get(name_col, "?")
        email = row.get(email_col, "")
        offer = row.get("OFFER", "")
        d1, d2 = person_to_days[idx]
        meeting_2 = f"{d1} {slot_label}"
        meeting_3 = f"{d2} {slot_label}"
        rows.append({
            "Name": name,
            "Email": email if pd.notna(email) else "",
            "Choice": offer if pd.notna(offer) else "",
            "Meeting 1": meeting_1_label,
            "Meeting 2": meeting_2,
            "Meeting 3": meeting_3,
        })
    return pd.DataFrame(rows)


def three_meetings_schedule_by_meeting_to_dataframe(result: dict | None) -> pd.DataFrame:
    """
    Build a DataFrame of the schedule grouped by meeting for Google Sheets.
    Each row = one attendee in one meeting. Columns: Meeting, Day & Time, Name, Email, Choice.
    Enables filtering by meeting to see each grouping and its attendees.
    """
    if result is None:
        return pd.DataFrame(columns=["Meeting", "Day & Time", "Name", "Email", "Choice"])
    name_col = APPLICANT_COL if APPLICANT_COL in result["cohort_df"].columns else "name"
    email_col = "EMAIL Address" if "EMAIL Address" in result["cohort_df"].columns else "EMAIL"
    anchor_label = f"{ANCHOR_DAY} at {SLOT_LABELS.get(ANCHOR_SLOT_COL, ANCHOR_SLOT_COL)}"
    slot_label = result["split_slot_label"]
    rows = []
    # Meeting 1: full cohort (Friday 9am).
    for _, row in result["anchor_available_df"].iterrows():
        rows.append({
            "Meeting": "Meeting 1 (everyone)",
            "Day & Time": anchor_label,
            "Name": row.get(name_col, "?"),
            "Email": row.get(email_col, "") if pd.notna(row.get(email_col, "")) else "",
            "Choice": row.get("OFFER", "") if pd.notna(row.get("OFFER", "")) else "",
        })
    # Meetings 2–5: weekday split meetings.
    for day in WEEKDAYS_NO_FRIDAY:
        df = result["day_to_df"][day]
        if len(df) == 0:
            continue
        day_time = f"{day} at {slot_label}"
        meeting_num = {"Monday": 2, "Tuesday": 3, "Wednesday": 4, "Thursday": 5}[day]
        meeting_name = f"Meeting {meeting_num} ({day})"
        for _, row in df.iterrows():
            rows.append({
                "Meeting": meeting_name,
                "Day & Time": day_time,
                "Name": row.get(name_col, "?"),
                "Email": row.get(email_col, "") if pd.notna(row.get(email_col, "")) else "",
                "Choice": row.get("OFFER", "") if pd.notna(row.get("OFFER", "")) else "",
            })
    return pd.DataFrame(rows)


def format_three_meeting_report(partition: dict | None, cohort_name: str = "Cohort A + Either") -> str:
    """Format a readable report for the three-meeting (1 full + 2 split) schedule."""
    if partition is None:
        return f"{cohort_name}: No valid partition found for three meetings (anchor + two split days).\n"
    lines = [
        f"Three meetings per week — {cohort_name}",
        "=" * 50,
        "",
        "No member attends 2 meetings on the same day (split meetings are on different days).",
        "",
        "Meeting 1 (everyone):",
        f"  {ANCHOR_DAY} at {SLOT_LABELS.get(ANCHOR_SLOT_COL, ANCHOR_SLOT_COL)}",
        f"  Attendees: {len(partition['anchor_available_df'])} people",
        "",
    ]
    for _, row in partition["anchor_available_df"].iterrows():
        lines.append(f"  - {_row_name_email(row)}")
    lines.extend(["", "Meeting 2 (Group 1):", f"  {partition['meeting2_day']} at {partition['meeting2_slot_label']}", f"  Attendees: {len(partition['group1_df'])} people", ""])
    for _, row in partition["group1_df"].iterrows():
        lines.append(f"  - {_row_name_email(row)}")
    lines.extend(["", "Meeting 3 (Group 2):", f"  {partition['meeting3_day']} at {partition['meeting3_slot_label']}", f"  Attendees: {len(partition['group2_df'])} people", ""])
    for _, row in partition["group2_df"].iterrows():
        lines.append(f"  - {_row_name_email(row)}")
    # Limited-availability members
    limited = []
    for _, row in partition["not_anchor_available_df"].iterrows():
        limited.append((_row_name_email(row), "cannot attend Friday 9am"))
    for _, row in partition.get("anchor_only_df", pd.DataFrame()).iterrows():
        limited.append((_row_name_email(row), "no other day works for second meeting"))
    if limited:
        lines.append("")
        lines.append("Limited availability (consider alternate candidate if needed):")
        for name_email, reason in limited:
            lines.append(f"  - {name_email} ({reason})")
    return "\n".join(lines)


def format_three_meetings_each_report(
    result: dict | None,
    cohort_name: str = "Cohort A + Either",
    excluded_for_availability: pd.DataFrame | None = None,
) -> str:
    """Format report when every person attends 3 meetings (anchor + 2 other days).
    excluded_for_availability: people from the pool who were excluded because they couldn't fit 3 meetings.
    """
    if result is None:
        return f"{cohort_name}: No valid schedule found.\n"
    n = len(result["anchor_available_df"])
    lines = [
        f"Three meetings per person per week — {cohort_name}",
        "=" * 55,
        "",
        f"Selected: {n} people (by availability; 1st choice preferred, then 2nd; only those who fit into 3 meetings are included).",
        "",
        "Everyone attends: Friday 9am (full cohort) + 2 other weekdays (assigned). No one has 2 meetings on the same day.",
        "",
        "Meeting 1 (everyone):",
        f"  {ANCHOR_DAY} at {SLOT_LABELS.get(ANCHOR_SLOT_COL, ANCHOR_SLOT_COL)}",
        f"  Attendees: {len(result['anchor_available_df'])} people",
        "",
    ]
    # Full-cohort meeting: list everyone with name, email, and choice (1st/2nd).
    for _, row in result["anchor_available_df"].iterrows():
        lines.append(f"  - {_row_name_email_offer(row)}")
    lines.append("")

    # Meetings 2–5: one section per weekday (Mon–Thu) with that day's attendees.
    slot_label = result["split_slot_label"]
    for day in WEEKDAYS_NO_FRIDAY:
        df = result["day_to_df"][day]
        if len(df) == 0:
            continue
        lines.append(f"Meeting — {day} at {slot_label}:")
        lines.append(f"  Attendees: {len(df)} people")
        lines.append("")
        for _, row in df.iterrows():
            lines.append(f"  - {_row_name_email_offer(row)}")
        lines.append("")

    # Per-person schedule: each person's 3 meetings (Fri + 2 weekdays), with choice.
    lines.append("Per-person schedule (3 meetings each):")
    lines.append("-" * 40)
    cohort = result["cohort_df"]
    name_col = APPLICANT_COL if APPLICANT_COL in cohort.columns else "name"
    for idx in result.get("person_to_days", {}):
        row = cohort.loc[idx]
        line = f"  {_row_name_email_offer(row)}:  Friday 9am, {result['person_to_days'][idx][0]} {slot_label}, {result['person_to_days'][idx][1]} {slot_label}"
        lines.append(line)
    lines.append("")

    # At the bottom: everyone excluded for availability reasons (couldn't fit into 3 meetings).
    if excluded_for_availability is not None and len(excluded_for_availability) > 0:
        lines.append("Excluded for availability reasons (could not fit into 3 meetings):")
        lines.append("-" * 55)
        for _, row in excluded_for_availability.iterrows():
            can_anchor = _available_for_slot(row, ANCHOR_SLOT_COL, ANCHOR_DAY)
            if not can_anchor:
                reason = "cannot attend Friday 9am"
            else:
                n_weekdays = sum(
                    1
                    for day in WEEKDAYS_NO_FRIDAY
                    if _available_for_slot(row, SPLIT_MEETING_SLOT_COL, day)
                )
                reason = "fewer than 2 weekdays available for second/third meeting" if n_weekdays < 2 else "could not be assigned"
            lines.append(f"  - {_row_name_email_offer(row)}  → {reason}")
        lines.append("")

    # If any in the selected cohort couldn't make Friday or had < 2 weekdays (edge case), list them.
    limited_df = result.get("limited_df", pd.DataFrame())
    not_anchor = result["not_anchor_available_df"]
    if len(not_anchor) or len(limited_df):
        lines.append("Limited availability (consider alternate candidate if needed):")
        for _, row in not_anchor.iterrows():
            lines.append(f"  - {_row_name_email_offer(row)} (cannot attend Friday 9am)")
        for _, row in limited_df.iterrows():
            lines.append(f"  - {_row_name_email_offer(row)} (fewer than 2 other days available for second/third meeting)")
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    from datetime import datetime

    parser = argparse.ArgumentParser(description="Generate meeting time scheduling report from form and candidates CSVs.")
    parser.add_argument(
        "--output",
        "-o",
        metavar="FILE",
        help="Write report to FILE (default: print to stdout)",
    )
    parser.add_argument(
        "--report-dir",
        metavar="DIR",
        default=None,
        help="Write report to DIR/scheduling_report_YYYY-MM-DD.txt (ignored if --output is set)",
    )
    parser.add_argument(
        "--first-choice-only",
        action="store_true",
        help="Include only people with OFFER = '1st choice' (from candidates.csv)",
    )
    args = parser.parse_args()

    report = build_full_report(first_choice_only=args.first_choice_only)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report, encoding="utf-8")
        print(f"Report written to {out_path}")
    elif args.report_dir:
        report_dir = Path(args.report_dir)
        report_dir.mkdir(parents=True, exist_ok=True)
        date_str = datetime.now().strftime("%Y-%m-%d")
        out_path = report_dir / f"scheduling_report_{date_str}.txt"
        out_path.write_text(report, encoding="utf-8")
        print(f"Report written to {out_path}")
    else:
        print(report)
