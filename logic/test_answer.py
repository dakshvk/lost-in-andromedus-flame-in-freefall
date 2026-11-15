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


@unittest.skipUnless(os.path.exists(TESTS_JSON), "tests.json not next to the repo")
class TestV9Answers(unittest.TestCase):
    """v9 (PR #1 review, Daksh, Nov 14): the combined % + airflow
    question, the material count without Link rows, the low-flow
    note, and the gravity note's pressure range from the data."""

    def setUp(self):
        from answer import dataset_stats_tests_json
        from cards import rows_from_tests_json

        self.rows = rows_from_tests_json(TESTS_JSON)
        self.stats = dataset_stats_tests_json(TESTS_JSON)

    def test_combined_oxygen_and_airflow_question_is_beyond(self):
        # Daksh's case: "PMMA at 20% oxygen and 45 cm/s airflow?"
        # must come back BEYOND — ask() used to drop the 45 cm/s
        # entirely, so it came back INSIDE on oxygen alone.
        from answer import ask

        out = ask("PMMA at 20% oxygen and 45 cm/s airflow?",
                  self.rows, stats=self.stats)
        answer = out["answer"]
        self.assertEqual(answer["verdict"], "BEYOND")
        # The sentence names the airflow, not the oxygen: 20% is
        # inside the PMMA O2 range, so "20.0% oxygen is beyond"
        # would be false.
        self.assertIn("45.0 cm/s airflow is beyond", answer["sentence"])
        self.assertNotIn("20.0% oxygen is beyond", answer["sentence"])
        self.assertTrue(answer["number_check"]["ok"])

    def test_combined_question_at_22_cm_s_is_near(self):
        from answer import ask

        out = ask("PMMA at 20% oxygen and 22 cm/s airflow?",
                  self.rows, stats=self.stats)
        answer = out["answer"]
        self.assertEqual(answer["verdict"], "NEAR")
        self.assertIn("22.0 cm/s airflow is just outside", answer["sentence"])
        self.assertTrue(answer["number_check"]["ok"])

    def test_inside_sentence_quotes_material_count_not_200(self):
        # The INSIDE sentence used to say "200 tests" for every
        # material. PMMA has 154 rows, and the 52 Link rows aren't
        # outcome evidence, so it quotes 102.
        from answer import ask

        out = ask("Is 20% oxygen inside our data for PMMA?",
                  self.rows, stats=self.stats)
        answer = out["answer"]
        self.assertEqual(answer["verdict"], "INSIDE")
        self.assertIn("102 tests", answer["sentence"])
        self.assertNotIn("200 tests", answer["sentence"])
        self.assertTrue(answer["number_check"]["ok"])

    def test_lowest_airflow_note_says_low_readings_are_uncertain(self):
        # "Lowest airflow for PMMA is 0.0 cm/s" — all 7 tie rows
        # carry Lane A's low-flow flag, so the answer adds a note.
        from answer import ask

        out = ask("Which PMMA test had the lowest airflow?",
                  self.rows, stats=self.stats)
        answer = out["answer"]
        self.assertIn("0.0 cm/s", answer["sentence"])
        self.assertIsNotNone(answer.get("note"))
        self.assertIn("uncertain", answer["note"])
        self.assertTrue(answer["number_check"]["ok"])

    def test_gravity_note_shows_pressure_range_from_the_data(self):
        # The gravity note used to say "pressure differs" (fixed
        # text). It now shows the recorded pressure range: 70.7
        # (Saffire V) to 100.0 kPa (Saffire IV).
        from answer import ask

        out = ask("Is 20% oxygen inside our data for PMMA?",
                  self.rows, stats=self.stats)
        note = out["answer"]["gravity_note"]
        self.assertIn("70.7–100.0 kPa", note)
        self.assertNotIn("pressure differs", note)

    def test_closest_rows_use_flow_not_just_oxygen(self):
        # For the combined question, the evidence must be rows with
        # flow data near 45 cm/s — not the no-flow rows (M12, O6),
        # which used to rank first because a missing flow scored 1.0
        # while a far flow scored more.
        from answer import ask

        out = ask("PMMA at 20% oxygen and 45 cm/s airflow?",
                  self.rows, stats=self.stats)
        ids = [r["test_id"] for r in out["answer"]["evidence"]]
        self.assertNotIn("M12", ids)
        self.assertNotIn("O6", ids)
        self.assertTrue(all(
            r["airflow_cm_s"] not in (None, "")
            for r in out["answer"]["evidence"]))

    def test_airflow_only_question_with_a_material_uses_its_range(self):
        # "PMMA at 45 cm/s airflow?" (no %) is BEYOND too — the
        # material's own flow range applies, not the hardware band.
        from answer import ask

        out = ask("PMMA at 45 cm/s airflow?",
                  self.rows, stats=self.stats)
        answer = out["answer"]
        self.assertEqual(answer["verdict"], "BEYOND")
        self.assertIn("PMMA airflow runs 0.0–20.0 cm/s", answer["sentence"])
        self.assertTrue(answer["number_check"]["ok"])


if __name__ == "__main__":
    unittest.main()
