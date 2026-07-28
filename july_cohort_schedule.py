#!/usr/bin/env python3
"""
July cohort — OPTION A: one session per meeting (maximize majority).

Needs:
- Friday orientation (Jul 31)
- Feedback next week (Aug 3–7)
- Feedback following week (Aug 10–14)
- A couple of office hours next week (Aug 3–7)

Applies free-text constraints from the form notes.
See july_cohort_schedule_split.py for OPTION B (Friday all-hands + split feedback).
"""
from __future__ import annotations

import csv
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent / "data" / "JULY_COHORT.csv"
REPORT_PATH = Path(__file__).resolve().parent / "reports" / "july_cohort_schedule.txt"
# Companion Option B (split sessions): july_cohort_schedule_split.py
# → reports/july_cohort_schedule_option_b_split.txt

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]


def parse_days(cell: str | None) -> set[str]:
    if not cell:
        return set()
    days: set[str] = set()
    for token in cell.split(","):
        normalized = token.strip().title()
        if normalized in WEEKDAYS:
            days.add(normalized)
    return days


def slot_label(col: str) -> str:
    if "[" in col and "]" in col:
        return col.split("[")[-1].split("]")[0]
    return col


def load_rows() -> tuple[list[dict[str, str]], list[str], str]:
    with DATA_PATH.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    avail_cols = [c for c in rows[0] if "Availability & Access" in c]
    flex_col = next(c for c in avail_cols if "[Flexible]" in c)
    nonflex = [c for c in avail_cols if c != flex_col]
    return rows, nonflex, flex_col


def base_available(row: dict[str, str], slot_col: str, day: str, flex_col: str) -> bool:
    days = parse_days(row.get(slot_col, "")) | parse_days(row.get(flex_col, ""))
    return day in days


def hard_available(
    row: dict[str, str],
    slot_col: str,
    day: str,
    flex_col: str,
    week: str,
) -> bool:
    """week: fri31 | aug3 | aug10"""
    name = row.get("Name (First, Last)", "")
    label = slot_label(slot_col)
    ok = base_available(row, slot_col, day, flex_col)

    if "Steven" in name and week == "fri31":
        return False
    if "Yerliza" in name and week == "aug3" and day in ("Wednesday", "Thursday", "Friday"):
        return False
    if "Elizabeth" in name and week == "aug10":
        return False
    if "Lidija" in name and week == "aug10" and day == "Monday":
        return False
    # Brandon: unavailable after 3pm ET → exclude 1–3pm PT (4–6pm ET)
    if "Brandon" in name and "1pm-3pm" in label:
        return False
    return ok


def brandon_note(slot_col: str) -> str:
    if "11am-1pm" in slot_label(slot_col):
        return " [Brandon: only until ~3pm ET; slot runs 2–4pm ET]"
    return ""


def names_for(rows: list[dict[str, str]], predicate) -> list[str]:
    return [r["Name (First, Last)"].strip() for r in rows if predicate(r)]


def missing_for(rows: list[dict[str, str]], yes_names: set[str]) -> list[str]:
    return [r["Name (First, Last)"].strip() for r in rows if r["Name (First, Last)"].strip() not in yes_names]


