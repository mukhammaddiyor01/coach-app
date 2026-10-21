"""Public response formats. These describe data, not exercise rules."""
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
