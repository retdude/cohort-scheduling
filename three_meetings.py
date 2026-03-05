#!/usr/bin/env python3
"""
Three meetings per person per week — Cohort A + Either, 1st and 2nd choice.

- Target: up to 21 people. Selection by availability: only people who fit into
  three meetings (Fri + 2 weekdays) are included; 1st choice preferred, then 2nd.
- Everyone attends exactly 3 meetings; no one has 2 meetings on the same day.
- Scope: March 16–27 or Either. OFFER = 1st choice or 2nd choice.
"""
import argparse
from pathlib import Path

from load_form_data import (
    load_merged,
    get_cohort_a,
    OFFER_FIRST_CHOICE,
    OFFER_SECOND_CHOICE,
    is_fittable_for_three_meetings,
    find_three_meetings_each,
    format_three_meetings_each_report,
    three_meetings_schedule_to_dataframe,
    three_meetings_schedule_by_meeting_to_dataframe,
)

# Target cohort size (boss requirement). Can override with -n.
TARGET_COHORT_SIZE = 21


def main():
    parser = argparse.ArgumentParser(description="Three meetings per person (Fri + 2 weekdays), up to 21 people.")
    parser.add_argument("-o", "--output", metavar="FILE", help="Write report to FILE")
    parser.add_argument("-n", "--max-size", type=int, default=TARGET_COHORT_SIZE, metavar="N", help=f"Max cohort size (default: {TARGET_COHORT_SIZE})")
    args = parser.parse_args()

    # Load merged form + candidates; restrict to Cohort A (March 16–27 or Either).
    merged = load_merged()
    cohort_a = get_cohort_a(merged)

    # Include only 1st and 2nd choice. Sort so 1st choice comes first (preferred when capping).
    if "OFFER" in cohort_a.columns:
        cohort_a = cohort_a[
            cohort_a["OFFER"].isin([OFFER_FIRST_CHOICE, OFFER_SECOND_CHOICE])
        ].copy()
        cohort_a["_offer_order"] = cohort_a["OFFER"].map({OFFER_FIRST_CHOICE: 0, OFFER_SECOND_CHOICE: 1})
        cohort_a = cohort_a.sort_values("_offer_order").drop(columns=["_offer_order"])
    cohort_a = cohort_a.drop_duplicates(subset=["APPLICANT"], keep="first")

    # Keep only people who can fit into 3 meetings: Friday 9am + at least 2 weekdays at 11am.
    # Anyone who can't is excluded for availability (listed at bottom of report).
    fittable = is_fittable_for_three_meetings(cohort_a)
    excluded_for_availability = cohort_a.loc[~fittable].copy()
    cohort_a = cohort_a.loc[fittable[fittable].index].copy()
    # Cap at max_size, in preference order (1st choice already first).
    cohort_selected = cohort_a.head(args.max_size).copy()

    # Assign each selected person to 2 weekdays (greedy balance); build 5-meeting schedule.
    result = find_three_meetings_each(cohort_selected)
    cohort_label = f"Cohort A + Either, 1st & 2nd choice (March 16–27 or Either), up to {args.max_size}"
    report = format_three_meetings_each_report(
        result,
        cohort_name=cohort_label,
        excluded_for_availability=excluded_for_availability,
    )

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report, encoding="utf-8")
        print(f"Report written to {out}")
        # Export schedule CSVs for Google Sheets.
        base = out.with_suffix("")
        schedule_df = three_meetings_schedule_to_dataframe(result)
        if not schedule_df.empty:
            csv_path = base.with_suffix(".csv")
            schedule_df.to_csv(csv_path, index=False, encoding="utf-8")
            print(f"Schedule CSV (by person) written to {csv_path}")
        by_meeting_df = three_meetings_schedule_by_meeting_to_dataframe(result)
        if not by_meeting_df.empty:
            by_meeting_path = base.parent / f"{base.name}_by_meeting.csv"
            by_meeting_df.to_csv(by_meeting_path, index=False, encoding="utf-8")
            print(f"Schedule CSV (by meeting / groupings) written to {by_meeting_path}")
    else:
        print(report)
    return report


if __name__ == "__main__":
    main()
