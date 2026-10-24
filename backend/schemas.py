"""Public response formats. These describe data, not exercise rules."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat


class PoseLandmark(BaseModel):
    x: FiniteFloat
    y: FiniteFloat
    z: FiniteFloat
    visibility: FiniteFloat
    presence: FiniteFloat


class PoseResult(BaseModel):
    landmarks: list[PoseLandmark] = Field(max_length=33)
    width: int = Field(gt=0, le=1280)
    height: int = Field(gt=0, le=1280)


class PostureFeedback(BaseModel):
    level: Literal["observed", "adjust", "unavailable"]
    code: str
    message: str
    side: Literal["left", "right"] | None = None


class WorkoutResult(BaseModel):
    rep_count: int = Field(ge=0)
    phase: Literal["ready", "up", "down"]
    status: Literal["waiting", "tracking"]
    message: str
    feedback: PostureFeedback
    torso_lean_angle: FiniteFloat | None = None
    elbow_angle: FiniteFloat | None = None
    body_angle: FiniteFloat | None = None
    knee_angle: FiniteFloat | None = None
    left_knee_angle: FiniteFloat | None = None
    right_knee_angle: FiniteFloat | None = None


class SessionResult(BaseModel):
    session_id: str
    exercise_id: Literal["pushup", "squats", "lunge"]
    workout: WorkoutResult


class WorkoutPoseResult(PoseResult):
    workout: WorkoutResult


class CountCheckInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    manual_count: int = Field(strict=True, ge=0, le=1000)
    observed_count: int = Field(strict=True, ge=0, le=1000)


class CountCheckResult(BaseModel):
    exercise_id: Literal["pushup", "squats", "lunge"]
    manual_count: int
    observed_count: int
    difference: int
    outcome: Literal["match", "extra", "missed"]
    message: str
