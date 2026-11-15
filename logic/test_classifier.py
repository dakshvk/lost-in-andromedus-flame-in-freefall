# Written with SI assistance (Muse), reviewed by Paridhi Singh
"""Unit tests for the Lane B classifier (team doc, Part 4, Step 1.9).

Run from inside logic/:  python3 -m unittest test_classifier -v
"""

import os
import unittest

from classifier import classify, dataset_range, flow_range, material_ranges

# Six real sample rows (B1, B2, F1, F2, T1, T25) — the same rows as
# sample_data.csv, written out so the tests do not depend on a file.
SAMPLE_ROWS = [
    {"test_id": "B1", "material": "PMMA", "oxygen_pct": "22.2", "airflow_cm_s": "5"},
    {"test_id": "B2", "material": "PMMA", "oxygen_pct": "22.2", "airflow_cm_s": "5"},
    {"test_id": "F1", "material": "Nomex", "oxygen_pct": "22.2", "airflow_cm_s": "9.5"},
    {"test_id": "F2", "material": "Nomex", "oxygen_pct": "21.0", "airflow_cm_s": "15"},
    {"test_id": "T1", "material": "SIBAL", "oxygen_pct": "18.5", "airflow_cm_s": "10"},
    {"test_id": "T25", "material": "SIBAL", "oxygen_pct": "20.8", "airflow_cm_s": "5", "airflow_end_cm_s": "2.5"},
]

# Twenty-one rows: 20 PMMA rows and 1 Wax row, so the "fewer than 3
# rows means extrapolated" rule can be tested without the full CSV.
MANY_ROWS = (
    [{"test_id": f"P{i}", "material": "PMMA", "oxygen_pct": "20.0", "airflow_cm_s": "5"}
     for i in range(20)]
    + [{"test_id": "F4", "material": "Wax", "oxygen_pct": "17.4", "airflow_cm_s": "3"}]
)


class TestClassifierRanges(unittest.TestCase):
    def test_point_inside_sibal_range(self):
        # SIBAL in the sample is 18.5–20.8%; 19% is inside.
        self.assertEqual(
            classify(19.0, material="SIBAL", rows=SAMPLE_ROWS)["verdict"], "INSIDE")

    def test_point_just_outside_sibal_range_is_near(self):
        # 21.5% is just past SIBAL's 20.8% max — inside the 1.0-point
        # NEAR band, not BEYOND.
        result = classify(21.5, material="SIBAL", rows=SAMPLE_ROWS)
        self.assertEqual(result["verdict"], "NEAR")

    def test_point_at_30_percent_oxygen_is_beyond(self):
        # A Moon-cabin oxygen level is extrapolated, not covered.
        result = classify(30.0, rows=SAMPLE_ROWS)
        self.assertEqual(result["verdict"], "BEYOND")

    def test_unknown_material(self):
        result = classify(20.0, material="Unobtainium", rows=SAMPLE_ROWS)
        self.assertEqual(result["verdict"], "BEYOND")
        self.assertIn("No Unobtainium rows", result["reason"])

    def test_material_with_too_few_rows_is_extrapolated(self):
        # Wax has 1 row in a 21-row dataset — fewer than 3, so even
        # its own tested oxygen (17.4%) is extrapolated, not covered.
        result = classify(17.4, material="Wax", rows=MANY_ROWS)
        self.assertEqual(result["verdict"], "BEYOND")
        self.assertIn("fewer than 3", result["reason"])

    def test_too_few_rows_rule_does_not_apply_to_the_sample(self):
        # The 6-row sample is explicitly a sample: Nomex has 2 rows
        # there, but 21% Nomex is still INSIDE, not extrapolated.
        result = classify(21.0, material="Nomex", rows=SAMPLE_ROWS)
        self.assertEqual(result["verdict"], "INSIDE")

    def test_oxygen_outside_0_to_100_is_invalid(self):
        for bad in (150.0, -5.0, 101.0):
            result = classify(bad, rows=SAMPLE_ROWS)
            self.assertEqual(result["verdict"], "INVALID", f"{bad}%")

    def test_missing_oxygen_asks_for_a_value(self):
        result = classify(None, rows=SAMPLE_ROWS)
        self.assertEqual(result["verdict"], "NEED_OXYGEN")

    def test_missing_flow_is_unknown_not_a_verdict(self):
        # No airflow given: the verdict comes from oxygen alone, and
        # airflow is listed as unknown.
        result = classify(20.0, airflow_cm_s=None, rows=SAMPLE_ROWS)
        self.assertEqual(result["verdict"], "INSIDE")
        self.assertTrue(any("airflow" in u for u in result["unknown"]))


