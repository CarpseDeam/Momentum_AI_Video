import json
import logging
import google.generativeai as genai
from google.generativeai.types import GenerateContentResponse
from pydantic import ValidationError

# Import the Pydantic model for the analysis result
from momentum.models.analysis import VideoSceneAnalysis

# Configure a logger for this module
logger = logging.getLogger(__name__)
# In a larger project, logging configuration would typically be centralized.
# For a single file, this basic setup ensures logs are emitted.
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class MultimodalAIClient:
    """
    Provides a client for interacting with an external multimodal AI model (e.g., Google Gemini),
    handling API requests and response parsing for video frame analysis.
    """

    def __init__(self, api_key: str, model_name: str = "gemini-pro-vision"):
        """
        Initializes the MultimodalAIClient.

        Args:
            api_key (str): The API key for the Google Generative AI service.
            model_name (str): The name of the generative AI model to use.
                              Defaults to "gemini-pro-vision", which supports multimodal input.

        Raises:
            ValueError: If the provided API key is empty or invalid.
            Exception: If there's an issue configuring the generative AI library or loading the model.
        """
        if not api_key:
            logger.error("API key for MultimodalAIClient is missing or empty.")
            raise ValueError("API key cannot be empty. Please provide a valid API key.")
        
        self.api_key = api_key
        self.model_name = model_name
        
        try:
            # Configure the generative AI library with the provided API key
            genai.configure(api_key=self.api_key)
            # Load the specified generative model, which should be capable of handling images
            self.model = genai.GenerativeModel(self.model_name)
            logger.info(f"MultimodalAIClient initialized successfully with model: '{self.model_name}'.")
        except Exception as e:
            logger.critical(f"Failed to configure Google Generative AI or load model '{self.model_name}': {e}")
            # Re-raise the exception as initialization failure is critical for the service
            raise

    async def analyze_frames(self, frames: list[bytes]) -> VideoSceneAnalysis:
        """
        Sends a list of image frames to the multimodal AI model for analysis.

        The AI model is prompted to identify the most visually interesting or action-packed moment
        within the sequence of frames and provide a brief, one-sentence description of the clip's
        content. The AI is instructed to return the result as a JSON object.

        Args:
            frames (list[bytes]): A list of image frames, where each frame is
                                  a bytes object (e.g., JPEG encoded).

        Returns:
            VideoSceneAnalysis: A Pydantic model containing the description
                                and key moment timestamp extracted from the AI's analysis.

        Raises:
            ValueError: If no frames are provided for analysis.
            RuntimeError: If the AI model interaction fails (e.g., network issues, API errors),
                          returns an empty response, or provides a response that cannot be parsed
                          into the expected VideoSceneAnalysis format (invalid JSON or schema mismatch).
        """
        if not frames:
            logger.warning("Attempted to analyze frames but no frames were provided.")
            raise ValueError("No frames provided for analysis. Cannot proceed with AI analysis.")

        # Define the precise prompt for the multimodal AI model
        prompt = (
            "You are a film scene analyst. I will provide you with several frames from a video clip. "
            "Your job is to identify the most visually interesting or action-packed moment. "
            "Also, provide a brief, one-sentence description of the clip's content. "
            "Return ONLY a JSON object with two keys: 'description' and 'key_moment_timestamp', "
            "where the timestamp is the estimated time in seconds of the most interesting moment."
        )

        # Prepare the content list for the AI model.
        # The first element is the text prompt, followed by image parts for each frame.
        # We assume frames are JPEG encoded bytes, which is a common output for video frame extraction.
        content = [prompt] + [
            {
                'mime_type': 'image/jpeg',  # Specify the MIME type for the image data
                'data': frame_bytes
            }
            for frame_bytes in frames
        ]

        response_text = ""  # Initialize to ensure it's always defined for logging in except blocks
        try:
            logger.debug(f"Sending {len(frames)} frames to AI model '{self.model_name}' for analysis.")
            
            # Make the asynchronous call to the AI model
            response: GenerateContentResponse = await self.model.generate_content_async(content)
            
            # Extract the text part of the response.
            # For structured JSON output, response.text typically contains the full JSON string.
            response_text = response.text
            
            if not response_text:
                logger.error("AI model returned an empty or unparseable text response.")
                raise RuntimeError("AI model returned an empty or unparseable text response.")

            # Attempt to parse the AI's text response as a JSON object
            json_data = json.loads(response_text)

            # Validate and parse the JSON data into the Pydantic VideoSceneAnalysis model.
            # Pydantic will automatically validate the structure and types.
            analysis = VideoSceneAnalysis(**json_data)
            logger.info("Successfully analyzed frames and parsed AI response into VideoSceneAnalysis.")
            return analysis

        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON from AI response: {e}. Raw response: '{response_text}'")
            raise RuntimeError(f"AI response was not valid JSON. Error: {e}") from e
        except ValidationError as e:
            logger.error(f"AI response JSON did not match VideoSceneAnalysis schema: {e}. Raw response: '{response_text}'")
            raise RuntimeError(f"AI response schema mismatch. Error: {e}") from e
        except Exception as e:
            # Catch any other unexpected exceptions that might occur during the API call or processing
            logger.error(f"An unexpected error occurred during AI analysis: {e}. Raw response (if available): '{response_text}'")
            raise RuntimeError(f"AI analysis failed due to an unexpected error: {e}") from e