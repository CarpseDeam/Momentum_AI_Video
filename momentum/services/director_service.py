"""
File: momentum/services/director_service.py
"""
import logging
from typing import Dict, List

from momentum.components.ai_client import MultimodalAIClient
from momentum.models.analysis import AudioAnalysis, VideoSceneAnalysis
from momentum.models.editing import EditDecisionList

logger = logging.getLogger(__name__)

class DirectorService:
    """
    Contains the logic for creating an Edit Decision List (EDL) by interpreting
    analysis data and creative goals using an AI client.
    """
    def __init__(self, ai_client: MultimodalAIClient):
        """
        Initializes the DirectorService with a MultimodalAIClient instance.

        Args:
            ai_client: An instance of MultimodalAIClient used for AI-driven EDL generation.
        """
        if not isinstance(ai_client, MultimodalAIClient):
            raise TypeError("ai_client must be an instance of MultimodalAIClient")
        self._ai_client = ai_client
        logger.info("DirectorService initialized.")

    async def create_edit_plan(
        self,
        video_analyses: Dict[str, VideoSceneAnalysis],
        audio_analysis: AudioAnalysis,
        video_goal: str,
        key_features: List[str]
    ) -> EditDecisionList:
        """
        Generates an Edit Decision List (EDL) based on video and audio analysis,
        a specified video goal, and key features by leveraging the AI client.

        Args:
            video_analyses: A dictionary mapping video file paths to their
                            VideoSceneAnalysis objects.
            audio_analysis: The AudioAnalysis object for the primary audio track.
            video_goal: A string describing the overall goal or theme of the video.
            key_features: A list of strings highlighting important features or
                          elements to include in the video.

        Returns:
            An EditDecisionList object containing the plan for video editing.

        Raises:
            Exception: If the underlying AI client call fails to generate the
                       edit decision list.
        """
        logger.info(
            f"Attempting to create edit plan with video goal: '{video_goal}' "
            f"and key features: {key_features}"
        )
        try:
            # Delegate the EDL generation to the AI client
            edl = await self._ai_client.generate_edit_decision_list(
                video_analyses=video_analyses,
                audio_analysis=audio_analysis,
                video_goal=video_goal,
                key_features=key_features
            )
            logger.info("Successfully generated Edit Decision List.")
            return edl
        except Exception as e:
            logger.error(f"Failed to generate edit decision list: {e}", exc_info=True)
            # Re-raise the exception for upstream handling (e.g., by the controller)
            raise