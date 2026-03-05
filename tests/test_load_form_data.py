"""
Unit tests for load_form_data: name parsing, day parsing, common slots, who's missing.
"""
import pandas as pd
import pytest

# Import after path is set; run from project root as: pytest tests/
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from load_form_data import (
    parse_name_to_last_first,
    parse_days,
    find_common_slots,
    who_is_missing,
    additional_details_mention_day,
    WEEKDAYS,
    TIME_SLOT_COLUMNS,
    ADDITIONAL_DETAILS_COL,
)


class TestParseNameToLastFirst:
    def test_asterisk_stripped(self):
        assert parse_name_to_last_first("*Kerrie Noble*") == "Noble, Kerrie"
        assert parse_name_to_last_first("*Hugo Pailthorpe*") == "Pailthorpe, Hugo"

    def test_first_last_becomes_last_first(self):
        assert parse_name_to_last_first("Kerrie Noble") == "Noble, Kerrie"
        assert parse_name_to_last_first("Walter Lloyd") == "Lloyd, Walter"

    def test_comma_first_last_becomes_last_first(self):
        assert parse_name_to_last_first("Rebecca, Gonzalez") == "Gonzalez, Rebecca"
        assert parse_name_to_last_first("Krishi, Chand") == "Chand, Krishi"

    def test_na_or_empty(self):
        assert parse_name_to_last_first("") == ""
        assert pd.isna(parse_name_to_last_first(pd.NA)) or parse_name_to_last_first(pd.NA) is pd.NA

    def test_single_word_unchanged(self):
        assert parse_name_to_last_first("Madonna") == "Madonna"


class TestParseDays:
    def test_normal_comma_separated(self):
        assert parse_days("Monday, Tuesday, Friday") == {"Monday", "Tuesday", "Friday"}
        assert parse_days("Friday") == {"Friday"}

    def test_ignores_na_no(self):
        assert parse_days("N/A") == set()
        assert parse_days("No") == set()
        assert parse_days("N/A, Monday") == {"Monday"}

    def test_empty_or_na(self):
        assert parse_days("") == set()
        assert parse_days(pd.NA) == set()

    def test_normalizes_to_title_case(self):
        assert parse_days("monday, FRIDAY") == {"Monday", "Friday"}


class TestFindCommonSlots:
    def test_everyone_same_day(self):
        df = pd.DataFrame({
            "Times_9am-11am_PT": ["Monday", "Monday", "Monday"],
            "Times_11am-1pm_PT": ["Tuesday", "Tuesday", "Tuesday"],
            "Times_1pm-3pm_PT": ["Friday", "Friday", "Friday"],
            "Times_Flexible": ["", "", ""],
        })
        common = find_common_slots(df)
        assert common["Times_9am-11am_PT"] == ["Monday"]
        assert common["Times_11am-1pm_PT"] == ["Tuesday"]
        assert common["Times_1pm-3pm_PT"] == ["Friday"]

    def test_no_common_day(self):
        df = pd.DataFrame({
            "Times_9am-11am_PT": ["Monday", "Tuesday", "Wednesday"],
            "Times_11am-1pm_PT": ["Monday", "Tuesday", "Friday"],
            "Times_1pm-3pm_PT": ["Monday", "Tuesday", "Thursday"],
            "Times_Flexible": ["", "", ""],
        })
        common = find_common_slots(df)
        assert common["Times_9am-11am_PT"] == []

    def test_flexible_expands_availability(self):
        # Person 1: only Monday in slot; Person 2: only Monday in Flexible
        df = pd.DataFrame({
            "Times_9am-11am_PT": ["Monday", ""],
            "Times_11am-1pm_PT": ["", ""],
            "Times_1pm-3pm_PT": ["", ""],
            "Times_Flexible": ["", "Monday"],
        })
        common = find_common_slots(df, treat_flexible_as_any_slot=True)
        assert "Monday" in common["Times_9am-11am_PT"]


class TestWhoIsMissing:
    def test_returns_non_available(self):
        df = pd.DataFrame({
            "APPLICANT": ["Alice", "Bob", "Carol"],
            "Times_9am-11am_PT": ["Monday", "Tuesday", "Monday"],
            "Times_Flexible": ["", "", ""],
        })
        missing = who_is_missing(df, "Monday", "Times_9am-11am_PT")
        assert len(missing) == 1
        assert missing.iloc[0]["APPLICANT"] == "Bob"

    def test_empty_when_all_available(self):
        df = pd.DataFrame({
            "APPLICANT": ["Alice", "Bob"],
            "Times_9am-11am_PT": ["Monday", "Monday"],
            "Times_Flexible": ["", ""],
        })
        missing = who_is_missing(df, "Monday", "Times_9am-11am_PT")
        assert len(missing) == 0


class TestAdditionalDetailsMentionDay:
    def test_mentions_day(self):
        assert additional_details_mention_day("Not free on Tuesday", "Tuesday") is True
        assert additional_details_mention_day("only after 4pm Monday", "Monday") is True

    def test_does_not_mention(self):
        assert additional_details_mention_day("I am flexible", "Tuesday") is False
        assert additional_details_mention_day("", "Monday") is False
        assert additional_details_mention_day("N/A", "Friday") is False
