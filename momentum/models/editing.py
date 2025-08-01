"""
File: momentum/models/editing.py
"""
from pydantic import BaseModel, Field
from typing import List, Optional

class TextOverlay(BaseModel):
    """
    Defines the properties of a text overlay on a video shot.
    The 'text' field will be generated by the AI acting as a copywriter.
    """
    text: str = Field(..., description="The compelling, concise marketing text content to be displayed.")
    font_size: int = Field(..., description="The font size of the text.")
    position: str = Field(
        ...,
        description="The position of the overlay on the screen (e.g., 'top_center', 'bottom_left')."
    )
    style: str = Field(
        ...,
        description="The visual style of the text (e.g., 'minimalist', 'cinematic_title')."
    )

class Shot(BaseModel):
    """
    Represents a single, continuous clip in the final video timeline.
    """
    source_video: str = Field(
        ...,
        description="The path or identifier of the source video file for this shot."
    )
    start_time: float = Field(
        ...,
        description="The start time of the segment to be used from the source video, in seconds."
    )
    end_time: float = Field(
        ...,
        description="The end time of the segment to be used from the source video, in seconds."
    )
    transition_to_next: str = Field(
        "hard_cut",
        description="The transition effect to use when moving to the next shot (e.g., 'hard_cut', 'fade')."
    )
    text_overlay: Optional[TextOverlay] = Field(
        None,
        description="An optional text overlay to be displayed during this shot."
    )

class EditDecisionList(BaseModel):
    """
    The master blueprint for the final video, containing an ordered sequence of shots.
    This is the root object the AI must generate.
    """
    shots: List[Shot] = Field(
        ...,
        description="An ordered list of shots that constitute the final video timeline."
    )