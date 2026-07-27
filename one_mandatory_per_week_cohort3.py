#!/usr/bin/env python3
"""
Cohort 3: choose one mandatory session per week.

Week 1 window: Monday-Friday
Week 2 window: Monday-Thursday (holiday week)
"""
from pathlib import Path
import argparse
import pandas as pd

from load_form_data import parse_days

DATA_PATH = Path(__file__).resolve().parent / "data" / "cohort_3_availability_only.csv"
DAYS_WEEK_1 = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
DAYS_WEEK_2 = ["Monday", "Tuesday", "Wednesday", "Thursday"]


def _slot_cols(df: pd.DataFrame) -> tuple[list[str], str | None]:
    cols = [c for c in df.columns if "Availability & Access" in c]
    flex = next((c for c in cols if "[Flexible]" in c), None)
    nonflex = [c for c in cols if c != flex]
    return nonflex, flex


def _slot_label(col: str) -> str:
    if "[" in col and "]" in col:
        return col.split("[")[-1].split("]")[0]
    return col


def _available(row: pd.Series, slot_col: str, day: str, flex_col: str | None) -> bool:
    days = parse_days(row.get(slot_col, ""))
    if flex_col and slot_col != flex_col:
        days = days | parse_days(row.get(flex_col, ""))
    return day in days


def _best_slot(
    df: pd.DataFrame,
    allowed_days: list[str],
    preferred_day: str | None = None,
) -> tuple[str, str, int, list[tuple[int, str, str]]]:
    nonflex, flex = _slot_cols(df)
    ranked: list[tuple[int, str, str]] = []
    for slot_col in nonflex:
        for day in allowed_days:
            count = sum(1 for _, row in df.iterrows() if _available(row, slot_col, day, flex))
            ranked.append((count, day, slot_col))
    ranked.sort(key=lambda x: (-x[0], x[1], _slot_label(x[2])))
    best_count, best_day, best_col = ranked[0]
    if preferred_day:
        # If the preferred day ties at top count, use it.
        top_count = best_count
        for count, day, col in ranked:
            if count < top_count:
                break
            if day == preferred_day:
                best_count, best_day, best_col = count, day, col
                break
    return best_day, best_col, best_count, ranked


def _missing_people(df: pd.DataFrame, day: str, slot_col: str) -> pd.DataFrame:
    nonflex, flex = _slot_cols(df)
    _ = nonflex
    mask = df.apply(lambda r: _available(r, slot_col, day, flex), axis=1)
    return df.loc[~mask].copy()


def build_report(df: pd.DataFrame, week2_preferred_day: str | None = None) -> str:
    n = len(df)
    name_col = "Name (First, Last)" if "Name (First, Last)" in df.columns else df.columns[0]
    email_col = "Email Address" if "Email Address" in df.columns else "EMAIL"

    d1, c1, n1, ranked1 = _best_slot(df, DAYS_WEEK_1)
    d2, c2, n2, ranked2 = _best_slot(df, DAYS_WEEK_2, preferred_day=week2_preferred_day)
    miss1 = _missing_people(df, d1, c1)
    miss2 = _missing_people(df, d2, c2)

    lines = [
        "Cohort 3 — One Mandatory Session Per Week",
        "=" * 45,
        f"Cohort size: {n}",
        "",
        "Week 1 (Mon-Fri):",
        f"  Best slot: {d1} at {_slot_label(c1)}  ({n1}/{n})",
        "",
        "Week 2 (Mon-Thu, holiday week):",
        f"  Best slot: {d2} at {_slot_label(c2)}  ({n2}/{n})",
        "",
        "Top 5 options — Week 1:",
    ]
    for count, day, col in ranked1[:5]:
        lines.append(f"  - {day} at {_slot_label(col)}: {count}/{n}")
    lines += ["", "Top 5 options — Week 2:"]
    for count, day, col in ranked2[:5]:
        lines.append(f"  - {day} at {_slot_label(col)}: {count}/{n}")

    lines += ["", "Not available for Week 1 best slot:"]
    for _, row in miss1.iterrows():
        lines.append(f"  - {row.get(name_col, '?')} — {row.get(email_col, '')}")
    lines += ["", "Not available for Week 2 best slot:"]
    for _, row in miss2.iterrows():
        lines.append(f"  - {row.get(name_col, '?')} — {row.get(email_col, '')}")
    return "\n".join(lines)


def build_csv(df: pd.DataFrame, week2_preferred_day: str | None = None) -> pd.DataFrame:
    d1, c1, n1, _ = _best_slot(df, DAYS_WEEK_1)
    d2, c2, n2, _ = _best_slot(df, DAYS_WEEK_2, preferred_day=week2_preferred_day)
    return pd.DataFrame(
        [
            {"Week": "Week 1 (Mon-Fri)", "Day": d1, "Time": _slot_label(c1), "Available": n1, "Cohort Size": len(df)},
            {"Week": "Week 2 (Mon-Thu)", "Day": d2, "Time": _slot_label(c2), "Available": n2, "Cohort Size": len(df)},
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Pick one mandatory slot per week for cohort 3.")
    parser.add_argument("-o", "--output", metavar="FILE", help="Write report to FILE")
    parser.add_argument(
        "--week2-prefer-day",
        choices=DAYS_WEEK_2,
        help="If tied at top count in Week 2, prefer this day (e.g. Wednesday).",
    )
    args = parser.parse_args()

    df = pd.read_csv(DATA_PATH, encoding="utf-8")
    report = build_report(df, week2_preferred_day=args.week2_prefer_day)
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report, encoding="utf-8")
        print(f"Report written to {out}")
        base = out.with_suffix("")
        csv_path = base.with_suffix(".csv")
        build_csv(df, week2_preferred_day=args.week2_prefer_day).to_csv(csv_path, index=False, encoding="utf-8")
        print(f"Summary CSV written to {csv_path}")
    else:
        print(report)


if __name__ == "__main__":
    main()
