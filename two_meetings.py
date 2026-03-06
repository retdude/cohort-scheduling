#!/usr/bin/env python3
"""
Two sessions per person per week — Cohort A + Either, 1st and 2nd choice.

New plan: Monday & Tuesday = remote independent work. Wednesday 11am and Thursday 11am
and Friday 9am remain. Each student attends 2 sessions: Friday 9am (all-hands) +
EITHER Wednesday 11am XOR Thursday 11am.

- Scope: Cohort A + Either only (March 16–27 or Either).
- Prioritize 1st choice, then 2nd choice. Target ~21 candidates.
- Only include people who are (A) available Friday 9am, (B) available for either
  Wednesday 11am OR Thursday 11am.
"""
import argparse
from pathlib import Path

from load_form_data import (
    load_merged,
    get_cohort_a,
    OFFER_FIRST_CHOICE,
    OFFER_SECOND_CHOICE,
    is_fittable_for_two_meetings,
    find_two_meetings_each,
    format_two_meetings_each_report,
    two_meetings_schedule_to_dataframe,
    two_meetings_schedule_by_meeting_to_dataframe,
)

TARGET_COHORT_SIZE = 21


def main():
    parser = argparse.ArgumentParser(
        description="Two sessions per person: Friday 9am + Wed XOR Thu 11am (Cohort A + Either, up to 21)."
    )
    parser.add_argument("-o", "--output", metavar="FILE", help="Write report to FILE")
    parser.add_argument(
        "-n", "--max-size",
        type=int,
        default=TARGET_COHORT_SIZE,
        metavar="N",
        help=f"Max cohort size (default: {TARGET_COHORT_SIZE})",
    )
    args = parser.parse_args()

    # Cohort A + Either only (March 16–27 or Either).
    merged = load_merged()
    cohort_a = get_cohort_a(merged)

    # 1st and 2nd choice only; 1st preferred when capping.
    if "OFFER" in cohort_a.columns:
        cohort_a = cohort_a[
            cohort_a["OFFER"].isin([OFFER_FIRST_CHOICE, OFFER_SECOND_CHOICE])
        ].copy()
        cohort_a["_offer_order"] = cohort_a["OFFER"].map(
            {OFFER_FIRST_CHOICE: 0, OFFER_SECOND_CHOICE: 1}
        )
        cohort_a = cohort_a.sort_values("_offer_order").drop(columns=["_offer_order"])
    cohort_a = cohort_a.drop_duplicates(subset=["APPLICANT"], keep="first")

    # Fittable = Friday 9am AND (Wednesday 11am OR Thursday 11am). Exclude others.
    fittable = is_fittable_for_two_meetings(cohort_a)
    excluded_for_availability = cohort_a.loc[~fittable].copy()
    cohort_a = cohort_a.loc[fittable[fittable].index].copy()
    cohort_selected = cohort_a.head(args.max_size).copy()

    result = find_two_meetings_each(cohort_selected)
    cohort_label = (
        f"Cohort A + Either, 1st & 2nd choice (March 16–27 or Either), up to {args.max_size}"
    )
    report = format_two_meetings_each_report(
        result,
        cohort_name=cohort_label,
        excluded_for_availability=excluded_for_availability,
    )

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report, encoding="utf-8")
        print(f"Report written to {out}")
        base = out.with_suffix("")
        schedule_df = two_meetings_schedule_to_dataframe(result)
        if not schedule_df.empty:
            csv_path = base.with_suffix(".csv")
            schedule_df.to_csv(csv_path, index=False, encoding="utf-8")
            print(f"Schedule CSV (by person) written to {csv_path}")
        by_meeting_df = two_meetings_schedule_by_meeting_to_dataframe(result)
        if not by_meeting_df.empty:
            by_meeting_path = base.parent / f"{base.name}_by_meeting.csv"
            by_meeting_df.to_csv(by_meeting_path, index=False, encoding="utf-8")
            print(f"Schedule CSV (by meeting / groupings) written to {by_meeting_path}")
    else:
        print(report)
    return report


if __name__ == "__main__":
    main()