def build_report(rows: list[dict[str, str]], nonflex: list[str], flex_col: str) -> str:
    lines: list[str] = []
    n = len(rows)

    def p(s: str = "") -> None:
        lines.append(s)

    p("July Cohort — OPTION A: Single Session (majority)")
    p("=" * 50)
    p(f"Cohort size: {n}")
    p("Source: data/JULY_COHORT.csv")
    p("Companion: reports/july_cohort_schedule_option_b_split.txt (OPTION B — split sessions)")
    p("")
    p("Constraints applied from free-text notes:")
    p("  - Steven: unavailable Fri Jul 31 (cross-state travel)")
    p("  - Yerliza: unavailable Aug 5–7 (school event)")
    p("  - Elizabeth: unavailable Aug 10–14 (sorority work week)")
    p("  - Lidija: unavailable Mon Aug 10")
    p("  - Brandon: unavailable after 3pm ET (1–3pm PT slots excluded)")
    p("  - Hasibullah: prefers afternoons/evenings; morning form marks may be unreliable")
    p("")

    # 1) Orientation
    p("1) ORIENTATION — Friday, July 31, 2026")
    p("-" * 40)
    for col in nonflex:
        yes = names_for(rows, lambda r, c=col: hard_available(r, c, "Friday", flex_col, "fri31"))
        miss = missing_for(rows, set(yes))
        p(f"  {slot_label(col)}: {len(yes)}/{n}{brandon_note(col)}")
        p(f"    Missing: {', '.join(miss)}")
    p("")
    p("  RECOMMEND: Fri Jul 31, 9:00–11:00am PT / 12:00–2:00pm ET (~10/12)")
    p("  Why: ties best headcount and fully respects Brandon's 3pm ET cutoff.")
    p("  Alt: 11:00am–1:00pm PT / 2:00–4:00pm ET (also ~10/12; Brandon only partial).")
    p("  Likely cannot attend: Steven Corona; Ma. Nina Johnie Macali.")
    p("")

    # 2) Feedback week 1
    p("2) FEEDBACK #1 — week of August 3–7, 2026")
    p("-" * 40)
    ranked: list[tuple[int, str, str, list[str]]] = []
    for col in nonflex:
        for day in WEEKDAYS:
            yes = names_for(rows, lambda r, c=col, d=day: hard_available(r, c, d, flex_col, "aug3"))
            ranked.append((len(yes), day, col, yes))
    ranked.sort(key=lambda x: (-x[0], WEEKDAYS.index(x[1]), slot_label(x[2])))
    p("  Top options:")
    for count, day, col, yes in ranked[:6]:
        miss = missing_for(rows, set(yes))
        p(f"    {count}/{n}  {day} {slot_label(col)}{brandon_note(col)}")
        p(f"      Missing: {', '.join(miss)}")
    p("")
    p("  RECOMMEND: Thu Aug 6, 11:00am–1:00pm PT / 2:00–4:00pm ET (~11/12)")
    p("  Only miss: Yerliza Valenzuela (school event Aug 5–7).")
    p("  Safer-for-Brandon alt: Thu Aug 6, 9:00–11:00am PT (~9/12; misses Walter, Steven, Yerliza).")
    p("")

    # 3) Office hours
    p("3) OFFICE HOURS — week of August 3–7 (2 sessions)")
    p("-" * 40)
    p("  Goal: catch Yerliza (out Wed–Fri) and offer drop-in times off the feedback day.")
    for day in ("Monday", "Tuesday"):
        for col in nonflex:
            yes = names_for(rows, lambda r, c=col, d=day: hard_available(r, c, d, flex_col, "aug3"))
            if not any("Yerliza" in name for name in yes):
                continue
            if len(yes) < 8:
                continue
            miss = missing_for(rows, set(yes))
            p(f"    Candidate: {day} {slot_label(col)} — {len(yes)}/{n}; missing {', '.join(miss)}")
    p("")
    p("  RECOMMEND:")
    p("    OH A: Mon Aug 3, 11:00am–1:00pm PT / 2:00–4:00pm ET (~9/12, includes Yerliza)")
    p("    OH B: Tue Aug 4, 1:00–3:00pm PT / 4:00–6:00pm ET (~8/12, afternoon-friendly)")
    p("  Note: Brandon is excluded from OH B by his 3pm ET cutoff; point him to OH A.")
    p("")

    # 4) Feedback week 2
    p("4) FEEDBACK #2 — week of August 10–14, 2026")
    p("-" * 40)
    ranked2: list[tuple[int, str, str, list[str]]] = []
    for col in nonflex:
        for day in WEEKDAYS:
            yes = names_for(rows, lambda r, c=col, d=day: hard_available(r, c, d, flex_col, "aug10"))
            ranked2.append((len(yes), day, col, yes))
    ranked2.sort(key=lambda x: (-x[0], WEEKDAYS.index(x[1]), slot_label(x[2])))
    p("  Top options:")
    for count, day, col, yes in ranked2[:6]:
        miss = missing_for(rows, set(yes))
        p(f"    {count}/{n}  {day} {slot_label(col)}{brandon_note(col)}")
        p(f"      Missing: {', '.join(miss)}")
    p("")
    p("  RECOMMEND: Thu Aug 13, 11:00am–1:00pm PT / 2:00–4:00pm ET (~11/12)")
    p("  Only miss: Elizabeth Williams (unavailable all of Aug 10–14).")
    p("  Offer Elizabeth async/written feedback or a 1:1 outside that week.")
    p("")

    p("SUMMARY — OPTION A calendar")
    p("=" * 50)
    p("  Fri Jul 31   9:00–11:00am PT   Orientation         (~10/12)")
    p("  Mon Aug 3   11:00am–1:00pm PT  Office hours         (~9/12)")
    p("  Tue Aug 4    1:00–3:00pm PT    Office hours         (~8/12)")
    p("  Thu Aug 6   11:00am–1:00pm PT  Feedback session #1  (~11/12)")
    p("  Thu Aug 13  11:00am–1:00pm PT  Feedback session #2  (~11/12)")
    p("")
    p("People (name — email):")
    for r in rows:
        p(f"  - {r['Name (First, Last)'].strip()} — {r['Email Address']}")
    return "\n".join(lines) + "\n"


def main() -> None:
    rows, nonflex, flex_col = load_rows()
    report = build_report(rows, nonflex, flex_col)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(report)
    print(f"Wrote {REPORT_PATH}")


if __name__ == "__main__":
    main()
