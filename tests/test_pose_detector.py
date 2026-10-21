"""Validate image boundaries without a camera or an external image service."""
from io import BytesIO
from pathlib import Path
import unittest

from PIL import Image

from backend.vision.pose_detector import (
    InvalidFrameError,
    ModelUnavailableError,
    PoseBusyError,
    PoseDetector,
    decode_frame,
)


def make_image(format="JPEG", size=(64, 48)):
    output = BytesIO()
    Image.new("RGB", size, color="black").save(output, format=format)
    return output.getvalue()


class FrameValidationTests(unittest.TestCase):
    def test_jpeg_decodes_to_rgb_without_changing_aspect_ratio(self):
        frame = decode_frame(make_image())
        self.assertEqual(frame.shape, (48, 64, 3))

    def test_empty_corrupt_or_large_inputs_are_rejected(self):
        for data in (b"", b"not an image", b"x" * 1_000_001):
            with self.subTest(size=len(data)):
                with self.assertRaises(InvalidFrameError):
                    decode_frame(data)

    def test_non_jpeg_images_are_rejected(self):
        with self.assertRaises(InvalidFrameError):
            decode_frame(make_image(format="PNG"))

    def test_image_dimensions_are_checked_before_pixel_conversion(self):
        with self.assertRaises(InvalidFrameError):
            decode_frame(make_image(size=(1281, 10)))

    def test_missing_model_returns_a_safe_setup_message(self):
        detector = PoseDetector(Path("models/missing-test-model.task"))
        with self.assertRaisesRegex(ModelUnavailableError, "download_model.py"):
            detector.detect(make_image())

    def test_busy_detector_rejects_overlap_instead_of_queuing_frames(self):
        detector = PoseDetector()
        detector._lock.acquire()
        try:
            with self.assertRaises(PoseBusyError):
                detector.detect(make_image())
        finally:
            detector._lock.release()

    def test_invalid_frame_releases_the_detector_lock(self):
        detector = PoseDetector()
        with self.assertRaises(InvalidFrameError):
            detector.detect(b"bad image")
        self.assertTrue(detector._lock.acquire(blocking=False))
        detector._lock.release()


if __name__ == "__main__":
    unittest.main()
