# Written with SI assistance (Muse), reviewed by Paridhi Singh
"""Unit tests for the Lane B swap to Lane A's data/tests.json (200 rows).

Run from inside logic/ (tests.json must sit at ../data/tests.json):
    python3 -m unittest test_swap -v
"""

import os
import unittest

TESTS_JSON = "../data/tests.json"


@unittest.skipUnless(os.path.exists(TESTS_JSON), "tests.json not next to the repo")
class TestTestsJsonLoader(unittest.TestCase):
    def setUp(self):
        from cards import rows_from_tests_json

        self.rows = rows_from_tests_json(TESTS_JSON)

    def test_loads_200_rows_with_unique_test_ids(self):
        self.assertEqual(len(self.rows), 200)
        ids = [r["test_id"] for r in self.rows]
        self.assertEqual(len(set(ids)), 200)

    def test_psi25_ids_lose_the_gmt_prefix(self):
        b1 = next(r for r in self.rows if r["test_id"] == "B1")
        self.assertEqual(b1["material"], "PMMA")
        self.assertEqual(b1["source"], "PSI-25")

    def test_saffire_i_and_iii_s_rows_are_disambiguated(self):
        ids = [r["test_id"] for r in self.rows]
        self.assertIn("98-S1", ids)
        self.assertIn("100-S1", ids)
        self.assertNotIn("S1", ids)

    def test_saffire_v_rows_stay_labeled_by_pressure(self):
        from classifier import material_ranges

        labeled = [r for r in self.rows if "(Saffire V," in r["material"]]
        self.assertEqual(len(labeled), 3)
        self.assertEqual(
            sorted(r["material"] for r in labeled),
            ["PMMA (Saffire V, 71.3 kPa)", "PMMA (Saffire V, 72.6 kPa)",
             "other (Saffire V, 70.7 kPa)"])
        # And the plain PMMA range never includes their 25.4–26.2%.
        ranges = material_ranges(self.rows)
        self.assertEqual(ranges["PMMA"], (13.6, 22.2))

    def test_sibal_range_includes_saffire_ii(self):
        from classifier import material_ranges

        ranges = material_ranges(self.rows)
        # PSI-25 SIBAL stops at 20.8%; Saffire II SIBAL reaches 22.1%
        # at standard pressure, so it joins the range.
        self.assertEqual(ranges["SIBAL"], (16.4, 22.1))

    def test_context_only_rows_have_no_oxygen(self):
        no_o2 = [r for r in self.rows if r.get("oxygen_pct") in (None, "")]
        self.assertEqual(len(no_o2), 2)
        self.assertEqual({r["test_id"] for r in no_o2}, {"100-S1", "100-S2"})

    def test_low_flow_flag_uses_the_2_cm_s_team_cutoff(self):
        o2 = next(r for r in self.rows if r["test_id"] == "O2")
        self.assertTrue(o2["low_flow_uncertain"])
        b1 = next(r for r in self.rows if r["test_id"] == "B1")
        self.assertFalse(b1["low_flow_uncertain"])

    def test_link_rows_excluded_from_outcome_evidence(self):
        from answer import build_answer, dataset_stats_tests_json

        stats = dataset_stats_tests_json(TESTS_JSON)
        answer = build_answer(
            "Did the material burn at 21% oxygen?",
            21.0, self.rows, stats=stats)
        sources = {e["source"] for e in answer["evidence"]}
        self.assertNotIn("Link et al. 2018", sources)

    def test_stats_come_from_tests_json(self):
        from answer import dataset_stats_tests_json

        stats = dataset_stats_tests_json(TESTS_JSON)
        self.assertEqual(stats["total_tests"], 200)
        self.assertEqual(stats["o2_min"], 13.6)
        self.assertEqual(stats["o2_max"], 22.2)
        self.assertEqual(stats["rows_above_21"], 32)

    def test_no_two_restrictor_psi25_row_has_flow_above_35(self):
        # The BASS-II report caps 2-restrictor flow at about 35 cm/s
        # ("~35 cm/s with two [flow restrictors]"). Lane A's
        # flow_start still has 49 for O5b and O13a — a fan reading,
        # not a flow (their Air display reads "49, 5 cm/s" and
        # "49 44 42 ... (5 2 0)"). This test FAILS until Lane A
        # fixes those rows; it guards the PMMA card range and any
        # per-material flow logic against the same bad value.
        import json

        with open(TESTS_JSON, encoding="utf-8") as f:
            tests = json.load(f)
        bad = []
        for t in tests:
            if t.get("source") != "psi-25":
                continue
            if str(t.get("raw_flow_restrictor")) != "2":
                continue
            for key in ("flow_start", "flow_end"):
                value = t.get(key)
                if value is not None and value > 35:
                    bad.append((t["id"], key, value))
        self.assertEqual(bad, [], f"2-restrictor rows above 35 cm/s: {bad}")


@unittest.skipUnless(os.path.exists(TESTS_JSON), "tests.json not next to the repo")
class TestSuffixedTestIds(unittest.TestCase):
    def test_link_and_saffire_ids_do_not_leak_numbers(self):
        from number_checker import numbers_in

        self.assertEqual(numbers_in("B13a-1 at 20.7% oxygen"), [20.7])
        self.assertEqual(numbers_in("2-7-PMMA at 22.1% oxygen"), [22.1])
        self.assertEqual(numbers_in("98-S1 at 21.5% oxygen"), [21.5])


if __name__ == "__main__":
    unittest.main()
