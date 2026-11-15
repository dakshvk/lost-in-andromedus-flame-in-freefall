# Written with SI assistance (Muse), reviewed by Paridhi Singh
"""Unit tests for the Lane B ranking (team doc, Part 4, Step 2).

Run from inside logic/:  python3 -m unittest test_ranking -v
"""

import unittest

from ranking import rank_experiments, score_experiment

BASS_II = {
    "psi_id": "PSI-25", "title": "Burning and Suppression of Solids - II",
    "fuel_type": "solid", "sub_research_area": "Spacecraft Fire Safety",
    "has_data_table": True, "is_flight": True, "gravity": "micro",
    "test_count": 129,
}

GROUND = {
    "psi_id": "PSI-117", "title": "Cool Flame Dynamics",
    "fuel_type": "liquid", "sub_research_area": "Droplet",
    "has_data_table": False, "is_flight": False, "gravity": "ground",
    "test_count": None,
}


class TestRankingScores(unittest.TestCase):
    def test_bass_ii_scores_12(self):
        score, breakdown, _ = score_experiment(BASS_II)
        self.assertEqual(score, 12)
        self.assertEqual(
            [b["points"] for b in breakdown], [3, 3, 2, 2, 1, 1])

    def test_ground_experiment_scores_0(self):
        score, _, _ = score_experiment(GROUND)
        self.assertEqual(score, 0)

    def test_missing_sub_area_is_zero_and_noted_missing(self):
        exp = dict(BASS_II, sub_research_area=None)
        score, breakdown, notes = score_experiment(exp)
        self.assertEqual(score, 9)
        self.assertIn("sub_research_area missing", notes)
        self.assertIn(
            {"reason": "sub-research area missing", "points": 0}, breakdown)

    def test_near_miss_sub_area_does_not_count(self):
        # "Spacecraft Fire, Smoke Distribution" is not the exact
        # wording "Spacecraft Fire Safety" — Lane B's call, noted in
        # the breakdown so the team can overrule it.
        exp = dict(BASS_II, sub_research_area="Spacecraft Fire, Smoke Distribution")
        score, breakdown, _ = score_experiment(exp)
        self.assertEqual(score, 9)
        self.assertTrue(any(
            "Spacecraft Fire, Smoke Distribution" in b["reason"]
            for b in breakdown))

    def test_fewer_than_20_tests_scores_0_for_that_rule(self):
        exp = dict(BASS_II, test_count=19)
        score, _, _ = score_experiment(exp)
        self.assertEqual(score, 11)

    def test_missing_test_count_is_zero_and_noted_missing(self):
        exp = dict(BASS_II, test_count=None)
        score, _, notes = score_experiment(exp)
        self.assertEqual(score, 11)
        self.assertIn("test_count missing", notes)


class TestRankingOrder(unittest.TestCase):
    def test_ties_break_by_test_count_then_title(self):
        a = dict(BASS_II, psi_id="PSI-25", title="BASS-II", test_count=129)
        b = dict(BASS_II, psi_id="PSI-26", title="BASS", test_count=122)
        c = dict(BASS_II, psi_id="PSI-100", title="SAFFIRE-III",
                 test_count=2, has_data_table=False)
        ranked = rank_experiments([b, c, a])
        self.assertEqual([e["psi_id"] for e in ranked],
                         ["PSI-25", "PSI-26", "PSI-100"])
        self.assertEqual([e["rank"] for e in ranked], [1, 2, 3])

    def test_ranking_note_says_team_judgement_not_nasa(self):
        ranked = rank_experiments([BASS_II])
        self.assertIn("team's judgement, not NASA's",
                      ranked[0]["score_note"])


if __name__ == "__main__":
    unittest.main()
