"""Public response formats. These describe data, not exercise rules."""
from typing import Literal

from pydantic import BaseModel, Field, FiniteFloat


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


class WorkoutResult(BaseModel):
    rep_count: int = Field(ge=0)
    phase: Literal["ready", "up", "down"]
    status: Literal["waiting", "tracking"]
    message: str
    elbow_angle: FiniteFloat | None
    body_angle: FiniteFloat | None


class SessionResult(BaseModel):
    session_id: str
    workout: WorkoutResult


class PushUpResult(PoseResult):
    workout: WorkoutResult
