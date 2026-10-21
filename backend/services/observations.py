"""Shared validation and visible-joint helpers for plain Python services."""
import math

MIN_CONFIDENCE = 0.65


class InvalidLandmarksError(ValueError):
    """An observation contains malformed landmark data."""


def validate_observation(landmarks, width, height, observed_at, previous_time):
    for dimension in (width, height):
        if type(dimension) is not int or dimension <= 0:
            raise InvalidLandmarksError("Frame dimensions must be positive integers.")
    if type(observed_at) not in (int, float) or not math.isfinite(observed_at) or observed_at < 0:
        raise InvalidLandmarksError("Observation time must be a finite, nonnegative number.")
    if previous_time is not None and observed_at < previous_time:
        raise InvalidLandmarksError("Observation time must not move backwards.")
    if not isinstance(landmarks, list) or len(landmarks) not in (0, 33):
        raise InvalidLandmarksError("Expected either no body or 33 body landmarks.")
    for landmark in landmarks:
        if not isinstance(landmark, dict):
            raise InvalidLandmarksError("Each landmark must contain named coordinates.")
        for name in ("x", "y", "visibility", "presence"):
            value = landmark.get(name)
            if type(value) not in (int, float) or not math.isfinite(value):
                raise InvalidLandmarksError("Landmark coordinates and confidence must be finite numbers.")
        if not 0 <= landmark["visibility"] <= 1 or not 0 <= landmark["presence"] <= 1:
            raise InvalidLandmarksError("Landmark confidence must be between zero and one.")



def visible_joints(landmarks, indexes):
    if not landmarks:
        return False
    for index in indexes:
        joint = landmarks[index]
        if min(joint["visibility"], joint["presence"]) < MIN_CONFIDENCE:
            return False
        if not (0 <= joint["x"] <= 1 and 0 <= joint["y"] <= 1):
            return False
    return True


def pixel_points(landmarks, indexes, width, height):
    return [
        (landmarks[index]["x"] * width, landmarks[index]["y"] * height)
        for index in indexes
    ]
