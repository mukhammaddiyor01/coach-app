"""A lower start is convenient without reviving interrupted repetitions."""
import unittest

from backend.services.lunge_service import LungeService
from backend.services.pushup_service import PushUpService
from test_lunge_service import lunge_body
from test_pushup_service import body


class FlexibleStartTests(unittest.TestCase):
    def exercise_services(self):
        return ((PushUpService, body), (LungeService, lunge_body))

    def hold(self, service, make_body, position, time):
        service.update(make_body(position), 640, 480, time)
        return service.update(make_body(position), 640, 480, time + 0.2)

    def test_single_lower_frame_cannot_start_a_repetition(self):
        for service_type, make_body in self.exercise_services():
            with self.subTest(service=service_type.__name__):
                service = service_type()
                service.update(make_body("down"), 640, 480, 0)
                result = self.hold(service, make_body, "up", 0.05)
                self.assertEqual(result["rep_count"], 0)

    def test_tracking_loss_or_gap_requires_a_new_upper_start(self):
        for service_type, make_body in self.exercise_services():
            for interruption in ("missing", "gap"):
                with self.subTest(service=service_type.__name__, interruption=interruption):
                    service = service_type()
                    self.hold(service, make_body, "down", 0)
                    if interruption == "missing":
                        service.update([], 640, 480, 0.3)
                    self.hold(service, make_body, "down", 2)
                    result = self.hold(service, make_body, "up", 2.4)
                    self.assertEqual(result["rep_count"], 0)
                    self.hold(service, make_body, "down", 2.8)
                    self.assertEqual(self.hold(service, make_body, "up", 3.2)["rep_count"], 1)

    def test_reset_allows_lower_start_again_and_instances_are_independent(self):
        for service_type, make_body in self.exercise_services():
            with self.subTest(service=service_type.__name__):
                first, second = service_type(), service_type()
                self.hold(first, make_body, "down", 0)
                self.assertEqual(self.hold(first, make_body, "up", 0.4)["rep_count"], 1)
                first.reset()
                for service in (first, second):
                    self.hold(service, make_body, "down", 0)
                    self.assertEqual(self.hold(service, make_body, "up", 0.4)["rep_count"], 1)
