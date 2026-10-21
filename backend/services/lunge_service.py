"""Count stationary lunges when both visible knees bend and straighten."""
import math

from backend.services.calculations import InvalidGeometryError, calculate_angle
from backend.services.observations import (
    InvalidLandmarksError, pixel_points, validate_observation, visible_joints,
)
from backend.services.repetition_counter import RepetitionCounter

# Experimental side-view settings for stationary lunges.
UP_KNEE_ANGLE = 150
DOWN_KNEE_ANGLE = 110
MIN_SEGMENT_PIXELS = 25
MIN_TORSO_PIXELS = 20
MIN_TORSO_VERTICAL_RATIO = 0.35
MIN_STANCE_TO_SHIN_RATIO = 0.7
MAX_ANKLE_HEIGHT_TO_SHIN_RATIO = 0.5
MIN_HIP_HEIGHT_TO_SHIN_RATIO = 0.2
MAX_STANCE_RATIO_CHANGE = 0.35
LEG_INDEXES = (23, 25, 27, 24, 26, 28)
TORSO_SIDES = {"left": (11, 23), "right": (12, 24)}


class LungeService:
    def __init__(self):
        self.counter = RepetitionCounter()
        self._clear_stance()

    def _clear_stance(self):
        self.selected_side = None
        self.stance_direction = None
        self.stance_ratio = None

    def reset(self):
        self.counter.reset()
        self._clear_stance()
        return self._result("waiting", "Start upright in a split stance with both legs visible.")

    def _discard_incomplete_rep(self):
        self.counter.discard_incomplete_rep()
        self._clear_stance()

    def _result(self, status, message, left_angle=None, right_angle=None):
        return {
            **self.counter.result(status, message),
            "left_knee_angle": round(left_angle, 1) if left_angle is not None else None,
            "right_knee_angle": round(right_angle, 1) if right_angle is not None else None,
        }

    def _choose_torso_side(self, landmarks):
        if self.selected_side is not None:
            indexes = TORSO_SIDES[self.selected_side]
            return self.selected_side if visible_joints(landmarks, indexes) else None
        for side, indexes in TORSO_SIDES.items():
            if visible_joints(landmarks, indexes):
                return side
        return None

    def update(self, landmarks, width, height, observed_at):
        try:
            validate_observation(landmarks, width, height, observed_at, self.counter.last_observed_at)
        except InvalidLandmarksError:
            self._discard_incomplete_rep()
            raise
        if self.counter.track_time(observed_at):
            self._clear_stance()

        side = self._choose_torso_side(landmarks)
        if side is None or not visible_joints(landmarks, LEG_INDEXES):
            self._discard_incomplete_rep()
            return self._result("waiting", "Use a side view with both hips, knees, and ankles visible.")

        left_hip, left_knee, left_ankle, right_hip, right_knee, right_ankle = pixel_points(
            landmarks, LEG_INDEXES, width, height,
        )
        shoulder, hip = pixel_points(landmarks, TORSO_SIDES[side], width, height)
        try:
            left_angle = calculate_angle(left_hip, left_knee, left_ankle)
            right_angle = calculate_angle(right_hip, right_knee, right_ankle)
        except InvalidGeometryError:
            self._discard_incomplete_rep()
            return self._result("waiting", "Move into view so both legs are distinguishable.")

        shin_lengths = (math.dist(left_knee, left_ankle), math.dist(right_knee, right_ankle))
        thigh_lengths = (math.dist(left_hip, left_knee), math.dist(right_hip, right_knee))
        mean_shin_length = sum(shin_lengths) / 2
        torso_length = math.dist(shoulder, hip)
        if min(*shin_lengths, *thigh_lengths) < MIN_SEGMENT_PIXELS or torso_length < MIN_TORSO_PIXELS:
            self._discard_incomplete_rep()
            return self._result("waiting", "Keep your whole body clearly visible at a useful distance.")

        ankle_separation = right_ankle[0] - left_ankle[0]
        # Torso length gives a stable scale when knees bend or feet move.
        stance_ratio = abs(ankle_separation) / torso_length
        stance_direction = 1 if ankle_separation > 0 else -1
        is_split_stance = abs(ankle_separation) >= mean_shin_length * MIN_STANCE_TO_SHIN_RATIO
        ankles_level = abs(left_ankle[1] - right_ankle[1]) <= mean_shin_length * MAX_ANKLE_HEIGHT_TO_SHIN_RATIO
        is_upright = hip[1] - shoulder[1] >= torso_length * MIN_TORSO_VERTICAL_RATIO
        hips_above_feet = max(left_hip[1], right_hip[1]) < min(left_ankle[1], right_ankle[1]) - mean_shin_length * MIN_HIP_HEIGHT_TO_SHIN_RATIO
        if not (is_split_stance and ankles_level and is_upright and hips_above_feet):
            self._discard_incomplete_rep()
            return self._result("waiting", "Stand side-on with one foot forward and the other behind.", left_angle, right_angle)

        # A changed lead leg or large stance change starts a fresh sequence.
        if self.stance_direction is not None:
            changed_leg = stance_direction != self.stance_direction
            changed_width = abs(stance_ratio - self.stance_ratio) > self.stance_ratio * MAX_STANCE_RATIO_CHANGE
            if changed_leg or changed_width:
                self._discard_incomplete_rep()
                return self._result("waiting", "Keep your feet in place, then hold the upper position again.", left_angle, right_angle)

        self.selected_side = side
        self.stance_direction = stance_direction
        if self.stance_ratio is None:
            self.stance_ratio = stance_ratio
        position = None
        if min(left_angle, right_angle) >= UP_KNEE_ANGLE:
            position = "up"
        elif max(left_angle, right_angle) <= DOWN_KNEE_ANGLE:
            position = "down"
        self.counter.confirm_position(position, observed_at)
        messages = {
            "ready": "Hold the upper split-stance position to begin.",
            "up": "Bend both knees to lower in place.",
            "down": "Return to the upper position to complete one repetition.",
        }
        return self._result("tracking", messages[self.counter.current_phase], left_angle, right_angle)
