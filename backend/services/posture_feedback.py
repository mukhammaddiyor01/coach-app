"""Plain data describing only posture features visible to an exercise service."""


def make_feedback(level, code, message, side=None):
    """Describe an observation, without claiming the whole exercise is correct."""
    return {"level": level, "code": code, "message": message, "side": side}
