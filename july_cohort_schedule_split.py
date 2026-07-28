#!/usr/bin/env python3
"""
July cohort — OPTION B: Friday all-hands + split feedback (~6 / ~6).

- Friday orientation stays one all-hands meeting (maximize attendance).
- Feedback meetings may be run twice as two groups of ~6 for fuller coverage.
- Optional small orientation make-up only for people who miss Friday.

Companion to Option A (single session throughout): july_cohort_schedule.py
"""
from __future__ import annotations

import csv
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent / "data" / "JULY_COHORT.csv"
REPORT_PATH = Path(__file__).resolve().parent / "reports" / "july_cohort_schedule_option_b_split.txt"

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
NAME_COL = "Name (First, Last)"
EMAIL_COL = "Email Address"


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
    name = row.get(NAME_COL, "")
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
    if "Brandon" in name and "1pm-3pm" in label:
        return False
    return ok


def attendees(
    rows: list[dict[str, str]],
    slot_col: str,
    day: str,
    flex_col: str,
    week: str,
) -> set[str]:
    return {
        r[NAME_COL].strip()
        for r in rows
        if hard_available(r, slot_col, day, flex_col, week)
    }


def assign_balanced(
    available_a: set[str],
    available_b: set[str],
) -> tuple[list[str], list[str], list[str], list[str]]:
    """
    Assign each covered person to exactly one of two sessions.
    People who can only make one session are locked there; flexible people
    fill toward equal group sizes (~6 / ~6).
    """
    only_a = available_a - available_b
    only_b = available_b - available_a
    both = available_a & available_b
    session_a = sorted(only_a)
    session_b = sorted(only_b)
    for name in sorted(both):
        if len(session_a) <= len(session_b):
            session_a.append(name)
        else:
            session_b.append(name)
    return sorted(session_a), sorted(session_b), sorted(only_a), sorted(only_b)


def pair_from_slots(
    rows: list[dict[str, str]],
    flex_col: str,
    *,
    day1: str,
    col1: str,
    week1: str,
    day2: str,
    col2: str,
    week2: str,
) -> dict:
    a1 = attendees(rows, col1, day1, flex_col, week1)
    a2 = attendees(rows, col2, day2, flex_col, week2)
    s1, s2, only1, only2 = assign_balanced(a1, a2)
    all_names = {r[NAME_COL].strip() for r in rows}
    uncovered = sorted(all_names - a1 - a2)
    return {
        "union": len(a1 | a2),
        "label1": slot_label(col1),
        "label2": slot_label(col2),
        "session1": s1,
        "session2": s2,
        "only1": only1,
        "only2": only2,
        "uncovered": uncovered,
    }


def _roster_lines(names: list[str], only: list[str] | None = None) -> list[str]:
    only = only or []
    return [f"    - {name}{' *' if name in only else ''}" for name in names]


