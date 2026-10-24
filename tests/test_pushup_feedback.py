"""Specific cues must follow visible geometry and never invent a full-form score."""
import unittest

from backend.services.pushup_service import PushUpService
from test_pushup_service import body, hold


class PushUpFeedbackTests(unittest.TestCase):
    def test_raised_and_lowered_hips_have_different_cues(self):
        for hip_height, knee_height, code in ((70, 110, "hips_raised"), (230, 190, "hips_lowered")):
            with self.subTest(code=code):
                observation = body()
                observation[23]["y"] = hip_height / 480
                observation[25]["y"] = knee_height / 480
                result = PushUpService().update(observation, 640, 480, 0)
                self.assertEqual(result["feedback"]["code"], code)
                self.assertEqual(result["feedback"]["level"], "adjust")
                self.assertEqual(result["phase"], "ready")
                self.assertEqual(result["rep_count"], 0)

    def test_bent_knees_and_wrist_position_have_specific_cues(self):
        knees = body()
        knees[25]["y"] = 220 / 480
        wrists = body()
        wrists[15]["y"] = 160 / 480
        for observation, code in ((knees, "knees_bent"), (wrists, "wrist_position")):
            self.assertEqual(PushUpService().update(observation, 640, 480, 0)["feedback"]["code"], code)

    def test_missing_and_uncertain_body_is_unavailable_not_a_form_judgment(self):
        uncertain = body()
        uncertain[13]["visibility"] = 0.1
        for observation in ([], uncertain):
            result = PushUpService().update(observation, 640, 480, 0)
            self.assertEqual(result["feedback"]["level"], "unavailable")
            self.assertIsNone(result["feedback"]["side"])
            self.assertIsNone(result["knee_angle"])

    def test_valid_tracking_describes_observed_side_without_correctness_score(self):
        result = hold(PushUpService(), "up", 0)
        self.assertEqual(result["feedback"]["level"], "observed")
        self.assertEqual(result["feedback"]["side"], "left")
        self.assertEqual(result["knee_angle"], 180)
        self.assertNotIn("score", result["feedback"])

    def test_feedback_cannot_add_reps_and_reset_clears_old_cues(self):
        service = PushUpService()
        hold(service, "up", 0)
        hold(service, "down", 0.4)
        hold(service, "up", 0.8)
        bent = body()
        bent[25]["y"] = 220 / 480
        result = service.update(bent, 640, 480, 1.1)
        self.assertEqual(result["rep_count"], 1)
        self.assertEqual(result["feedback"]["code"], "knees_bent")
        result = service.reset()
        self.assertEqual(result["feedback"]["level"], "unavailable")
        self.assertEqual(result["rep_count"], 0)


if __name__ == "__main__":
    unittest.main()
