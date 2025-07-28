from typing import Optional
from PyQt6.QtCore import QObject, pyqtSignal as Signal
from momentum.services.analysis_service import AnalysisService
from momentum.services.director_service import DirectorService
from momentum.services.editor_service import EditorService
from pathlib import Path
import logging

# Configure logging for the controller
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MomentumController(QObject):
    """
    Defines the main application controller (MVC pattern). It orchestrates the backend services
    for video generation and communicates with the GUI via Qt signals, decoupling business logic from the UI.
    """

    # Custom signals for UI communication
    generation_started = Signal()
    generation_finished = Signal(str) # Emits the path to the final video or an error message

    def __init__(self, analysis_service: AnalysisService, director_service: DirectorService, editor_service: EditorService, parent: Optional[QObject] = None):
        """
        Initializes the MomentumController with necessary backend services.

        Args:
            analysis_service: Service for analyzing audio and video content.
            director_service: Service for creating the video edit plan.
            editor_service: Service for rendering the final video.
            parent: The parent QObject, if any.
        """
        super().__init__(parent)
        self.analysis_service = analysis_service
        self.director_service = director_service
        self.editor_service = editor_service
        logger.info("MomentumController initialized with backend services.")

    async def start_video_generation(self, file_paths: list[str]):
        """
        Orchestrates the entire video generation process. This method identifies media files,
        calls analysis, planning, and rendering services, and emits signals to update the UI.

        Args:
            file_paths: A list of paths (strings) to the input media files (audio and video).
        """
        self.generation_started.emit()
        logger.info(f"Video generation process initiated for files: {file_paths}")

        audio_file_path: Optional[Path] = None
        video_file_paths: list[Path] = []
        output_file_name = "output.mp4" # Default output file name
        output_path = Path(output_file_name)

        try:
            # 1. Identify audio and video files from the provided paths
            for path_str in file_paths:
                p = Path(path_str)
                if not p.exists():
                    raise FileNotFoundError(f"Input file does not exist: {p}")

                suffix = p.suffix.lower()
                if suffix in ['.mp3', '.wav']:
                    if audio_file_path:
                        logger.warning(f"Multiple audio files detected. Using '{audio_file_path.name}'. Ignoring '{p.name}'.")
                    else:
                        audio_file_path = p
                elif suffix in ['.mp4', '.mov']:
                    video_file_paths.append(p)
                else:
                    logger.warning(f"Unsupported file type skipped: {p.name}")

            if not audio_file_path:
                raise ValueError("No audio file (.mp3, .wav) found among the provided inputs.")
            if not video_file_paths:
                raise ValueError("No video files (.mp4, .mov) found among the provided inputs.")

            logger.info(f"Identified audio: '{audio_file_path.name}', videos: {[p.name for p in video_file_paths]}")

            # 2. Call analysis services
            logger.info("Starting audio analysis...")
            audio_analysis = await self.analysis_service.analyze_audio(str(audio_file_path))
            logger.info("Audio analysis complete.")

            logger.info("Starting video analysis...")
            # Convert Path objects to strings as services expect string paths
            video_analysis_input_paths = [str(p) for p in video_file_paths]
            video_analyses = await self.analysis_service.analyze_videos(video_analysis_input_paths)
            logger.info("Video analysis complete.")

            # 3. Define video goal and key features (as per architect's plan)
            video_goal = "Create an engaging short video for social media."
            key_features = ["dynamic cuts", "text overlays", "upbeat music sync"]
            logger.info(f"Using video goal: '{video_goal}' and key features: {key_features}")

            # 4. Call director service to create the edit plan (EDL)
            logger.info("Creating video edit plan (EDL)...")
            edl = await self.director_service.create_edit_plan(video_analyses, audio_analysis, video_goal, key_features)
            logger.info("Edit plan (EDL) created successfully.")

            # 5. Call editor service to render the final video
            logger.info(f"Rendering final video to '{output_path.name}'...")
            # Ensure paths are strings for the editor service
            final_video_path_str = await self.editor_service.render_video(edl, str(audio_file_path), str(output_path))
            logger.info(f"Video rendering complete. Output file: '{final_video_path_str}'")

            # Emit success signal with the path to the generated video
            self.generation_finished.emit(final_video_path_str)

        except (FileNotFoundError, ValueError) as e:
            error_message = f"Input Error: {e}"
            logger.error(error_message)
            self.generation_finished.emit(error_message) # Communicate specific error to UI
        except Exception as e:
            # Catch any other unexpected errors during the process
            error_message = f"An unexpected error occurred during video generation: {e}"
            logger.exception(error_message) # Log full traceback for unexpected errors
            self.generation_finished.emit(error_message) # Communicate generic error to UI