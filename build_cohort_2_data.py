#!/usr/bin/env python3
"""
Add cohort 1 people who pass filters to cohort 2 candidate and form files.

Filters (person is EXCLUDED from being added if either applies):
  1. They marked cohort 1 in the form (COHORT = "March 16 - 27 2026" in cohort_1_form_results).
  2. They were selected for the first cohort (appear in reports/two_meetings_schedule.csv
     or reports/three_meetings_schedule.csv).

We ADD to the existing files:
  - data/cohort_2_candidates.csv: append candidate rows from cohort_1_candidates.
  - data/cohort_2_form_results.csv: append form rows from cohort_1_form_results.
     If cohort_2_form_results.csv does not exist, we use cohort_2_form_responses.csv
     as the initial content, then append (so existing cohort 2 form data is preserved).

Matching is by normalized name ("Last, First") to avoid duplicates and to align with reports.
"""
from pathlib import Path

import pandas as pd

from load_form_data import (
    parse_name_to_last_first,
    COHORT_MARCH_16_27,
    APPLICANT_COL,
)
from load_form_data import NAME_FIRST_LAST_COL

DATA_DIR = Path(__file__).resolve().parent / "data"
REPORTS_DIR = Path(__file__).resolve().parent / "reports"

COHORT_1_CANDIDATES = DATA_DIR / "cohort_1_candidates.csv"
COHORT_1_FORM_RESULTS = DATA_DIR / "cohort_1_form_results.csv"
COHORT_2_CANDIDATES = DATA_DIR / "cohort_2_candidates.csv"
COHORT_2_FORM_RESULTS = DATA_DIR / "cohort_2_form_results.csv"
COHORT_2_FORM_RESPONSES = DATA_DIR / "cohort_2_form_responses.csv"
TWO_MEETINGS_CSV = REPORTS_DIR / "two_meetings_schedule.csv"
THREE_MEETINGS_CSV = REPORTS_DIR / "three_meetings_schedule.csv"


def _normalized_name_from_row(row: pd.Series, name_col: str) -> str:
    """Get normalized 'Last, First' name from a row."""
    raw = row.get(name_col, row.get("Name", ""))
    if pd.isna(raw):
        return ""
    return parse_name_to_last_first(str(raw).strip())


def _build_exclude_set() -> set[str]:
    """
    People to exclude from being added to cohort 2:
    - Anyone who marked cohort 1 in cohort_1_form_results (COHORT == March 16 - 27 2026).
    - Anyone who appears as selected in two_meetings_schedule.csv or three_meetings_schedule.csv.
    Returns set of normalized names (Last, First).
    """
    exclude = set()

    # From cohort 1 form: anyone who selected cohort 1 (March 16 - 27 2026)
    if COHORT_1_FORM_RESULTS.exists():
        form = pd.read_csv(COHORT_1_FORM_RESULTS, encoding="utf-8")
        name_col = APPLICANT_COL if APPLICANT_COL in form.columns else "Name (First, Last)"
        for _, row in form.iterrows():
            if str(row.get("COHORT", "")).strip() == COHORT_MARCH_16_27:
                name = _normalized_name_from_row(row, name_col)
                if name:
                    exclude.add(name)

    # From reports: anyone selected for cohort 1
    for report_path in (TWO_MEETINGS_CSV, THREE_MEETINGS_CSV):
        if report_path.exists():
            df = pd.read_csv(report_path, encoding="utf-8")
            if "Name" not in df.columns:
                continue
            for _, row in df.iterrows():
                name = _normalized_name_from_row(row, "Name")
                if name:
                    exclude.add(name)

    return exclude


def _existing_normalized_names(df: pd.DataFrame, name_col: str) -> set[str]:
    """Set of normalized names already in df."""
    out = set()
    for _, row in df.iterrows():
        n = _normalized_name_from_row(row, name_col)
        if n:
            out.add(n)
    return out


