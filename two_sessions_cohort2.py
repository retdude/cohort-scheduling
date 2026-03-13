#!/usr/bin/env python3
"""
Cohort 2: Two sessions per person — one anchor (most people) + one of two other sessions.
Company holds 3 sessions total (no two on the same day). Excludes people who can only make one session.
"""
import argparse
from pathlib import Path

from cohort_2_schedule import (
    load_cohort_2_merged,
    best_availability_counts,
    find_anchor_and_two_sessions,
    format_two_sessions_report,
    two_sessions_cohort2_to_dataframe,
    two_sessions_cohort2_by_meeting_to_dataframe,
)


def main():
    parser = argparse.ArgumentParser(
        description="Cohort 2: Schedule 3 sessions (anchor + 2 others); each person attends 2."
    )
    parser.add_argument("-o", "--output", metavar="FILE", help="Write report to FILE")
    parser.add_argument(
        "--show-availability",
        action="store_true",
        help="Print (day, time) availability counts before the schedule",
    )
    args = parser.parse_args()

    merged = load_cohort_2_merged()
    if merged.empty:
        print("No cohort 2 data (merge of candidates + form results is empty).")
        return

    # Optional: only 1st and 2nd choice
    if "OFFER" in merged.columns:
        merged = merged[
            merged["OFFER"].astype(str).str.strip().isin(["1st choice", "2nd choice"])
        ].copy()
    if merged.empty:
        print("No cohort 2 candidates with OFFER 1st or 2nd choice.")
        return

    if args.show_availability:
        best = best_availability_counts(merged)
        print("Cohort 2 — (day, time) availability (top options):")
        print(f"  {'Day':<10} {'Time':<35} Count")
        print("  " + "-" * 50)
        for day, label, count in best[:15]:
            print(f"  {day:<10} {label:<35} {count}")
        print()

    result = find_anchor_and_two_sessions(merged)
    report = format_two_sessions_report(result, cohort_name="Cohort 2")

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report, encoding="utf-8")
        print(f"Report written to {out}")
        base = out.with_suffix("")
        if result and result.get("person_to_second_session"):
            df = two_sessions_cohort2_to_dataframe(result)
            df.to_csv(base.with_suffix(".csv"), index=False, encoding="utf-8")
            print(f"Schedule CSV (by person) written to {base.with_suffix('.csv')}")
            by_m = two_sessions_cohort2_by_meeting_to_dataframe(result)
            by_m.to_csv(base.parent / f"{base.name}_by_meeting.csv", index=False, encoding="utf-8")
            print(f"Schedule CSV (by meeting) written to {base.name}_by_meeting.csv")
    else:
        print(report)


if __name__ == "__main__":
    main()
