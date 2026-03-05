# How the Three-Meetings Schedule Works

A short, team-friendly explanation of how we assign everyone to exactly 3 meetings per week (on 3 different days) and how we select who is in the cohort.

---

## Goal

- **Each person in the cohort** attends **exactly 3 meetings per week**.
- **No one** has 2 meetings on the **same day**.
- **Cohort size:** Up to **21 people**. We select by availability: only people who can fit into three meetings are included. **1st choice is preferred**, then 2nd choice.
- The **company** hosts **5 meetings** per week: one Friday (full cohort) + four weekdays (Mon–Thu at the same time).

---

## Who’s in the Pool and Who Gets Selected

1. **Pool:** Only people in **Cohort A or Either** (March 16–27 or “Either”). People who chose only March 30–April 10 are not in this schedule. We consider **OFFER = 1st choice** and **OFFER = 2nd choice** (2nd choice is included to help reach the target size).

2. **Selection by availability:** We only **include** people who can actually fit into three meetings:
   - They must be available for **Friday 9am–11am PT** (the full-cohort meeting).
   - They must have **at least 2 weekdays** (Mon–Thu) available for **11am–1pm PT** (so we can assign them to two weekday meetings).
   - If someone can’t meet both of these, they are **not considered for this cohort** (we don’t schedule them).

3. **Preference and cap:** From everyone who fits, we take people in order: **all 1st choice first**, then **2nd choice**, until we reach **21 people** (or we run out of fittable people). So we never choose a 2nd-choice person over a 1st-choice person when both fit.

---

## The Meetings

1. **Meeting 1 — same for everyone:**  
   **Friday, 9am–11am PT.**  
   Everyone in the selected cohort attends this meeting.

2. **Meetings 2–5 — two per person:**  
   We run **four more meetings** at **11am–1pm PT** on:
   - Monday, Tuesday, Wednesday, Thursday  

   Each person is assigned to **exactly 2** of these 4 days. So each person’s week is:
   - **Friday** (full cohort) + **2 weekdays** (their assigned days).

3. **No double-booking:** We only assign someone to a weekday if their form said they’re available that day for 11am–1pm PT (or “Flexible” for that day). We never put 2 meetings on the same day for the same person.

---

## The Algorithm (Simple Version)

**Step 1 — Build the pool.**  
Take everyone in Cohort A or Either with OFFER = 1st choice or 2nd choice. Sort so 1st choice comes before 2nd choice. Remove duplicates (one row per person).

**Step 2 — Who fits into 3 meetings?**  
For each person in the pool:
- Can they attend **Friday 9am–11am PT**?
- Do they have **at least 2 weekdays** (Mon–Thu) available for **11am–1pm PT**?  
If both are yes, they are **fittable**. If not, they are **not** included in this cohort.

**Step 3 — Select up to 21.**  
Take the first **21 fittable people** in order (1st choice first, then 2nd). If fewer than 21 are fittable, the cohort is smaller (e.g. 18).

**Step 4 — Assign 2 weekdays to each selected person.**  
For everyone in the selected cohort, assign **exactly 2** weekdays from the days they said they’re available. We **balance** so no single weekday meeting is overloaded: when we assign a person, we give them two days that currently have the **smallest** number of people already assigned.

**Step 5 — Build the schedule.**  
- **Meeting 1:** Friday 9am — everyone in the cohort.  
- **Meetings 2–5:** Monday, Tuesday, Wednesday, Thursday at 11am — each meeting is the list of people assigned to that day.

Result: **everyone in the cohort** has **3 meetings on 3 different days**, and the company runs **5 meetings** total.

---

## One-Sentence Summary

We take 1st and 2nd choice from Cohort A/Either, keep only people who can do Friday 9am plus at least two weekdays at 11am, select up to 21 (1st choice first), then assign each person to two weekdays so everyone has three meetings on three different days.

---

## For Your Meeting

You can say:

- “We **target up to 21 people**. We include **1st and 2nd choice** from Cohort A/Either, but we **only select people who can fit into three meetings** (Friday 9am plus two other weekdays). If they can’t fit, they’re not in this cohort.”
- “**1st choice is preferred**: we fill the cohort with 1st choice first, then add 2nd choice until we hit 21 or run out of fittable people.”
- “Each person gets **exactly 3 meetings per week** on **3 different days**. Friday 9am is the all-hands; the other two are on two weekdays at 11am, chosen from their availability and balanced across days.”
