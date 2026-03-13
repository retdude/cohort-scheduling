# Meeting Time Scheduling

Finds a day and time when as many people as possible (ideally everyone) in each cohort can attend, using Google Form availability responses and a candidates list.

## What it does

- **Loads** `data/form_results.csv` (form responses) and `data/candidates.csv` (candidate list), merged by normalized name (form data wins on conflicts).
- **Splits** respondents into two cohorts by COHORT:
  - **Cohort A:** March 16–27 2026 or Either  
  - **Cohort B:** March 30–April 10 2026 or Either  
- **Finds** for each cohort:
  - Days when **everyone** is available for each time slot (if any).
  - Best (day, time) options by head count when no slot works for everyone.
- **Recommends** one slot per cohort, lists who’s **not** available, and flags people whose “additional details” mention that day (for you to double-check).
- **Three meetings per person** (`three_meetings.py`): For Cohort A + Either (1st & 2nd choice), selects up to 21 people who can fit into exactly 3 meetings per week (Friday 9am full cohort + 2 other weekdays at 11am). No one has 2 meetings on the same day. Selection is by availability; 1st choice preferred, then 2nd. See `docs/THREE_MEETINGS_ALGORITHM.md` for the algorithm.

## Data files

- **`data/form_results.csv`** – Export from the Google Form. Must include at least: Timestamp, email, applicant name, COHORT, Location, and the four time-slot columns (`Times_9am-11am_PT`, `Times_11am-1pm_PT`, `Times_1pm-3pm_PT`, `Times_Flexible`). Names can be “First Last” or “First, Last”; asterisks (e.g. `*Name*`) are stripped for accessibility.
- **`data/candidates.csv`** – Must include APPLICANT and EMAIL; can include COHORT, FORM FILLED, OFFER, NOTES. Merged with form by **name** (normalized to “Last, First”).

## How to run

### One-time setup

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Generate the report

**Print to terminal:**

```bash
python load_form_data.py
```

**Write to a file:**

```bash
python load_form_data.py --output reports/scheduling_report.txt
```

**Write to a dated file in a directory:**

```bash
python load_form_data.py --report-dir reports
# Creates reports/scheduling_report_YYYY-MM-DD.txt
```

**Three meetings per person (Cohort A + Either, up to 21 people):**

```bash
python three_meetings.py                           # print to terminal
python three_meetings.py -o reports/three_meetings_schedule.txt
python three_meetings.py -n 21 -o reports/three_meetings_schedule.txt   # cap at 21 (default)
```

### Run tests

```bash
pytest tests/ -v
```

## Output explained

- **“Days when EVERYONE is available”** – For each time slot, the list of weekdays that appear in every respondent’s availability. If “(none)”, no single day works for everyone in that slot.
- **“Best (day, time) options”** – Table of (time slot, day, count) sorted by how many people can make it. Use this when there’s no perfect slot.
- **“Recommendations”** – One chosen slot per cohort (the best head count), plus:
  - **Not available this slot** – Names and emails of people who didn’t select that day for that slot (or Flexible).
  - **Additional-details mention this day** – People who mentioned that weekday in their free-text notes; review in case of partial availability (e.g. “only after 4pm on Friday”).

## Project layout

- `load_form_data.py` – Load, merge, cohort split, common-slot logic, recommendations, three-meetings assignment, and report builders.
- `three_meetings.py` – Three meetings per person (Fri + 2 weekdays), 1st/2nd choice, cap 21, selection by availability.
- `clean_availability_columns.py` – One-off script to clean the four time-slot column names in the form CSV.
- `data/form_results.csv` – Form export.
- `data/candidates.csv` – Candidates list.
- `docs/THREE_MEETINGS_ALGORITHM.md` – Plain-language explanation of the three-meetings algorithm.
- `tests/test_load_form_data.py` – Unit tests for name/day parsing and scheduling logic.
- `requirements.txt` – pandas, pytest.
