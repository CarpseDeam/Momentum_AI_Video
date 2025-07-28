"""
File: momentum/models/analysis.py
"""
from pydantic import BaseModel, Field
from typing import List

class VideoSceneAnalysis(BaseModel):
    """
    Represents the structured analysis of a single video clip as defined
    by the multimodal AI model's output specification.
    """
    description: str = Field(
        ...,
        description="A brief, one-sentence description of the clip's content."
    )
    key_moment_timestamp: float = Field(
        ...,
        description="The estimated time in seconds of the most interesting or action-packed moment.",
        gt=0.0
    )

class AudioAnalysis(BaseModel):
    """
    Represents the structured analysis of an audio file, containing the
    detected beat timestamps.
    """
    beat_timestamps: List[float] = Field(
        default_factory=list,
        description="A list of floating-point numbers, where each number is a beat's timestamp in seconds."
    )