"""Squats counting using a visible side's hip, knee, and ankle."""
import math

from backend.services.calculations import InvalidGeometryError, calculate_angle
from backend.services.observations import (
    InvalidLandmarksError, pixel_points, validate_observation, visible_joints,
)
from backend.services.repetition_counter import RepetitionCounter
from backend.services.posture_feedback import make_feedback

# Experimental side-view settings, not universal exercise standards.
UP_KNEE_ANGLE = 160
DOWN_KNEE_ANGLE = 105
MIN_TORSO_PIXELS = 20
MIN_SHIN_PIXELS = 25
MIN_TORSO_VERTICAL_RATIO = 0.35
HIP_BELOW_KNEE_ALLOWANCE = 0.25
BODY_SIDES = {"left": (11, 23, 25, 27), "right": (12, 24, 26, 28)}


class SquatsService:
    def __init__(self):
        self.counter = RepetitionCounter()
        self.selected_side = None

    def reset(self):
        self.counter.reset()
        self.selected_side = None
        return self._result("waiting", "Start standing with your whole body visible.")

    def _discard_incomplete_rep(self):
        self.counter.discard_incomplete_rep()
        self.selected_side = None

    def _result(self, status, message, knee_angle=None, torso_lean_angle=None, feedback=None):
        if feedback is None:
            feedback = make_feedback(
                "observed" if status == "tracking" else "unavailable",
                "visible_leg" if status == "tracking" else "tracking_unavailable",
                "Keep the same leg visible while you move." if status == "tracking" else message,
                self.selected_side,
            )
        return {
            **self.counter.result(status, message),
            "knee_angle": round(knee_angle, 1) if knee_angle is not None else None,
            "torso_lean_angle": round(torso_lean_angle, 1) if torso_lean_angle is not None else None,
            "feedback": feedback,
        }

    def _choose_side(self, landmarks):
        if self.selected_side is not None:
            indexes = BODY_SIDES[self.selected_side]
            return self.selected_side if visible_joints(landmarks, indexes) else None
        visible_sides = [side for side, indexes in BODY_SIDES.items() if visible_joints(landmarks, indexes)]
        if not visible_sides:
            return None
        return max(visible_sides, key=lambda side: min(
            min(landmarks[index]["visibility"], landmarks[index]["presence"])
            for index in BODY_SIDES[side]
        ))

    def update(self, landmarks, width, height, observed_at):
        try:
            validate_observation(landmarks, width, height, observed_at, self.counter.last_observed_at)
        except InvalidLandmarksError:
            self._discard_incomplete_rep()
            raise
        if self.counter.track_time(observed_at):
            self.selected_side = None

        side = self._choose_side(landmarks)
        if side is None:
            self._discard_incomplete_rep()
            return self._result("waiting", "Use a side view. Keep your shoulder, hip, knee, and ankle visible.")

        shoulder, hip, knee, ankle = pixel_points(landmarks, BODY_SIDES[side], width, height)
        try:
            knee_angle = calculate_angle(hip, knee, ankle)
        except InvalidGeometryError:
            self._discard_incomplete_rep()
            return self._result("waiting", "Move into view so your leg joints are distinguishable.")

        torso_length = math.dist(shoulder, hip)
        shin_length = math.dist(knee, ankle)
        torso_lean_angle = math.degrees(math.atan2(abs(shoulder[0] - hip[0]), hip[1] - shoulder[1]))
        feedback = self._check_setup(shoulder, hip, knee, ankle, torso_length, shin_length, side)
        if feedback is not None:
            self._discard_incomplete_rep()
            return self._result("waiting", feedback["message"], knee_angle, torso_lean_angle, feedback)

        self.selected_side = side
        position = None
        if knee_angle >= UP_KNEE_ANGLE:
            position = "up"
        elif knee_angle <= DOWN_KNEE_ANGLE:
            position = "down"
        self.counter.confirm_position(position, observed_at)

        messages = {
            "ready": "Hold a standing position to begin.",
            "up": "Bend your knees and hips to lower with control.",
            "down": "Return to standing to complete one repetition.",
        }
        feedback = None
        if position is None and self.counter.current_phase == "up":
            feedback = make_feedback("observed", "lower_position_unconfirmed", "Lower position is not confirmed yet.", side)
        elif position is None and self.counter.current_phase == "down":
            feedback = make_feedback("observed", "upper_position_unconfirmed", "Return to standing to confirm the upper position.", side)
        return self._result("tracking", messages[self.counter.current_phase], knee_angle, torso_lean_angle, feedback)

    def _check_setup(self, shoulder, hip, knee, ankle, torso_length, shin_length, side):
        if torso_length < MIN_TORSO_PIXELS or shin_length < MIN_SHIN_PIXELS:
            return make_feedback("unavailable", "body_too_small", "Move closer while keeping your whole leg in view.", side)
        if hip[1] - shoulder[1] < torso_length * MIN_TORSO_VERTICAL_RATIO:
            return make_feedback("adjust", "torso_position", "Bring your torso toward an upright position.", side)
        if knee[1] >= ankle[1] or hip[1] > knee[1] + shin_length * HIP_BELOW_KNEE_ALLOWANCE:
            return make_feedback("unavailable", "leg_view_needed", "Adjust the side view so your hip, knee, and ankle are clearly separated.", side)
        return None
