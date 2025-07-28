"""
File: momentum/components/ai_client.py
"""
import json
import logging
import google.generativeai as genai
from google.generativeai.types import GenerateContentResponse
from pydantic import ValidationError
from typing import Dict, List

from momentum.models.analysis import VideoSceneAnalysis, AudioAnalysis
from momentum.models.editing import EditDecisionList

# Configure a logger for this module
logger = logging.getLogger(__name__)


class MultimodalAIClient:
    """
    Provides a client for interacting with Google's Generative AI models (e.g., Gemini),
    handling API requests for both vision (frame analysis) and text (EDL generation) tasks.
    """

    def __init__(self, api_key: str, model_name: str):
        """
        Initializes the MultimodalAIClient.

        Args:
            api_key (str): The API key for the Google Generative AI service.
            model_name (str): The name of the generative model to use for all tasks.

        Raises:
            ValueError: If the provided API key is empty.
            Exception: If there's an issue configuring the generative AI library or loading the model.
        """
        if not api_key:
            logger.error("API key for MultimodalAIClient is missing or empty.")
            raise ValueError("API key cannot be empty. Please provide a valid API key.")

        try:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(model_name)
            logger.info(f"MultimodalAIClient initialized successfully with model: '{model_name}'.")
        except Exception as e:
            logger.critical(f"Failed to configure Google Generative AI or load model '{model_name}': {e}")
            raise

    async def analyze_frames(self, frames: list[bytes]) -> VideoSceneAnalysis:
        """
        Sends a list of image frames to the multimodal AI model for analysis.

        The AI model is prompted to identify the most visually interesting or action-packed moment
        within the sequence of frames and provide a brief, one-sentence description of the clip's
        content. The AI is instructed to return the result as a JSON object.

        Args:
            frames (list[bytes]): A list of image frames, where each frame is a bytes object (e.g., JPEG encoded).

        Returns:
            VideoSceneAnalysis: A Pydantic model containing the description and key moment timestamp.

        Raises:
            ValueError: If no frames are provided for analysis.
            RuntimeError: If the AI model interaction fails or the response is invalid.
        """
        if not frames:
            logger.warning("Attempted to analyze frames but no frames were provided.")
            raise ValueError("No frames provided for analysis.")

        prompt = (
            "You are a film scene analyst. I will provide you with several frames from a video clip. "
            "Your job is to identify the most visually interesting or action-packed moment. "
            "Also, provide a brief, one-sentence description of the clip's content. "
            "Return ONLY a JSON object with two keys: 'description' and 'key_moment_timestamp', "
            "where 'key_moment_timestamp' is the estimated time in seconds of the most interesting moment "
            "relative to the start of the clip (which is at 0 seconds)."
        )

        content = [prompt] + [{'mime_type': 'image/jpeg', 'data': frame_bytes} for frame_bytes in frames]
        response_text = ""
        try:
            logger.debug(f"Sending {len(frames)} frames to AI model for analysis.")
            response: GenerateContentResponse = await self.model.generate_content_async(content)
            response_text = response.text

            if not response_text:
                logger.error("AI model returned an empty response for frame analysis.")
                raise RuntimeError("AI model returned an empty response.")

            analysis = VideoSceneAnalysis(**json.loads(response_text))
            logger.info("Successfully analyzed frames and parsed AI response.")
            return analysis
        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(f"Failed to parse AI response for frame analysis. Response: '{response_text}'. Error: {e}")
            raise RuntimeError(f"AI response for frame analysis was not valid: {e}") from e
        except Exception as e:
            logger.error(f"An unexpected error occurred during frame analysis: {e}")
            raise RuntimeError(f"AI analysis failed unexpectedly: {e}") from e

    async def generate_edit_decision_list(
            self,
            video_analyses: Dict[str, VideoSceneAnalysis],
            audio_analysis: AudioAnalysis,
            video_goal: str,
            key_features: List[str]
    ) -> EditDecisionList:
        """
        Generates an Edit Decision List (EDL) using a text-based generative AI.

        Args:
            video_analyses: A dictionary mapping video file paths to their analysis.
            audio_analysis: The analysis of the audio track.
            video_goal: A high-level goal for the final video.
            key_features: A list of key features to highlight.

        Returns:
            An EditDecisionList object representing the complete edit plan.

        Raises:
            RuntimeError: If the AI model fails to generate a valid EDL.
        """
        # Prepare the input data for the prompt as a structured string
        input_data = {
            "video_analyses": {path: analysis.model_dump() for path, analysis in video_analyses.items()},
            "audio_analysis": audio_analysis.model_dump(),
            "video_goal": video_goal,
            "key_features": key_features,
        }

        # Prepare the schema for the desired JSON output
        output_schema = EditDecisionList.model_json_schema()

        prompt = (
            "You are a professional video editor and creative director. Your task is to create a "
            "dynamic, engaging video based on the provided media analysis and creative brief. "
            "You must generate a JSON object that represents an Edit Decision List (EDL).\n\n"
            "--- INPUT DATA ---\n"
            f"{json.dumps(input_data, indent=2)}\n\n"
            "--- CREATIVE TASK ---\n"
            "1. Create a sequence of shots (`shots`) for the final video timeline.\n"
            "2. Each shot must have a `source_video` path from the `video_analyses` input.\n"
            "3. Select `start_time` and `end_time` for each shot to create a compelling narrative. Try to use the `key_moment_timestamp` from the analysis for important shots.\n"
            "4. Make cuts that align with the `beat_timestamps` in the `audio_analysis` for a rhythmic feel.\n"
            "5. The total video duration should be reasonable for social media (e.g., 15-60 seconds).\n"
            "6. If specified in `key_features`, add `text_overlay` to some shots. Be creative with the text, making it short and impactful. Position it thoughtfully.\n\n"
            "--- OUTPUT FORMAT ---\n"
            "You must return ONLY a single, valid JSON object that conforms to the following JSON Schema. Do not include any other text or explanations.\n"
            f"{json.dumps(output_schema, indent=2)}"
        )

        response_text = ""
        try:
            logger.debug("Sending request to AI model for EDL generation.")
            # Use the single, unified model for this text-based task as well
            response: GenerateContentResponse = await self.model.generate_content_async(prompt)
            # The model might wrap the JSON in ```json ... ```, so we need to clean it.
            response_text = response.text.strip().removeprefix("```json").removesuffix("```").strip()

            if not response_text:
                logger.error("AI model returned an empty response for EDL generation.")
                raise RuntimeError("AI model returned an empty response.")

            edl = EditDecisionList(**json.loads(response_text))
            logger.info("Successfully generated and parsed Edit Decision List from AI.")
            return edl
        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(f"Failed to parse AI response for EDL generation. Response: '{response_text}'. Error: {e}")
            raise RuntimeError(f"AI response for EDL was not valid: {e}") from e
        except Exception as e:
            logger.error(f"An unexpected error occurred during EDL generation: {e}")
            raise RuntimeError(f"EDL generation failed unexpectedly: {e}") from e
