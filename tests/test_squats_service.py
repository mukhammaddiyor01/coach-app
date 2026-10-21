"""Synthetic leg positions verify Squats rules without native vision libraries."""
import copy
import unittest

from backend.services.observations import InvalidLandmarksError
from backend.services.squats_service import SquatsService


def squat_body(position="up", width=640, height=480, side="left"):
    landmarks = [dict(x=0, y=0, visibility=0, presence=0) for _ in range(33)]
    points = [(240, 60), (240, 180), (240, 280), (240, 380)]
    if position == "down":
        points = [(140, 60), (140, 200), (240, 200), (240, 300)]
    if position == "middle":
        points = [(180, 60), (180, 180), (240, 240), (240, 340)]
    indexes = (11, 23, 25, 27) if side == "left" else (12, 24, 26, 28)
    for index, (horizontal, vertical) in zip(indexes, points):
        landmarks[index] = dict(x=horizontal / width, y=vertical / height, visibility=1, presence=1)
    return landmarks


def hold(service, position, start, **kwargs):
    observation = squat_body(position, **kwargs)
    dimensions = (kwargs.get("width", 640), kwargs.get("height", 480))
    service.update(observation, *dimensions, start)
    return service.update(observation, *dimensions, start + 0.2)


class SquatsServiceTests(unittest.TestCase):
    def test_complete_repetitions_and_holding_do_not_overcount(self):
        service = SquatsService()
        for start in (0, 1.2):
            hold(service, "up", start)
            hold(service, "down", start + 0.4)
            result = hold(service, "up", start + 0.8)
        self.assertEqual(result["rep_count"], 2)
        self.assertEqual(hold(service, "up", 2.4)["rep_count"], 2)

    def test_bottom_start_and_half_movements_do_not_count(self):
        service = SquatsService()
        hold(service, "down", 0)
        hold(service, "up", 0.4)
        hold(service, "middle", 0.8)
        self.assertEqual(hold(service, "up", 1.2)["rep_count"], 0)

    def test_short_jitter_and_middle_positions_interrupt_candidate_holds(self):
        service = SquatsService()
        hold(service, "up", 0)
        for time, position in ((0.3, "down"), (0.35, "middle"), (0.4, "down"), (0.45, "up")):
            service.update(squat_body(position), 640, 480, time)
        self.assertEqual(hold(service, "up", 0.6)["rep_count"], 0)

    def test_lost_body_bad_confidence_and_side_changes_discard_partial_rep(self):
        hidden = squat_body()
        hidden[25]["visibility"] = 0.2
        outside = squat_body()
        outside[27]["y"] = 1.2
        for observation in ([], hidden, outside, squat_body(side="right")):
            with self.subTest():
                service = SquatsService()
                hold(service, "up", 0)
                hold(service, "down", 0.4)
                self.assertEqual(service.update(observation, 640, 480, 0.7)["phase"], "ready")
                self.assertEqual(hold(service, "up", 0.8)["rep_count"], 0)

    def test_gap_preserves_total_but_discards_partial_rep(self):
        service = SquatsService()
        hold(service, "up", 0)
        hold(service, "down", 0.4)
        hold(service, "up", 0.8)
        hold(service, "down", 1.2)
        self.assertEqual(hold(service, "up", 3)["rep_count"], 1)

    def test_horizontal_or_degenerate_body_is_not_evaluated(self):
        lying = squat_body()
        lying[11]["y"] = lying[23]["y"]
        degenerate = squat_body()
        degenerate[25] = dict(degenerate[23])
        for observation in (lying, degenerate):
            self.assertEqual(SquatsService().update(observation, 640, 480, 0)["status"], "waiting")

    def test_aspect_ratio_and_either_visible_side(self):
        for side in ("left", "right"):
            service = SquatsService()
            hold(service, "up", 0, width=1000, height=400, side=side)
            lower = hold(service, "down", 0.4, width=1000, height=400, side=side)
            self.assertEqual(lower["knee_angle"], 90)
            self.assertEqual(hold(service, "up", 0.8, width=1000, height=400, side=side)["rep_count"], 1)

    def test_reset_and_instance_isolation(self):
        first, second = SquatsService(), SquatsService()
        hold(first, "up", 0)
        hold(first, "down", 0.4)
        self.assertEqual(hold(first, "up", 0.8)["rep_count"], 1)
        self.assertEqual(second.reset()["rep_count"], 0)
        self.assertEqual(first.reset()["rep_count"], 0)
        self.assertEqual(hold(first, "up", 0)["phase"], "up")

    def test_invalid_observation_discards_partial_rep(self):
        service = SquatsService()
        hold(service, "up", 0)
        hold(service, "down", 0.4)
        malformed = squat_body()
        malformed[25]["x"] = float("nan")
        with self.assertRaises(InvalidLandmarksError):
            service.update(malformed, 640, 480, 0.7)
        self.assertEqual(hold(service, "up", 0.8)["rep_count"], 0)
        with self.assertRaises(InvalidLandmarksError):
            service.update([], 640, 480, 0)

    def test_landmarks_are_not_retained_or_modified(self):
        service = SquatsService()
        observation = squat_body()
        original = copy.deepcopy(observation)
        service.update(observation, 640, 480, 0)
        self.assertEqual(observation, original)
        self.assertEqual(set(vars(service)), {"counter", "selected_side"})
        self.assertTrue(all(type(value) in (int, float, str, type(None)) for value in vars(service.counter).values()))


if __name__ == "__main__":
    unittest.main()
