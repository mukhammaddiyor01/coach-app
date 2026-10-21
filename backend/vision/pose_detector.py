"""Convert one JPEG frame into body landmarks without saving user data."""
from io import BytesIO
from pathlib import Path
from threading import Lock

import numpy as np
from PIL import Image, UnidentifiedImageError

MODEL_PATH = Path(__file__).resolve().parents[2] / "models" / "pose_landmarker.task"
MAX_FRAME_BYTES = 1_000_000
MAX_FRAME_SIDE = 1280


class InvalidFrameError(ValueError):
    """The input is not a supported, bounded JPEG frame."""


class ModelUnavailableError(RuntimeError):
    """The local pose model is missing or could not be initialized."""


class PoseBusyError(RuntimeError):
    """The detector is already processing a frame."""


class PoseDetectionError(RuntimeError):
    """The model could not process this frame."""


def decode_frame(frame_bytes: bytes) -> np.ndarray:
    if not frame_bytes or len(frame_bytes) > MAX_FRAME_BYTES:
        raise InvalidFrameError("Send a JPEG frame smaller than 1 MB.")

    try:
        with Image.open(BytesIO(frame_bytes)) as image:
            if image.format != "JPEG":
                raise InvalidFrameError("Only JPEG frames are supported.")

            width, height = image.size
            if not (0 < width <= MAX_FRAME_SIDE and 0 < height <= MAX_FRAME_SIDE):
                raise InvalidFrameError("Frame dimensions must not exceed 1280 pixels.")

            return np.asarray(image.convert("RGB"))
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise InvalidFrameError("The JPEG frame could not be read.") from None


class PoseDetector:
    def __init__(self, model_path: Path = MODEL_PATH):
        self.model_path = model_path
        self._landmarker = None
        self._lock = Lock()

    def _load_model(self):
        if self._landmarker is not None:
            return

        if not self.model_path.is_file():
            raise ModelUnavailableError("Run python download_model.py before body detection.")

        try:
            import mediapipe as mp
            from mediapipe.tasks.python import vision

            options = vision.PoseLandmarkerOptions(
                base_options=mp.tasks.BaseOptions(model_asset_path=str(self.model_path)),
                running_mode=vision.RunningMode.IMAGE,
                num_poses=1,
                min_pose_detection_confidence=0.6,
                min_pose_presence_confidence=0.6,
            )
            self._landmarker = vision.PoseLandmarker.create_from_options(options)
        except (ImportError, OSError, RuntimeError, ValueError):
            raise ModelUnavailableError("The local pose model could not start.") from None

    def detect(self, frame_bytes: bytes) -> dict:
        # IMAGE mode has no shared video history or repetition state between users.
        if not self._lock.acquire(blocking=False):
            raise PoseBusyError("The detector is busy. Try the next frame.")

        try:
            rgb_frame = decode_frame(frame_bytes)
            self._load_model()

            import mediapipe as mp

            image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            try:
                result = self._landmarker.detect(image)
            except (RuntimeError, ValueError):
                raise PoseDetectionError("Body detection could not process this frame.") from None

            landmarks = []
            if result.pose_landmarks:
                landmarks = [
                    {
                        "x": float(point.x),
                        "y": float(point.y),
                        "z": float(point.z),
                        "visibility": float(point.visibility),
                        "presence": float(point.presence),
                    }
                    for point in result.pose_landmarks[0]
                ]

            height, width = rgb_frame.shape[:2]
            return {"landmarks": landmarks, "width": width, "height": height}
        finally:
            self._lock.release()

    def close(self):
        with self._lock:
            if self._landmarker is not None:
                self._landmarker.close()
                self._landmarker = None


# Only model weights are reused. Input frames and results are not stored here.
pose_detector = PoseDetector()


def get_pose_detector() -> PoseDetector:
    return pose_detector
