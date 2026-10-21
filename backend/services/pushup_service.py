"""Push Up counting rules, independent of the camera and web framework."""
import math

from backend.services.calculations import InvalidGeometryError, calculate_angle

# Prototype settings; these are not universal exercise standards.
UP_ELBOW_ANGLE = 155
DOWN_ELBOW_ANGLE = 100
MIN_BODY_ANGLE = 160
MIN_KNEE_ANGLE = 160
MIN_CONFIDENCE = 0.65
POSITION_HOLD_SECONDS = 0.15
MAX_OBSERVATION_GAP_SECONDS = 1.0
MIN_TORSO_PIXELS = 20
BODY_SIDES = {
    "left": (11, 13, 15, 23, 25, 27),
    "right": (12, 14, 16, 24, 26, 28),
}


class InvalidLandmarksError(ValueError):
    """An observation contains malformed landmark data."""


class PushUpService:
    """Remember only counting state for one camera session."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.rep_count = 0
        self.last_observed_at = None
        self._discard_incomplete_rep()
        return self._result("waiting", "Start in the upper Push Up position.")

    def _discard_incomplete_rep(self):
        self.current_phase = "ready"
        self.selected_side = None
        self.candidate_position = None
        self.candidate_since = None

    def _result(self, status, message, elbow_angle=None, body_angle=None):
        return {
            "rep_count": self.rep_count,
            "phase": self.current_phase,
            "status": status,
            "message": message,
            "elbow_angle": round(elbow_angle, 1) if elbow_angle is not None else None,
            "body_angle": round(body_angle, 1) if body_angle is not None else None,
        }

    def update(self, landmarks, width, height, observed_at):
        """Evaluate one observation using pixel geometry and monotonic seconds."""
        try:
            self._validate_observation(landmarks, width, height, observed_at)
        except InvalidLandmarksError:
            self._discard_incomplete_rep()
            raise

        if self.last_observed_at is not None:
            if observed_at - self.last_observed_at > MAX_OBSERVATION_GAP_SECONDS:
                self._discard_incomplete_rep()
        self.last_observed_at = observed_at

        side = self._choose_visible_side(landmarks)
        if side is None:
            self._discard_incomplete_rep()
            return self._result("waiting", "Keep your shoulder, arm, hip, knee, and ankle in view.")

        points = [
            (landmarks[index]["x"] * width, landmarks[index]["y"] * height)
            for index in BODY_SIDES[side]
        ]
        shoulder, elbow, wrist, hip, knee, ankle = points
        try:
            elbow_angle = calculate_angle(shoulder, elbow, wrist)
            body_angle = calculate_angle(shoulder, hip, ankle)
            knee_angle = calculate_angle(hip, knee, ankle)
        except InvalidGeometryError:
            self._discard_incomplete_rep()
            return self._result("waiting", "Move into view so your joints are distinguishable.")

        torso_length = math.dist(shoulder, hip)
        body_width = abs(ankle[0] - shoulder[0])
        body_height = abs(ankle[1] - shoulder[1])
        is_horizontal = body_width >= torso_length and body_height <= body_width * 0.6
        is_supported = wrist[1] - shoulder[1] >= torso_length * 0.1
        is_body_straight = body_angle >= MIN_BODY_ANGLE and knee_angle >= MIN_KNEE_ANGLE

        if torso_length < MIN_TORSO_PIXELS or not (is_horizontal and is_supported and is_body_straight):
            self._discard_incomplete_rep()
            return self._result(
                "waiting", "Use a side view with your whole body in a straight plank position.",
                elbow_angle, body_angle,
            )

        self.selected_side = side
        self._confirm_position(elbow_angle, observed_at)
        messages = {
            "ready": "Hold the upper position to begin.",
            "up": "Bend your elbows to reach the lower position.",
            "down": "Return to the upper position to complete one repetition.",
        }
        return self._result("tracking", messages[self.current_phase], elbow_angle, body_angle)

    def _validate_observation(self, landmarks, width, height, observed_at):
        for dimension in (width, height):
            if type(dimension) is not int or dimension <= 0:
                raise InvalidLandmarksError("Frame dimensions must be positive integers.")
        if type(observed_at) not in (int, float) or not math.isfinite(observed_at) or observed_at < 0:
            raise InvalidLandmarksError("Observation time must be a finite, nonnegative number.")
        if self.last_observed_at is not None and observed_at < self.last_observed_at:
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

    def _choose_visible_side(self, landmarks):
        if not landmarks:
            return None
        visible_sides = {}
        for side, indexes in BODY_SIDES.items():
            joints = [landmarks[index] for index in indexes]
            confidence = min(min(joint["visibility"], joint["presence"]) for joint in joints)
            in_frame = all(0 <= joint["x"] <= 1 and 0 <= joint["y"] <= 1 for joint in joints)
            if confidence >= MIN_CONFIDENCE and in_frame:
                visible_sides[side] = confidence

        # Switching arms halfway through a repetition could create a false transition.
        if self.selected_side is not None:
            return self.selected_side if self.selected_side in visible_sides else None
        return max(visible_sides, key=visible_sides.get) if visible_sides else None

    def _confirm_position(self, elbow_angle, observed_at):
        position = None
        if elbow_angle >= UP_ELBOW_ANGLE:
            position = "up"
        elif elbow_angle <= DOWN_ELBOW_ANGLE:
            position = "down"

        if position != self.candidate_position:
            self.candidate_position = position
            self.candidate_since = observed_at
            return
        if position is None or observed_at - self.candidate_since < POSITION_HOLD_SECONDS:
            return

        if position == "down" and self.current_phase == "up":
            self.current_phase = "down"
        elif position == "up":
            if self.current_phase == "down":
                self.rep_count += 1
            self.current_phase = "up"