class TestFlowRange(unittest.TestCase):
    def test_null_flow_start_is_skipped(self):
        # O12 has no flow number at all ("no ign at any flow"); it
        # must not break the range or count as 0. T25's end (2.5)
        # now counts — a test whose flow changed covers its whole
        # span — so the range is (2.5, 5.0), not (5.0, 5.0).
        rows = [
            {"test_id": "O12", "material": "PMMA", "oxygen_pct": "13.6", "airflow_cm_s": ""},
            {"test_id": "B1", "material": "PMMA", "oxygen_pct": "22.2", "airflow_cm_s": "5"},
            {"test_id": "T25", "material": "SIBAL", "oxygen_pct": "20.8", "airflow_cm_s": "5", "airflow_end_cm_s": "2.5"},
        ]
        self.assertEqual(flow_range(rows), (2.5, 5.0))

    def test_flow_range_uses_the_whole_span(self):
        # T17 ramps 6 -> 53 and T25 drops 5 -> 2.5: the range covers
        # the full span of every test, not just the starting flows.
        rows = [
            {"test_id": "B1", "material": "PMMA", "oxygen_pct": "22.2", "airflow_cm_s": "5"},
            {"test_id": "T25", "material": "SIBAL", "oxygen_pct": "20.8", "airflow_cm_s": "5", "airflow_end_cm_s": "2.5"},
            {"test_id": "T17", "material": "SIBAL", "oxygen_pct": "20.0", "airflow_cm_s": "6", "airflow_end_cm_s": "53"},
        ]
        self.assertEqual(flow_range(rows), (2.5, 53.0))

    def test_flow_range_empty_when_no_row_has_a_flow(self):
        rows = [{"test_id": "O12", "material": "PMMA", "oxygen_pct": "13.6", "airflow_cm_s": ""}]
        self.assertEqual(flow_range(rows), (None, None))


@unittest.skipUnless(
    os.path.exists("../data/tests.json"),
    "tests.json not next to the repo",
)
class TestMaterialFlowRange(unittest.TestCase):
    """v9: classify() uses each material's own tested flow range with
    a 25% margin (doc Step 1 items 3 and 4), not the hardware limit
    for every material. PMMA was tested at 0–20 cm/s, so 45 cm/s for
    PMMA is BEYOND; the hardware band (0–55, NEAR to 65) is only the
    fallback when no material is given."""

    @classmethod
    def setUpClass(cls):
        from answer import _standard_pressure
        from cards import rows_from_tests_json

        # As in build_answer: the standard-pressure filter first, so
        # the Saffire V rows never join the ranges.
        all_rows = rows_from_tests_json("../data/tests.json")
        cls.rows = [r for r in all_rows if _standard_pressure(r)]

    def test_pmma_flow_range_is_0_to_20(self):
        from classifier import material_flow_range

        self.assertEqual(material_flow_range(self.rows, "PMMA"), (0.0, 20.0))

    def test_sibal_flow_range_is_1_to_53(self):
        from classifier import material_flow_range

        self.assertEqual(material_flow_range(self.rows, "SIBAL"), (1.0, 53.0))

    def test_pmma_at_45_cm_s_is_beyond(self):
        # Daksh's case (PR #1 review, Nov 14): PMMA was only tested
        # to 20 cm/s, so 45 cm/s is beyond even the 25% margin (25).
        result = classify(20.0, 45.0, material="PMMA", rows=self.rows)
        self.assertEqual(result["verdict"], "BEYOND")
        self.assertIn("45.0 cm/s airflow", result["reason"])

    def test_pmma_at_20_cm_s_is_inside(self):
        result = classify(20.0, 20.0, material="PMMA", rows=self.rows)
        self.assertEqual(result["verdict"], "INSIDE")

    def test_pmma_at_22_cm_s_is_near(self):
        # 22 is past PMMA's 20 max but inside the 25% margin (25).
        result = classify(20.0, 22.0, material="PMMA", rows=self.rows)
        self.assertEqual(result["verdict"], "NEAR")

    def test_pmma_at_25_cm_s_is_near_at_the_margin_edge(self):
        result = classify(20.0, 25.0, material="PMMA", rows=self.rows)
        self.assertEqual(result["verdict"], "NEAR")

    def test_pmma_at_26_cm_s_is_beyond(self):
        result = classify(20.0, 26.0, material="PMMA", rows=self.rows)
        self.assertEqual(result["verdict"], "BEYOND")

    def test_sibal_at_60_cm_s_is_near(self):
        # SIBAL runs 1–53, margin 13, so NEAR up to 66.
        result = classify(20.0, 60.0, material="SIBAL", rows=self.rows)
        self.assertEqual(result["verdict"], "NEAR")

    def test_sibal_at_70_cm_s_is_beyond(self):
        result = classify(20.0, 70.0, material="SIBAL", rows=self.rows)
        self.assertEqual(result["verdict"], "BEYOND")

    def test_nomex_at_22_cm_s_is_near(self):
        # Nomex runs 8–20, margin 3, so NEAR up to 23.
        result = classify(21.0, 22.0, material="Nomex", rows=self.rows)
        self.assertEqual(result["verdict"], "NEAR")

    def test_nomex_at_24_cm_s_is_beyond(self):
        result = classify(21.0, 24.0, material="Nomex", rows=self.rows)
        self.assertEqual(result["verdict"], "BEYOND")

    def test_no_material_uses_the_hardware_band(self):
        # No material given: 45 cm/s is inside the BASS-II duct's
        # 0–55 cm/s band, 60 is NEAR (to 65), 70 is BEYOND.
        self.assertEqual(
            classify(20.0, 45.0, rows=self.rows)["verdict"], "INSIDE")
        self.assertEqual(
            classify(20.0, 60.0, rows=self.rows)["verdict"], "NEAR")
        self.assertEqual(
            classify(20.0, 70.0, rows=self.rows)["verdict"], "BEYOND")

    def test_wax_hits_the_too_few_rows_rule(self):
        # v10: Wax has 1 row (F4), so it is extrapolated, not covered.
        # The "coverage" key tells build_answer to use the coverage
        # sentence instead of the generic "both beyond" one (which
        # would name an airflow that was never given).
        result = classify(17.0, None, material="Wax", rows=self.rows)
        self.assertEqual(result["verdict"], "BEYOND")
        self.assertEqual(result.get("coverage"), "too_few")

    def test_margin_definition_is_team_confirmed(self):
        # v10: Daksh confirmed the 25% margin is 25% of the range
        # width, on both sides, low clamped at 0. FLOW_MARGIN is
        # that fraction; the PMMA 25 cm/s edge test above pins the
        # arithmetic (20 + 25% of 20 = 25).
        from classifier import FLOW_MARGIN

        self.assertEqual(FLOW_MARGIN, 0.25)


