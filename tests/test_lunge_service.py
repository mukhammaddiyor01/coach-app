"""Stationary Lunge sequences use synthetic landmarks, never a camera."""
import copy
import unittest

from backend.services.lunge_service import LungeService
from backend.services.observations import InvalidLandmarksError


def lunge_body(position="up", width=640, height=480, mirrored=False):
    landmarks = [dict(x=0, y=0, visibility=0, presence=0) for _ in range(33)]
    points = {
        11: (240, 40), 12: (240, 40),
        23: (240, 150), 24: (240, 150),
        25: (290, 225), 27: (340, 300),
        26: (190, 225), 28: (140, 300),
    }
    if position == "down":
        points.update({11: (240, 70), 12: (240, 70), 23: (240, 200), 24: (240, 200), 25: (340, 200), 26: (240, 300)})
    for index, (horizontal, vertical) in points.items():
        if mirrored:
            horizontal = 640 - horizontal
        landmarks[index] = dict(x=horizontal / width, y=vertical / height, visibility=1, presence=1)
    return landmarks


def hold(service, position, start, **kwargs):
    observation = lunge_body(position, **kwargs)
    dimensions = (kwargs.get("width", 640), kwargs.get("height", 480))
    service.update(observation, *dimensions, start)
    return service.update(observation, *dimensions, start + 0.2)


class LungeServiceTests(unittest.TestCase):
    def test_full_repetition_and_holding_either_position(self):
        service = LungeService()
        hold(service, "up", 0)
        hold(service, "down", 0.4)
        self.assertEqual(hold(service, "down", 0.8)["rep_count"], 0)
        self.assertEqual(hold(service, "up", 1.2)["rep_count"], 1)
        self.assertEqual(hold(service, "up", 1.6)["rep_count"], 1)

    def test_starting_at_bottom_does_not_count(self):
        service = LungeService()
        hold(service, "down", 0)
        self.assertEqual(hold(service, "up", 0.4)["rep_count"], 0)

    def test_both_knees_must_bend_and_straighten(self):
        service = LungeService()
        hold(service, "up", 0)
        one_bent = lunge_body("down")
        one_bent[26] = dict(lunge_body()[26])
        for time in (0.4, 0.6):
            service.update(one_bent, 640, 480, time)
        self.assertEqual(hold(service, "up", 0.8)["rep_count"], 0)
        hold(service, "down", 1.2)
        for time in (1.6, 1.8):
            result = service.update(one_bent, 640, 480, time)
        self.assertEqual(result["rep_count"], 0)
        self.assertEqual(hold(service, "up", 2)["rep_count"], 1)

    def test_short_position_jitter_does_not_count(self):
        service = LungeService()
        hold(service, "up", 0)
        for time, position in ((0.3, "down"), (0.35, "up"), (0.4, "down"), (0.45, "up")):
            service.update(lunge_body(position), 640, 480, time)
        self.assertEqual(hold(service, "up", 0.6)["rep_count"], 0)

    def test_missing_or_uncertain_joint_discards_partial_rep(self):
        hidden = lunge_body()
        hidden[26]["presence"] = 0.1
        outside = lunge_body()
        outside[28]["x"] = -0.1
        for observation in ([], hidden, outside):
            with self.subTest():
                service = LungeService()
                hold(service, "up", 0)
                hold(service, "down", 0.4)
                self.assertEqual(service.update(observation, 640, 480, 0.7)["phase"], "ready")
                self.assertEqual(hold(service, "up", 0.8)["rep_count"], 0)

    def test_gap_and_lost_body_preserve_completed_count(self):
        service = LungeService()
        hold(service, "up", 0)
        hold(service, "down", 0.4)
        hold(service, "up", 0.8)
        hold(service, "down", 1.2)
        self.assertEqual(hold(service, "up", 3)["rep_count"], 1)
        self.assertEqual(service.update([], 640, 480, 3.4)["rep_count"], 1)

    def test_switching_lead_leg_or_moving_feet_discards_partial_rep(self):
        wider = lunge_body()
        wider[28]["x"] = 30 / 640
        wider[27]["x"] = 550 / 640
        for observation in (lunge_body(mirrored=True), wider):
            with self.subTest():
                service = LungeService()
                hold(service, "up", 0)
                hold(service, "down", 0.4)
                self.assertEqual(service.update(observation, 640, 480, 0.7)["phase"], "ready")
                self.assertEqual(hold(service, "up", 0.8)["rep_count"], 0)

    def test_feet_together_and_horizontal_torso_are_not_evaluated(self):
        together = lunge_body()
        together[28]["x"] = together[27]["x"]
        horizontal = lunge_body()
        horizontal[11]["y"] = horizontal[23]["y"]
        for observation in (together, horizontal):
            self.assertEqual(LungeService().update(observation, 640, 480, 0)["status"], "waiting")

    def test_mirrored_stance_and_aspect_ratio(self):
        for mirrored in (False, True):
            service = LungeService()
            hold(service, "up", 0, width=1000, height=400, mirrored=mirrored)
            lower = hold(service, "down", 0.4, width=1000, height=400, mirrored=mirrored)
            self.assertEqual(lower["left_knee_angle"], 90)
            self.assertEqual(lower["right_knee_angle"], 90)
            self.assertEqual(hold(service, "up", 0.8, width=1000, height=400, mirrored=mirrored)["rep_count"], 1)

    def test_reset_and_instance_isolation(self):
        first, second = LungeService(), LungeService()
        hold(first, "up", 0)
        hold(first, "down", 0.4)
        self.assertEqual(hold(first, "up", 0.8)["rep_count"], 1)
        self.assertEqual(second.reset()["rep_count"], 0)
        self.assertEqual(first.reset()["rep_count"], 0)
        self.assertEqual(hold(first, "up", 0)["phase"], "up")

    def test_malformed_and_degenerate_joints(self):
        service = LungeService()
        malformed = lunge_body()
        malformed[25]["x"] = float("nan")
        with self.assertRaises(InvalidLandmarksError):
            service.update(malformed, 640, 480, 0)
        degenerate = lunge_body()
        degenerate[25] = dict(degenerate[23])
        self.assertEqual(service.update(degenerate, 640, 480, 0)["status"], "waiting")

    def test_only_primitive_counting_state_is_retained(self):
        service = LungeService()
        observation = lunge_body()
        original = copy.deepcopy(observation)
        service.update(observation, 640, 480, 0)
        self.assertEqual(observation, original)
        for name, value in vars(service).items():
            if name != "counter":
                self.assertIn(type(value), (int, float, str, type(None)))


if __name__ == "__main__":
    unittest.main()
