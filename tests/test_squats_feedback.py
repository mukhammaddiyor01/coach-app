import unittest

from backend.services.squats_service import SquatsService
from test_squats_service import squat_body, hold


class SquatsFeedbackTests(unittest.TestCase):
    def test_extreme_torso_lean_is_reported_without_claiming_back_shape(self):
        observation = squat_body()
        observation[11]["x"] = 100 / 640
        observation[11]["y"] = 150 / 480
        result = SquatsService().update(observation, 640, 480, 0)
        self.assertEqual(result["feedback"]["code"], "torso_position")
        self.assertEqual(result["feedback"]["level"], "adjust")
        self.assertGreater(result["torso_lean_angle"], 70)
        self.assertEqual(result["rep_count"], 0)

    def test_half_movement_is_unconfirmed_not_a_complete_rep(self):
        service = SquatsService()
        hold(service, "up", 0)
        result = hold(service, "middle", 0.4)
        self.assertEqual(result["feedback"]["code"], "lower_position_unconfirmed")
        self.assertEqual(result["feedback"]["level"], "observed")
        self.assertEqual(hold(service, "up", 0.8)["rep_count"], 0)

    def test_return_from_lower_position_requires_confirmed_standing(self):
        service = SquatsService()
        hold(service, "up", 0)
        hold(service, "down", 0.4)
        result = hold(service, "middle", 0.8)
        self.assertEqual(result["feedback"]["code"], "upper_position_unconfirmed")
        self.assertEqual(result["rep_count"], 0)
        self.assertEqual(hold(service, "up", 1.2)["rep_count"], 1)

    def test_missing_or_low_confidence_side_has_no_posture_judgment(self):
        observation = squat_body()
        observation[25]["presence"] = 0.1
        for landmarks in ([], observation):
            result = SquatsService().update(landmarks, 640, 480, 0)
            self.assertEqual(result["feedback"]["level"], "unavailable")
            self.assertIsNone(result["torso_lean_angle"])

    def test_completed_count_survives_feedback_and_reset_clears_it(self):
        service = SquatsService()
        hold(service, "up", 0)
        hold(service, "down", 0.4)
        hold(service, "up", 0.8)
        result = service.update([], 640, 480, 1.1)
        self.assertEqual(result["rep_count"], 1)
        self.assertEqual(result["feedback"]["level"], "unavailable")
        self.assertEqual(service.reset()["rep_count"], 0)
        self.assertIsNone(service.reset()["feedback"]["side"])


if __name__ == "__main__":
    unittest.main()
