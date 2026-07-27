#!/usr/bin/env python3
"""
Cohort 3 scheduling from form-only data.

Finds:
- One anchor meeting (best day/time by availability)
- One second meeting (best other day/time among anchor attendees)

Assumes everyone in cohort_3_form_results.csv is selected.
"""
from pathlib import Path
import argparse
import pandas as pd

from load_form_data import parse_days, WEEKDAYS

DATA_PATH = Path(__file__).resolve().parent / "data" / "cohort_3_availability_only.csv"


def _slot_columns(df: pd.DataFrame) -> tuple[list[str], str | None]:
    availability = [c for c in df.columns if "Which times generally work best for you?" in c]
    flex = next((c for c in availability if "[Flexible]" in c), None)
    nonflex = [c for c in availability if c != flex]
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


def compute_two_meeting_plan(df: pd.DataFrame) -> dict:
    nonflex, flex = _slot_columns(df)
    if not nonflex:
        return {"ok": False, "reason": "No availability columns found."}

    anchor_options = []
    for col in nonflex:
        for day in WEEKDAYS:
            count = sum(1 for _, row in df.iterrows() if _available(row, col, day, flex))
            anchor_options.append((count, day, col))
    anchor_options.sort(key=lambda x: (-x[0], x[1], _slot_label(x[2])))
    anchor_count, anchor_day, anchor_col = anchor_options[0]

    anchor_mask = df.apply(lambda r: _available(r, anchor_col, anchor_day, flex), axis=1)
    anchor_df = df.loc[anchor_mask].copy()
    if len(anchor_df) == 0:
        return {"ok": False, "reason": "No anchor attendees found."}

    second_options = []
    for col in nonflex:
        for day in WEEKDAYS:
            if day == anchor_day:
                continue
            count = sum(1 for _, row in anchor_df.iterrows() if _available(row, col, day, flex))
            second_options.append((count, day, col))
    second_options.sort(key=lambda x: (-x[0], x[1], _slot_label(x[2])))
    second_count, second_day, second_col = second_options[0]

    both_mask = anchor_df.apply(lambda r: _available(r, second_col, second_day, flex), axis=1)
    both_df = anchor_df.loc[both_mask].copy()
    excluded_df = anchor_df.loc[~both_mask].copy()

    return {
        "ok": True,
        "anchor_count": anchor_count,
        "anchor_day": anchor_day,
        "anchor_col": anchor_col,
        "anchor_label": _slot_label(anchor_col),
        "anchor_df": anchor_df,
        "second_count": second_count,
        "second_day": second_day,
        "second_col": second_col,
        "second_label": _slot_label(second_col),
        "both_df": both_df,
        "excluded_df": excluded_df,
        "anchor_options": anchor_options,
        "second_options": second_options,
    }


def _name_col(df: pd.DataFrame) -> str:
    if "APPLICANT" in df.columns:
        return "APPLICANT"
    if "Name (First, Last)" in df.columns:
        return "Name (First, Last)"
    return df.columns[0]


def format_report(df: pd.DataFrame, plan: dict) -> str:
    if not plan.get("ok"):
        return f"Cohort 3: {plan.get('reason', 'No plan found.')}\n"
    name_col = _name_col(df)
    email_col = "Email Address" if "Email Address" in df.columns else "EMAIL"
    lines = [
        "Two meetings per week — Cohort 3 (form-only)",
        "=" * 52,
        "",
        f"Cohort size: {len(df)}",
        f"Anchor: {plan['anchor_day']} at {plan['anchor_label']} ({plan['anchor_count']}/{len(df)})",
        f"Second: {plan['second_day']} at {plan['second_label']} ({plan['second_count']}/{len(plan['anchor_df'])} of anchor attendees)",
        f"Can attend both meetings: {len(plan['both_df'])}/{len(df)}",
        "",
        "Top 5 anchor options:",
    ]
    for count, day, col in plan["anchor_options"][:5]:
        lines.append(f"  - {day} at {_slot_label(col)}: {count}/{len(df)}")
    lines += ["", "Top 5 second options (within anchor attendees):"]
    for count, day, col in plan["second_options"][:5]:
        lines.append(f"  - {day} at {_slot_label(col)}: {count}/{len(plan['anchor_df'])}")
    lines += ["", "People who can attend both meetings:"]
    for _, row in plan["both_df"].iterrows():
        lines.append(f"  - {row.get(name_col, '?')} — {row.get(email_col, '')}")
    if len(plan["excluded_df"]) > 0:
        lines += ["", "Anchor attendees missing second meeting:"]
        for _, row in plan["excluded_df"].iterrows():
            lines.append(f"  - {row.get(name_col, '?')} — {row.get(email_col, '')}")
    return "\n".join(lines)


def to_by_person_csv(plan: dict) -> pd.DataFrame:
    if not plan.get("ok"):
        return pd.DataFrame(columns=["Name", "Email", "Anchor", "Second", "Status"])
    df = plan["anchor_df"].copy()
    name_col = _name_col(df)
    email_col = "Email Address" if "Email Address" in df.columns else "EMAIL"
    can_second = set(plan["both_df"].index)
    rows = []
    for idx, row in df.iterrows():
        rows.append(
            {
                "Name": row.get(name_col, "?"),
                "Email": row.get(email_col, ""),
                "Anchor": f"{plan['anchor_day']} at {plan['anchor_label']}",
                "Second": f"{plan['second_day']} at {plan['second_label']}" if idx in can_second else "",
                "Status": "both meetings" if idx in can_second else "anchor only",
            }
        )
    return pd.DataFrame(rows)


def to_by_meeting_csv(plan: dict, full_df: pd.DataFrame) -> pd.DataFrame:
    if not plan.get("ok"):
        return pd.DataFrame(columns=["Meeting", "Day & Time", "Name", "Email"])
    name_col = _name_col(full_df)
    email_col = "Email Address" if "Email Address" in full_df.columns else "EMAIL"
    rows = []
    for _, row in plan["anchor_df"].iterrows():
        rows.append(
            {
                "Meeting": "Anchor",
                "Day & Time": f"{plan['anchor_day']} at {plan['anchor_label']}",
                "Name": row.get(name_col, "?"),
                "Email": row.get(email_col, ""),
            }
        )
    for _, row in plan["both_df"].iterrows():
        rows.append(
            {
                "Meeting": "Second",
                "Day & Time": f"{plan['second_day']} at {plan['second_label']}",
                "Name": row.get(name_col, "?"),
                "Email": row.get(email_col, ""),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Cohort 3: find anchor + one second weekly meeting.")
    parser.add_argument("-o", "--output", metavar="FILE", help="Write report to FILE")
    args = parser.parse_args()

    df = pd.read_csv(DATA_PATH, encoding="utf-8")
    plan = compute_two_meeting_plan(df)
    report = format_report(df, plan)

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report, encoding="utf-8")
        print(f"Report written to {out}")
        base = out.with_suffix("")
        to_by_person_csv(plan).to_csv(base.with_suffix(".csv"), index=False, encoding="utf-8")
        print(f"Schedule CSV (by person) written to {base.with_suffix('.csv')}")
        by_meeting = to_by_meeting_csv(plan, df)
        by_meeting_path = base.parent / f"{base.name}_by_meeting.csv"
        by_meeting.to_csv(by_meeting_path, index=False, encoding="utf-8")
        print(f"Schedule CSV (by meeting) written to {by_meeting_path}")
    else:
        print(report)


if __name__ == "__main__":
    main()