def build_report(rows: list[dict[str, str]], nonflex: list[str], flex_col: str) -> str:
    lines: list[str] = []
    n = len(rows)
    col_9am, col_11am, _col_1pm = nonflex

    def p(s: str = "") -> None:
        lines.append(s)

    p("July Cohort — OPTION B: Friday All-Hands + Split Feedback")
    p("=" * 55)
    p(f"Cohort size: {n}")
    p("Source: data/JULY_COHORT.csv")
    p("Companion to: reports/july_cohort_schedule.txt (OPTION A — single session throughout)")
    p("")
    p("Model:")
    p("  - Friday orientation = ALL-HANDS (one meeting, as many people as possible)")
    p("  - Feedback meetings = TWO groups of ~6 (split sessions for fuller coverage)")
    p("  - Optional small Friday make-up only for people who cannot attend all-hands")
    p("")
    p("Constraints applied from free-text notes (same as Option A):")
    p("  - Steven: unavailable Fri Jul 31 (cross-state travel)")
    p("  - Yerliza: unavailable Aug 5–7 (school event)")
    p("  - Elizabeth: unavailable Aug 10–14 (sorority work week)")
    p("  - Lidija: unavailable Mon Aug 10")
    p("  - Brandon: unavailable after 3pm ET (1–3pm PT slots excluded)")
    p("  - Hasibullah: prefers afternoons/evenings; morning form marks may be unreliable")
    p("")

    # 1) Friday all-hands
    all_hands = sorted(attendees(rows, col_9am, "Friday", flex_col, "fri31"))
    missing_friday = sorted({r[NAME_COL].strip() for r in rows} - set(all_hands))
    p("1) ORIENTATION — Friday ALL-HANDS (Jul 31)")
    p("-" * 40)
    p(f"  RECOMMEND: Fri Jul 31, 9:00–11:00am PT / 12:00–2:00pm ET  ({len(all_hands)}/{n})")
    p("  One session for everyone who can make it — not a split.")
    p(f"  Attending ({len(all_hands)}):")
    lines.extend(_roster_lines(all_hands))
    p(f"  Cannot attend ({len(missing_friday)}): {', '.join(missing_friday)}")
    p("    - Steven: travel that day")
    p("    - Nina: never selected Friday on the form")
    p("")
    p("  Optional make-up (small; not a second half of the cohort):")
    p("    Mon Aug 3, 9:00–11:00am PT / 12:00–2:00pm ET — covers both Steven & Nina")
    p("    (Invite only Friday missers, or anyone who wants a refresher.)")
    p("")

    # 2) Feedback week 1 — true 6+6 split
    fb1 = pair_from_slots(
        rows,
        flex_col,
        day1="Monday",
        col1=col_11am,
        week1="aug3",
        day2="Thursday",
        col2=col_11am,
        week2="aug3",
    )
    p("2) FEEDBACK #1 — week of August 3–7 (TWO groups of ~6)")
    p("-" * 40)
    p(f"  Coverage: {fb1['union']}/{n} — each person assigned to one group")
    p("  Monday group catches Yerliza (out Wed–Fri that week).")
    p(f"  Group A — Mon Aug 3, 11:00am–1:00pm PT / 2:00–4:00pm ET  ({len(fb1['session1'])} people)")
    lines.extend(_roster_lines(fb1["session1"], fb1["only1"]))
    p(f"  Group B — Thu Aug 6, 11:00am–1:00pm PT / 2:00–4:00pm ET  ({len(fb1['session2'])} people)")
    lines.extend(_roster_lines(fb1["session2"], fb1["only2"]))
    p("  Still uncovered: (none)")
    p("  (* = can only make this group of the pair)")
    p("")

    # 3) Feedback week 2 — same pattern
    fb2 = pair_from_slots(
        rows,
        flex_col,
        day1="Monday",
        col1=col_11am,
        week1="aug10",
        day2="Thursday",
        col2=col_11am,
        week2="aug10",
    )
    p("3) FEEDBACK #2 — week of August 10–14 (TWO groups of ~6)")
    p("-" * 40)
    p(f"  Coverage: {fb2['union']}/{n} — same Mon/Thu pattern for consistency")
    p(f"  Group A — Mon Aug 10, 11:00am–1:00pm PT / 2:00–4:00pm ET  ({len(fb2['session1'])} people)")
    lines.extend(_roster_lines(fb2["session1"], fb2["only1"]))
    p(f"  Group B — Thu Aug 13, 11:00am–1:00pm PT / 2:00–4:00pm ET  ({len(fb2['session2'])} people)")
    lines.extend(_roster_lines(fb2["session2"], fb2["only2"]))
    if fb2["uncovered"]:
        p(f"  Still uncovered: {', '.join(fb2['uncovered'])}")
        p("  Elizabeth is out all of Aug 10–14 — no split can include her that week.")
        p("  Offer async/written feedback or a 1:1 outside that week.")
    p("  (* = can only make this group of the pair)")
    p("")

    p("4) OFFICE HOURS — week of August 3–7")
    p("-" * 40)
    p("  Less critical under Option B (split feedback already covers 12/12).")
    p("  Optional drop-in:")
    p("    Tue Aug 4, 1:00–3:00pm PT / 4:00–6:00pm ET (afternoon-friendly for Hasibullah)")
    p("")

    p("SUMMARY — OPTION B calendar")
    p("=" * 55)
    p("  Fri Jul 31   9:00–11:00am PT   Orientation ALL-HANDS      (~10/12)")
    p("  Mon Aug 3    9:00–11:00am PT   Optional orient. make-up   (Steven, Nina)")
    p("  Mon Aug 3   11:00am–1:00pm PT  Feedback #1 Group A        (6)")
    p("  Thu Aug 6   11:00am–1:00pm PT  Feedback #1 Group B        (6)")
    p("  Mon Aug 10  11:00am–1:00pm PT  Feedback #2 Group A        (6)")
    p("  Thu Aug 13  11:00am–1:00pm PT  Feedback #2 Group B        (5)")
    p("  Optional: Tue Aug 4  1:00–3:00pm PT  Office hours")
    p("")
    p("OPTION A vs OPTION B (quick compare)")
    p("-" * 40)
    p("  Orientation:   both use Friday all-hands (~10/12); B adds optional make-up")
    p("  Feedback #1:   A one session ~11/12 | B two groups of 6 → 12/12")
    p("  Feedback #2:   A one session ~11/12 | B two groups → 11/12 (Elizabeth still out)")
    p("  Tradeoff: Option B = two extra feedback sessions to facilitate.")
    p("")
    p("People (name — email):")
    for r in rows:
        p(f"  - {r[NAME_COL].strip()} — {r[EMAIL_COL]}")
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
