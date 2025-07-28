"""
File: momentum/services/analysis_service.py
"""
import logging
import asyncio
from pathlib import Path
from typing import Dict, List, Optional

from momentum.models.analysis import AudioAnalysis, VideoSceneAnalysis
from momentum.components.ai_client import MultimodalAIClient
from momentum.components.audio_processor import AudioProcessor
from momentum.components.video_extractor import VideoFrameExtractor

# Configure logging for this module
logger = logging.getLogger(__name__)


class AnalysisService:
    """
    Orchestrates media analysis by using dedicated components for audio and video processing.
    It extracts features like audio beats and uses an AI client for video content analysis.
    """

    def __init__(self, ai_client: MultimodalAIClient, frames_per_video: int):
        """
        Initializes the AnalysisService.

        Args:
            ai_client: An instance of MultimodalAIClient for AI-powered analysis.
            frames_per_video: The number of frames to extract from each video for analysis.
        """
        self.ai_client = ai_client
        self.audio_processor = AudioProcessor()
        self.video_extractor = VideoFrameExtractor()
        self.frames_per_video = frames_per_video
        logger.info("AnalysisService initialized with real components.")

    async def analyze_audio(self, audio_path: str) -> AudioAnalysis:
        """
        Analyzes an audio file to extract beat timestamps using the AudioProcessor.

        Args:
            audio_path: The path to the audio file.

        Returns:
            An AudioAnalysis object containing the beat timestamps.
        """
        logger.info(f"Starting audio analysis for: {audio_path}")
        try:
            # Run the synchronous librosa function in a separate thread
            # to avoid blocking the asyncio event loop.
            beat_times = await asyncio.to_thread(
                self.audio_processor.detect_beats, audio_path
            )
            audio_analysis = AudioAnalysis(beat_timestamps=beat_times)
            logger.info(f"Audio analysis complete for {audio_path}. Found {len(beat_times)} beats.")
            return audio_analysis
        except Exception as e:
            logger.error(f"An unexpected error occurred during audio analysis for {audio_path}: {e}", exc_info=True)
            # Return an empty analysis to allow the process to continue gracefully
            return AudioAnalysis(beat_timestamps=[])

    async def analyze_videos(self, video_paths: List[str]) -> Dict[str, VideoSceneAnalysis]:
        """
        Analyzes a list of video files concurrently using the video extractor and AI client.

        Args:
            video_paths: A list of string paths to the video files.

        Returns:
            A dictionary mapping video file paths to their VideoSceneAnalysis objects.
        """
        logger.info(f"Starting video analysis for {len(video_paths)} video(s).")

        tasks = [self.analyze_single_video(path) for path in video_paths]
        results = await asyncio.gather(*tasks)

        video_analyses: Dict[str, VideoSceneAnalysis] = {}
        for video_path, analysis_result in zip(video_paths, results):
            if analysis_result:
                video_analyses[video_path] = analysis_result

        logger.info(
            f"Finished video analysis. Successfully analyzed {len(video_analyses)} out of {len(video_paths)} videos.")
        return video_analyses

    async def analyze_single_video(self, video_path: str) -> Optional[VideoSceneAnalysis]:
        """
        Helper method to extract frames from a single video and send them for AI analysis.
        """
        if not Path(video_path).is_file():
            logger.warning(f"Video file not found, skipping analysis for: {video_path}")
            return None

        logger.info(f"Processing video: {video_path}")
        try:
            # Extract frames in a thread
            frames = await asyncio.to_thread(
                self.video_extractor.extract_evenly_spaced_frames, video_path, self.frames_per_video
            )
            if not frames:
                logger.warning(f"No frames were extracted from {video_path}. Skipping AI analysis.")
                return None

            # Analyze frames with the AI client
            analysis = await self.ai_client.analyze_frames(frames)
            logger.info(f"Successfully analyzed video: {video_path}")
            return analysis
        except Exception as e:
            logger.error(f"Failed to analyze video {video_path}: {e}", exc_info=True)
            return None