class TestFullDataset(unittest.TestCase):
    """Locks in the corrected airflow numbers on the real dataset
    (Lane A's tests.json, 200 rows, once it lands; the PSI-25 CSV
    before that)."""

    @unittest.skipUnless(
        os.path.exists("../data/tests.json"),
        "tests.json not next to the repo",
    )
    def test_highest_airflow_is_53_not_49(self):
        from answer import max_airflow
        from cards import rows_from_tests_json

        rows = rows_from_tests_json("../data/tests.json")
        result = max_airflow(rows)
        # 49 cm/s (O5b, O13a) was a fan reading, not a flow. The real
        # max is 53 cm/s, test T17 (report Table 7.1: "6 to 53").
        self.assertEqual(result["max_airflow"], 53.0)
        self.assertEqual(result["test_ids"], ["T17"])

    @unittest.skipUnless(
        os.path.exists("../data/tests.json"),
        "tests.json not next to the repo",
    )
    def test_sibal_lowest_airflow_is_1_not_2_5(self):
        from answer import min_airflow
        from cards import rows_from_tests_json

        rows = rows_from_tests_json("../data/tests.json")
        sibal = [r for r in rows if r["material"] == "SIBAL"]
        result = min_airflow(sibal)
        # T25/T26 dropped to 2.5, but T4, T5 and T13 went to 1.0. T6
        # is NOT in the list: its Air display reads "5 2 1 <1" and
        # tests.json records no end flow for it, so its lowest is its
        # 5 cm/s start. (v6's CSV parser read the "1" as the end.)
        self.assertEqual(result["min_airflow"], 1.0)
        self.assertEqual(result["test_ids"], ["T4", "T5", "T13"])

    @unittest.skipUnless(
        os.path.exists("../data/tests.json"),
        "tests.json not next to the repo",
    )
    def test_o12_has_no_flow(self):
        from cards import rows_from_tests_json

        rows = rows_from_tests_json("../data/tests.json")
        o12 = next(r for r in rows if r["test_id"] == "O12")
        self.assertEqual(o12["airflow_cm_s"], "")
        self.assertEqual(o12["airflow_end_cm_s"], "")

    @unittest.skipUnless(
        os.path.exists("../data/tests.json"),
        "tests.json not next to the repo",
    )
    def test_highest_oxygen_excludes_low_pressure_saffire_v(self):
        from answer import max_oxygen
        from cards import rows_from_tests_json

        rows = rows_from_tests_json("../data/tests.json")
        result = max_oxygen(rows)
        # The Saffire V rows reach 26.2% but at ~71 kPa — they stay
        # labeled by pressure and never join the normal max.
        self.assertEqual(result["max_oxygen"], 22.2)
        self.assertEqual(len(result["test_ids"]), 14)


if __name__ == "__main__":
    unittest.main()