def main() -> None:
    import os
    verbose = os.environ.get("BUILD_COHORT2_VERBOSE", "").lower() in ("1", "true", "yes")
    exclude = _build_exclude_set()
    print(f"Excluding {len(exclude)} people (marked cohort 1 in form or selected for cohort 1).")
    if verbose:
        print("  Excluded names:", sorted(exclude))

    # Load cohort 1 data
    c1_candidates = pd.read_csv(COHORT_1_CANDIDATES, encoding="utf-8")
    c1_form = pd.read_csv(COHORT_1_FORM_RESULTS, encoding="utf-8")
    c1_form_name_col = APPLICANT_COL if APPLICANT_COL in c1_form.columns else NAME_FIRST_LAST_COL
    c1_candidates["_name"] = c1_candidates["APPLICANT"].map(
        lambda x: parse_name_to_last_first(str(x).strip()) if pd.notna(x) else ""
    )
    c1_form["_name"] = c1_form[c1_form_name_col].map(
        lambda x: parse_name_to_last_first(str(x).strip()) if pd.notna(x) else ""
    )

    # Who from cohort 1 passes filters? (in form, did not mark cohort 1, not in exclude)
    form_marked_cohort1 = set(
        c1_form.loc[c1_form["COHORT"].astype(str).str.strip() == COHORT_MARCH_16_27, "_name"]
    )
    add_names = set()
    for _, row in c1_form.iterrows():
        n = row["_name"]
        if not n or n in exclude or n in form_marked_cohort1:
            continue
        add_names.add(n)
    if verbose:
        print(f"  Cohort 1 people who passed filters (did not mark cohort 1, not selected): {len(add_names)}")
        if add_names:
            print("  ", sorted(add_names))

    # Load existing cohort 2 files
    c2_candidates = pd.read_csv(COHORT_2_CANDIDATES, encoding="utf-8")
    c2_cand_name_col = "APPLICANT" if "APPLICANT" in c2_candidates.columns else "Name"
    existing_c2_cand_names = _existing_normalized_names(c2_candidates, c2_cand_name_col)
    existing_c2_cand_names_initial = set(existing_c2_cand_names)

    if COHORT_2_FORM_RESULTS.exists():
        c2_form = pd.read_csv(COHORT_2_FORM_RESULTS, encoding="utf-8")
    else:
        if COHORT_2_FORM_RESPONSES.exists():
            c2_form = pd.read_csv(COHORT_2_FORM_RESPONSES, encoding="utf-8")
            print(f"Using {COHORT_2_FORM_RESPONSES.name} as base for cohort_2_form_results.")
        else:
            c2_form = pd.DataFrame()
    c2_form_name_col = None
    for col in (APPLICANT_COL, NAME_FIRST_LAST_COL, "Name (First, Last)", "Name"):
        if col in c2_form.columns:
            c2_form_name_col = col
            break
    existing_c2_form_names = _existing_normalized_names(c2_form, c2_form_name_col or "Name") if len(c2_form) else set()

    # Append cohort 1 rows that pass and are not already in cohort 2
    to_add_cand = []
    to_add_form = []
    for n in add_names:
        if n in existing_c2_cand_names:
            continue
        cand_rows = c1_candidates[c1_candidates["_name"] == n]
        form_rows = c1_form[c1_form["_name"] == n]
        if len(cand_rows) == 0 or len(form_rows) == 0:
            continue
        cand_row = cand_rows.iloc[0].drop(labels=["_name"], errors="ignore")
        form_row = form_rows.iloc[0].drop(labels=["_name"], errors="ignore")
        to_add_cand.append(cand_row)
        if n not in existing_c2_form_names:
            to_add_form.append(form_row)
            existing_c2_form_names.add(n)
        existing_c2_cand_names.add(n)

    if verbose and add_names:
        already_in_c2 = add_names & existing_c2_cand_names_initial
        if already_in_c2:
            print(f"  Already in cohort 2 (not appended): {sorted(already_in_c2)}")

    if not to_add_cand:
        print("No new people to add from cohort 1 (all either marked cohort 1, were selected, or already in cohort 2).")
        if not COHORT_2_FORM_RESULTS.exists() and len(c2_form):
            c2_form.to_csv(COHORT_2_FORM_RESULTS, index=False, encoding="utf-8")
            print(f"Wrote {COHORT_2_FORM_RESULTS.name} with existing cohort 2 form data.")
        return

    # Append and write (align new rows to existing columns)
    new_cand = pd.DataFrame(to_add_cand)
    for c in c2_candidates.columns:
        if c not in new_cand.columns:
            new_cand[c] = ""
    new_cand = new_cand[c2_candidates.columns]
    out_candidates = pd.concat([c2_candidates, new_cand], ignore_index=True)
    out_candidates.to_csv(COHORT_2_CANDIDATES, index=False, encoding="utf-8")
    print(f"Appended {len(to_add_cand)} row(s) to {COHORT_2_CANDIDATES.name}.")

    if to_add_form:
        new_form = pd.DataFrame(to_add_form)
        if len(c2_form):
            out_form = pd.concat([c2_form, new_form], ignore_index=True, sort=False)
        else:
            out_form = new_form
        out_form.to_csv(COHORT_2_FORM_RESULTS, index=False, encoding="utf-8")
        print(f"Appended {len(to_add_form)} row(s) to {COHORT_2_FORM_RESULTS.name}.")
    else:
        if not COHORT_2_FORM_RESULTS.exists() and len(c2_form):
            c2_form.to_csv(COHORT_2_FORM_RESULTS, index=False, encoding="utf-8")
            print(f"Wrote {COHORT_2_FORM_RESULTS.name} (existing form data only, no new form rows to add).")

    print("Done.")


if __name__ == "__main__":
    import sys
    if "--verbose" in sys.argv or "-v" in sys.argv:
        import os
        os.environ["BUILD_COHORT2_VERBOSE"] = "1"
    main()
