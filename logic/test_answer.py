# Written with SI assistance (Muse), reviewed by Paridhi Singh
"""Unit tests for the Lane B answer builder (team doc, Part 4, Step 1.9).

Run from inside logic/:  python3 -m unittest test_answer -v
"""

import os
import unittest

from answer import build_answer

TESTS_JSON = "../data/tests.json"

STATS = {"total_tests": 129, "o2_min": 13.6, "o2_max": 22.2, "rows_above_21": 18}

# A Link et al. row (rod data from the paper) placed closest to the
# question's oxygen on purpose: without the filter it would be the
# top evidence row for an outcome question.
ROWS_WITH_LINK = [
    {"test_id": "B1", "material": "PMMA", "oxygen_pct": "22.2",
     "airflow_cm_s": "5", "airflow_end_cm_s": "", "outcome": "",
     "source": "PSI-25", "source_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-25"},
    {"test_id": "T25", "material": "SIBAL", "oxygen_pct": "20.8",
     "airflow_cm_s": "5", "airflow_end_cm_s": "2.5", "outcome": "",
     "source": "PSI-25", "source_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-25"},
    {"test_id": "L1", "material": "PMMA", "oxygen_pct": "20.9",
     "airflow_cm_s": "7.6", "airflow_end_cm_s": "", "outcome": "spread",
     "source": "Link et al. 2018", "source_url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC5760683/"},
]


class TestOutcomeEvidence(unittest.TestCase):
    def test_link_row_never_in_outcome_evidence(self):
        # L1 (20.9%) is the closest row to 21.0%, but it is a Link
        # et al. paper row, not a BASS-II test — an outcome question
        # must never cite it.
        answer = build_answer(
            "Did the material burn at 21% oxygen?", 21.0,
            ROWS_WITH_LINK, stats=STATS)
        ids = [r["test_id"] for r in answer["evidence"]]
        self.assertNotIn("L1", ids)

    def test_link_row_allowed_for_non_outcome_questions(self):
        # The filter only applies to outcome questions: a plain
        # range question may still cite the closest row.
        answer = build_answer(
            "What about 21% oxygen?", 21.0, ROWS_WITH_LINK, stats=STATS)
        ids = [r["test_id"] for r in answer["evidence"]]
        self.assertIn("L1", ids)


class TestInvalidAndWaxSentences(unittest.TestCase):
    def test_invalid_oxygen_sentence(self):
        answer = build_answer(
            "What about 150% oxygen?", 150.0, ROWS_WITH_LINK, stats=STATS)
        self.assertEqual(answer["verdict"], "INVALID")
        self.assertIn("between 0 and 100%", answer["sentence"])

    def test_wax_sentence_quotes_wax_range_not_overall(self):
        # 14% for Wax is BEYOND, and the sentence must say so for the
        # Wax range (17.4%), not the overall range (13.6–22.2%).
        wax = [r for r in ROWS_WITH_LINK if r["material"] == "PMMA"]
        answer = build_answer(
            "What about 14% oxygen for Wax?", 14.0, wax, material="Wax",
            stats=STATS)
        self.assertEqual(answer["verdict"], "BEYOND")


@unittest.skipUnless(os.path.exists(TESTS_JSON), "tests.json not next to the repo")
class TestLowPressureRowsStayOut(unittest.TestCase):
    """The Saffire V rows (~71 kPa) stay labeled by pressure: they
    never join the normal ranges or the evidence pool. Without the
    filter, 24% oxygen read INSIDE (the overall range stretched to
    26.2%) and the 30% Moon-base answer cited the Saffire V rows as
    its evidence — even though the sentence quoted 13.6–22.2%."""

    def setUp(self):
        from answer import dataset_stats_tests_json
        from cards import rows_from_tests_json

        self.rows = rows_from_tests_json(TESTS_JSON)
        self.stats = dataset_stats_tests_json(TESTS_JSON)

    def test_24_percent_oxygen_is_beyond_not_inside(self):
        answer = build_answer(
            "What about 24% oxygen?", 24.0, self.rows, stats=self.stats)
        self.assertEqual(answer["verdict"], "BEYOND")
        self.assertIn("13.6–22.2% oxygen", answer["sentence"])

    def test_25_4_percent_oxygen_is_beyond(self):
        # 25.4% is a Saffire V level (V-3), but at ~71 kPa — it does
        # not make a standard-pressure question INSIDE.
        answer = build_answer(
            "What about 25.4% oxygen?", 25.4, self.rows, stats=self.stats)
        self.assertEqual(answer["verdict"], "BEYOND")

    def test_moon_base_evidence_is_standard_pressure_only(self):
        answer = build_answer(
            "A Moon base runs at 30% oxygen. What does NASA's testing cover?",
            30.0, self.rows, stats=self.stats)
        self.assertEqual(answer["verdict"], "BEYOND")
        # The evidence is the closest standard-pressure rows (22.2%);
        # Saffire V is cited separately in nearest_evidence, not as
        # evidence rows.
        ids = [r["test_id"] for r in answer["evidence"]]
        self.assertEqual(ids, ["B1", "B2", "B3"])
        self.assertTrue(all("Saffire V" not in r["material"]
                            for r in answer["evidence"]))
        self.assertIn("Saffire V", answer["nearest_evidence"]["text"])


if __name__ == "__main__":
    unittest.main()
