"""Exercise rules can be checked without a camera, model, or server."""
import copy
import unittest

from backend.services.pushup_service import InvalidLandmarksError, PushUpService


def body(position="up", width=640, height=480, side="left"):
    landmarks = [dict(x=0, y=0, visibility=0, presence=0) for _ in range(33)]
    # The bent arm has a 90-degree elbow; the straight arm has a 180-degree elbow.
    elbow = (100, 200) if position == "up" else (150, 200)
    points = [(100, 150), elbow, (100, 250), (250, 150), (350, 150), (450, 150)]
    indexes = (11, 13, 15, 23, 25, 27) if side == "left" else (12, 14, 16, 24, 26, 28)
    for index, (horizontal, vertical) in zip(indexes, points):
        landmarks[index] = dict(x=horizontal / width, y=vertical / height, visibility=1, presence=1)
    return landmarks


def hold(service, position, start, **kwargs):
    landmarks = body(position, **kwargs)
    service.update(landmarks, kwargs.get("width", 640), kwargs.get("height", 480), start)
    return service.update(landmarks, kwargs.get("width", 640), kwargs.get("height", 480), start + 0.2)


class PushUpTests(unittest.TestCase):
    def test_full_repetition_and_holding_upper_position(self):
        service = PushUpService()
        self.assertEqual(hold(service, "up", 0)["phase"], "up")
        self.assertEqual(hold(service, "down", 0.4)["rep_count"], 0)
        self.assertEqual(hold(service, "up", 0.8)["rep_count"], 1)
        self.assertEqual(hold(service, "up", 1.2)["rep_count"], 1)

    def test_lower_position_must_follow_confirmed_upper_position(self):
        service = PushUpService()
        hold(service, "down", 0)
        self.assertEqual(hold(service, "up", 0.4)["rep_count"], 0)

    def test_incomplete_repetition_and_jitter_are_not_counted(self):
        service = PushUpService()
        hold(service, "up", 0)
        for time, position in ((0.3, "down"), (0.35, "up"), (0.4, "down"), (0.45, "up")):
            service.update(body(position), 640, 480, time)
        self.assertEqual(hold(service, "up", 0.6)["rep_count"], 0)

    def test_middle_angle_breaks_a_candidate_hold(self):
        service = PushUpService()
        hold(service, "up", 0)
        service.update(body("down"), 640, 480, 0.3)
        middle = body()
        middle[13]["x"] = 125 / 640
        service.update(middle, 640, 480, 0.4)
        service.update(body("down"), 640, 480, 0.5)
        self.assertEqual(service.update(body(), 640, 480, 0.6)["phase"], "up")
        self.assertEqual(hold(service, "up", 0.8)["rep_count"], 0)

    def test_missing_low_confidence_and_outside_body_discard_incomplete_rep(self):
        observations = [[], body(), body()]
        observations[1][15]["presence"] = 0.2
        observations[2][27]["x"] = 1.2
        for observation in observations:
            with self.subTest(observation=bool(observation)):
                service = PushUpService()
                hold(service, "up", 0)
                hold(service, "down", 0.4)
                self.assertEqual(service.update(observation, 640, 480, 0.7)["status"], "waiting")
                self.assertEqual(hold(service, "up", 0.8)["rep_count"], 0)

    def test_lost_tracking_preserves_completed_count(self):
        service = PushUpService()
        hold(service, "up", 0)
        hold(service, "down", 0.4)
        hold(service, "up", 0.8)
        self.assertEqual(service.update([], 640, 480, 1.1)["rep_count"], 1)

    def test_long_gap_discards_incomplete_rep(self):
        service = PushUpService()
        hold(service, "up", 0)
        hold(service, "down", 0.4)
        self.assertEqual(hold(service, "up", 2)["rep_count"], 0)

    def test_standing_bent_body_and_unsupported_positions_are_rejected(self):
        bent = body()
        bent[23]["y"] = 300 / 480
        standing = body()
        for index in (23, 25, 27):
            standing[index]["x"] = 100 / 640
        unsupported = body()
        unsupported[15]["y"] = 150 / 480
        for observation in (bent, standing, unsupported):
            with self.subTest():
                result = PushUpService().update(observation, 640, 480, 0)
                self.assertEqual(result["status"], "waiting")

    def test_pixel_geometry_accounts_for_frame_aspect_ratio(self):
        service = PushUpService()
        hold(service, "up", 0, width=1000, height=300)
        result = hold(service, "down", 0.4, width=1000, height=300)
        self.assertEqual(result["elbow_angle"], 90)
        self.assertEqual(hold(service, "up", 0.8, width=1000, height=300)["rep_count"], 1)

    def test_arm_switch_discards_incomplete_rep(self):
        service = PushUpService()
        hold(service, "up", 0)
        hold(service, "down", 0.4)
        self.assertEqual(hold(service, "up", 0.8, side="right")["rep_count"], 0)

    def test_reset_and_separate_instances(self):
        first, second = PushUpService(), PushUpService()
        hold(first, "up", 0)
        hold(first, "down", 0.4)
        self.assertEqual(hold(first, "up", 0.8)["rep_count"], 1)
        self.assertEqual(second.rep_count, 0)
        result = first.reset()
        self.assertEqual(result["rep_count"], 0)
        self.assertEqual(result["phase"], "ready")
        self.assertEqual(hold(first, "up", 0)["rep_count"], 0)

    def test_malformed_observations_raise_explicit_errors(self):
        malformed = [None, {}, [dict(x=0)], body(), body()]
        malformed[3][11]["x"] = float("nan")
        malformed[4][11]["visibility"] = 2
        for observation in malformed:
            with self.subTest():
                with self.assertRaises(InvalidLandmarksError):
                    PushUpService().update(observation, 640, 480, 0)
        for width, height, time in ((0, 480, 0), (640, -1, 0), (640, 480, float("inf"))):
            with self.assertRaises(InvalidLandmarksError):
                PushUpService().update(body(), width, height, time)
        service = PushUpService()
        hold(service, "up", 1)
        with self.assertRaises(InvalidLandmarksError):
            service.update(body(), 640, 480, 0)
        self.assertEqual(service.current_phase, "ready")

    def test_observations_are_not_retained_or_modified(self):
        service = PushUpService()
        observation = body()
        original = copy.deepcopy(observation)
        service.update(observation, 640, 480, 0)
        self.assertEqual(observation, original)
        self.assertTrue(all(type(value) in (int, float, str, type(None)) for value in vars(service).values()))


if __name__ == "__main__":
    unittest.main()
