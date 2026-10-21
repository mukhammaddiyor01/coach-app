"""Check geometry independently of the camera and server."""
import unittest

from backend.services.calculations import InvalidGeometryError, calculate_angle


class AngleCalculationTests(unittest.TestCase):
    def test_right_angle(self):
        self.assertAlmostEqual(calculate_angle((1, 0), (0, 0), (0, 1)), 90)

    def test_straight_line(self):
        self.assertAlmostEqual(calculate_angle((-1, 0), (0, 0), (1, 0)), 180)

    def test_same_direction(self):
        self.assertAlmostEqual(calculate_angle((1, 0), (0, 0), (2, 0)), 0)

    def test_translation_and_uniform_scale_preserve_angle(self):
        self.assertAlmostEqual(calculate_angle((12, 10), (10, 10), (10, 12)), 90)

    def test_degenerate_or_non_finite_points_are_rejected(self):
        examples = [
            ((0, 0), (0, 0), (1, 0)),
            ((float('nan'), 0), (0, 0), (1, 0)),
            ((float('inf'), 0), (0, 0), (1, 0)),
            ((1,), (0, 0), (1, 0)),
            (("one", 0), (0, 0), (1, 0)),
        ]
        for points in examples:
            with self.subTest(points=points):
                with self.assertRaises(InvalidGeometryError):
                    calculate_angle(*points)


if __name__ == "__main__":
    unittest.main()
