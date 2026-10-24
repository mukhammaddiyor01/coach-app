import unittest

from backend.services.lunge_service import LungeService
from test_lunge_service import lunge_body, hold


class LungeFeedbackTests(unittest.TestCase):
    def test_missing_leg_cannot_produce_a_posture_judgment(self):
        observation = lunge_body()
        observation[26]["visibility"] = 0.1
        for landmarks in ([], observation):
            result = LungeService().update(landmarks, 640, 480, 0)
            self.assertEqual(result["feedback"]["level"], "unavailable")
            self.assertIsNone(result["torso_lean_angle"])

    def test_split_stance_and_extreme_lean_have_specific_cues(self):
        together = lunge_body()
        together[28]["x"] = together[27]["x"]
        leaning = lunge_body()
        leaning[11]["x"] = 100 / 640
        leaning[11]["y"] = 140 / 480
        for observation, code in ((together, "split_stance_needed"), (leaning, "torso_position")):
            with self.subTest(code=code):
                result = LungeService().update(observation, 640, 480, 0)
                self.assertEqual(result["feedback"]["code"], code)
                self.assertEqual(result["feedback"]["level"], "adjust")
                self.assertEqual(result["phase"], "ready")

    def test_one_bent_knee_is_unconfirmed_and_does_not_count(self):
        service = LungeService()
        hold(service, "up", 0)
        one_bent = lunge_body("down")
        one_bent[26] = dict(lunge_body()[26])
        service.update(one_bent, 640, 480, 0.4)
        result = service.update(one_bent, 640, 480, 0.6)
        self.assertEqual(result["feedback"]["code"], "bend_both_knees")
        self.assertIn("110° or less", result["feedback"]["message"])
        self.assertIn("Left:", result["feedback"]["message"])
        self.assertEqual(result["feedback"]["level"], "observed")
        self.assertEqual(hold(service, "up", 0.8)["rep_count"], 0)

    def test_stance_change_requires_a_new_upper_sequence(self):
        service = LungeService()
        hold(service, "up", 0)
        hold(service, "down", 0.4)
        result = service.update(lunge_body(mirrored=True), 640, 480, 0.7)
        self.assertEqual(result["feedback"]["code"], "stance_changed")
        self.assertEqual(hold(service, "up", 0.8)["rep_count"], 0)

    def test_starting_with_bent_knees_explains_why_counting_has_not_started(self):
        service = LungeService()
        result = hold(service, "down", 0)
        self.assertEqual(result["phase"], "ready")
        self.assertEqual(result["rep_count"], 0)
        self.assertEqual(result["feedback"]["code"], "starting_position_unconfirmed")
        self.assertIn("150° or more", result["feedback"]["message"])
        self.assertIn("Left: 90.0°, right: 90.0°", result["feedback"]["message"])
        self.assertEqual(hold(service, "up", 0.4)["rep_count"], 0)
        hold(service, "down", 0.8)
        self.assertEqual(hold(service, "up", 1.2)["rep_count"], 1)

    def test_first_upper_observation_explains_confirmation_hold(self):
        service = LungeService()
        result = service.update(lunge_body(), 640, 480, 0)
        self.assertEqual(result["phase"], "ready")
        self.assertEqual(result["feedback"]["code"], "upper_hold_needed")
        self.assertEqual(service.update(lunge_body(), 640, 480, 0.2)["phase"], "up")

    def test_unconfirmed_finish_reports_measured_knees_without_counting(self):
        service = LungeService()
        hold(service, "up", 0)
        hold(service, "down", 0.4)
        one_bent = lunge_body("down")
        one_bent[26] = dict(lunge_body()[26])
        result = service.update(one_bent, 640, 480, 0.8)
        self.assertEqual(result["phase"], "down")
        self.assertEqual(result["rep_count"], 0)
        self.assertEqual(result["feedback"]["code"], "upper_position_unconfirmed")
        self.assertIn("150° or more", result["feedback"]["message"])
        self.assertIn("Left:", result["feedback"]["message"])
        self.assertEqual(hold(service, "up", 1)["rep_count"], 1)

    def test_valid_observation_and_reset_do_not_claim_complete_form_correctness(self):
        service = LungeService()
        result = hold(service, "up", 0)
        self.assertEqual(result["feedback"]["level"], "observed")
        self.assertEqual(result["torso_lean_angle"], 0)
        self.assertNotIn("score", result["feedback"])
        self.assertEqual(service.reset()["feedback"]["level"], "unavailable")


if __name__ == "__main__":
    unittest.main()
