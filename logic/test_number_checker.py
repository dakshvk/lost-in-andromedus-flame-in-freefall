# Written with SI assistance (Muse), reviewed by Paridhi Singh
"""Unit tests for the Lane B number checker (team doc, Part 4, Step 4.4).

Run from inside logic/:  python3 -m unittest test_number_checker -v
"""

import unittest

from number_checker import check_answer_numbers

STATS = {"total_tests": 129, "o2_min": 13.6, "o2_max": 22.2, "rows_above_21": 18}

EVIDENCE = [
    {"test_id": "B1", "material": "PMMA", "oxygen_pct": "22.2",
     "airflow_cm_s": "5", "airflow_end_cm_s": ""},
    {"test_id": "T25", "material": "SIBAL", "oxygen_pct": "20.8",
     "airflow_cm_s": "5", "airflow_end_cm_s": "2.5"},
    {"test_id": "F1", "material": "Nomex", "oxygen_pct": "22.2",
     "airflow_cm_s": "9.5", "airflow_end_cm_s": ""},
]


class TestNumberChecker(unittest.TestCase):
    def test_accept_answer_using_only_allowed_numbers(self):
        sentence = (
            "22.2% oxygen is inside the tested range (13.6–22.2% oxygen, "
            "129 BASS-II tests), so the rows below are direct evidence."
        )
        self.assertTrue(check_answer_numbers(sentence, EVIDENCE, STATS)["ok"])

    def test_reject_invented_oxygen_value(self):
        # No row has 19.5% oxygen — an answer that invents it fails.
        sentence = "19.5% oxygen is inside the tested range."
        result = check_answer_numbers(sentence, EVIDENCE, STATS)
        self.assertFalse(result["ok"])
        self.assertTrue(any("19.5%" in u for u in result["unverified"]))

    def test_reject_changed_unit(self):
        # 22.2 is an oxygen value, not an airflow — "22.2 cm/s" fails.
        sentence = "The airflow was 22.2 cm/s."
        result = check_answer_numbers(sentence, EVIDENCE, STATS)
        self.assertFalse(result["ok"])
        # And 5 is an airflow, not oxygen — "5% oxygen" fails too.
        sentence = "The test ran at 5% oxygen."
        result = check_answer_numbers(sentence, EVIDENCE, STATS)
        self.assertFalse(result["ok"])

    def test_accept_count_when_rows_were_used(self):
        # "3 tests" is allowed when 3 rows were used for this answer.
        sentence = "The highest oxygen tested is 22.2%, in 3 tests (B1, F1, T25)."
        result = check_answer_numbers(
            sentence, EVIDENCE, STATS, extra_allowed={3.0})
        self.assertTrue(result["ok"])

    def test_reject_count_when_rows_were_not_used(self):
        # "3 tests" without the rows to back it up fails.
        sentence = "The highest oxygen tested is 22.2%, in 3 tests (B1, F1, T25)."
        result = check_answer_numbers(sentence, EVIDENCE, STATS)
        self.assertFalse(result["ok"])

    def test_reject_number_inside_a_larger_invented_claim(self):
        # Every number is real on its own, but the claim as a whole is
        # invented: no row burned at 25% oxygen.
        sentence = "14 tests burned at 25% oxygen."
        result = check_answer_numbers(sentence, EVIDENCE, STATS)
        self.assertFalse(result["ok"])
        self.assertTrue(any("25%" in u for u in result["unverified"]))

    def test_row_number_binding(self):
        # "T25 at 22.2%" is wrong — T25 is 20.8%.
        sentence = "T25 at 22.2% oxygen burned well."
        result = check_answer_numbers(sentence, EVIDENCE, STATS)
        self.assertFalse(result["ok"])
        self.assertTrue(any("T25 is 20.8%" in u for u in result["unverified"]))

    def test_range_bounds_are_allowed_without_the_bound_row(self):
        # A sentence quoting "SIBAL 16.4–20.8%" is fine even when the
        # 20.8% row (T25) is in the evidence but 16.4% is not.
        sentence = (
            "NASA's BASS-II tests cover SIBAL 16.4–20.8% oxygen, so "
            "14.0% oxygen is beyond what was tested."
        )
        result = check_answer_numbers(
            sentence, EVIDENCE, STATS, question_oxygen=14.0,
            range_bounds=(16.4, 20.8))
        self.assertTrue(result["ok"])

    def test_blank_oxygen_in_evidence_does_not_crash(self):
        # v9: the two context-only Saffire III rows (100-S1, 100-S2)
        # have flow 30 cm/s but no oxygen recorded. float("") used
        # to raise ValueError in o2_values and in rule 1's per-row
        # check. A sentence with only valid numbers must pass.
        evidence = EVIDENCE + [
            {"test_id": "100-S1", "material": "SIBAL", "oxygen_pct": "",
             "airflow_cm_s": "30", "airflow_end_cm_s": "30"},
            {"test_id": "100-S2", "material": "SIBAL", "oxygen_pct": "",
             "airflow_cm_s": "30", "airflow_end_cm_s": "30"},
        ]
        sentence = "30.0 cm/s airflow is beyond the tested range."
        result = check_answer_numbers(
            sentence, evidence, STATS, question_flow=30.0)
        self.assertTrue(result["ok"])
        # And a % attached to the blank-oxygen row is skipped, not a
        # crash (there is no oxygen to contradict).
        sentence = "100-S1 at 22.2% oxygen burned well."
        result = check_answer_numbers(sentence, evidence, STATS)
        self.assertTrue(result["ok"])


if __name__ == "__main__":
    unittest.main()
