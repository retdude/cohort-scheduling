#!/usr/bin/env python3
"""
Clean up the four availability time-slot column names in form_results.csv.
Replaces long Google Form headers with short, distinct names.
"""
import csv
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
CSV_PATH = DATA_DIR / "form_results.csv"

# Map substring that identifies each column -> clean header name
AVAILABILITY_COLUMN_RENAMES = {
    "[9am-11am (PT) / 12pm-2pm (ET)]": "Times_9am-11am_PT",
    "[11am-1pm (PT) / 2pm-4pm (ET)]": "Times_11am-1pm_PT",
    "[1pm-3pm (PT) / 4pm -6pm (ET)]": "Times_1pm-3pm_PT",
    "[Flexible]": "Times_Flexible",
}


def clean_header(name: str) -> str:
    """If this is one of the four availability columns, return the short name; else return name unchanged."""
    for key, new_name in AVAILABILITY_COLUMN_RENAMES.items():
        if key in name:
            return new_name
    return name


def main() -> None:
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        print("CSV is empty.")
        return

    headers = rows[0]
    cleaned = [clean_header(h) for h in headers]
    rows[0] = cleaned

    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    print("Cleaned column names:")
    for old, new in zip(headers, cleaned):
        if old != new:
            print(f"  -> {new}")


if __name__ == "__main__":
    main()
