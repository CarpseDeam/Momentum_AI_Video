import asyncio
import logging
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import List

from momentum.models import EditDecisionList, Shot, TextOverlay

# Configure logging for the EditorService
logger = logging.getLogger(__name__)
# Set level to INFO for production, DEBUG for development for more verbose FFmpeg output
logger.setLevel(logging.INFO) 
# Add a stream handler if not already configured by the main application
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class EditorService:
    """
    Handles the final video rendering process by executing the instructions in an
    Edit Decision List (EDL) to assemble video clips and audio using FFmpeg.
    """

    def __init__(self):
        """
        Initializes the EditorService and checks for FFmpeg availability.
        """
        logger.info("EditorService initialized.")
        # Verify FFmpeg is installed and accessible in the system's PATH
        try:
            subprocess.run(["ffmpeg", "-version"], check=True, capture_output=True, text=True)
            logger.info("FFmpeg is available on the system.")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.error(
                "FFmpeg is not found or not working. "
                "Please ensure FFmpeg is installed and in your system's PATH. "
                f"Error: {e}"
            )
            raise RuntimeError("FFmpeg is required but not found or not working correctly.") from e

    async def render_video(self, edl: EditDecisionList, audio_path: str, output_path: str) -> str:
        """
        Renders a final video based on an Edit Decision List (EDL),
        a background audio track, and an output path.

        This method orchestrates FFmpeg commands to:
        1. Trim and apply text overlays to individual video shots.
        2. Concatenate the processed video shots.
        3. Merge the concatenated video with the provided audio track.

        Args:
            edl (EditDecisionList): The Edit Decision List containing video shots and their properties.
            audio_path (str): The file path to the background audio track.
            output_path (str): The desired file path for the final rendered video.

        Returns:
            str: The absolute path to the successfully rendered video file.

        Raises:
            FileNotFoundError: If the audio file or any required video input is not found.
            RuntimeError: If any FFmpeg command fails during the rendering process.
            ValueError: If no valid video clips can be processed from the EDL.
        """
        output_path_obj = Path(output_path)
        audio_path_obj = Path(audio_path)

        if not audio_path_obj.exists():
            logger.error(f"Audio file not found at: {audio_path_obj}")
            raise FileNotFoundError(f"Audio file not found: {audio_path_obj}")

        logger.info(f"Starting video rendering process for EDL to: {output_path_obj}")

        temp_dir: Path | None = None
        try:
            # Create a temporary directory for intermediate FFmpeg outputs
            temp_dir = Path(tempfile.mkdtemp(prefix="momentum_editor_"))
            logger.debug(f"Created temporary directory: {temp_dir}")

            intermediate_clips: List[Path] = []

            # --- Step 1: Process each shot (trim and add text overlay) ---
            for i, shot in enumerate(edl.shots):
                input_video_path = Path(shot.video_path)
                if not input_video_path.exists():
                    logger.warning(f"Input video for shot {i} not found: {input_video_path}. Skipping this shot.")
                    continue

                temp_clip_path = temp_dir / f"clip_{i:03d}.mp4"

                # Base FFmpeg command for trimming and re-encoding
                # Using libx264 for video and aac for audio for broad compatibility
                command = [
                    "ffmpeg",
                    "-i", str(input_video_path),
                    "-ss", str(shot.start_time),
                    "-to", str(shot.end_time),
                    "-c:v", "libx264",
                    "-preset", "superfast",  # Faster encoding, slightly larger file
                    "-crf", "23",             # Constant Rate Factor (quality setting)
                    "-c:a", "aac",
                    "-b:a", "128k",           # Audio bitrate
                    "-y",                     # Overwrite output files without asking
                ]

                # Add text overlay filter if specified in the shot
                if shot.text_overlay and shot.text_overlay.text:
                    # Escape single quotes in text for FFmpeg filter string
                    escaped_text = shot.text_overlay.text.replace("'", "'\\''")
                    # Basic text overlay: white text, black box background, centered at bottom
                    drawtext_filter = (
                        f"drawtext=text='{escaped_text}':"
                        "x=(w-text_w)/2:y=h-th-10:"
                        "fontcolor=white:fontsize=24:box=1:boxcolor=black@0.5"
                    )
                    command.extend(["-vf", drawtext_filter]) # Add video filter argument

                command.append(str(temp_clip_path)) # Add output file path

                logger.debug(f"Executing FFmpeg for shot {i}: {' '.join(command)}")
                try:
                    # Run FFmpeg in a separate thread to avoid blocking the asyncio event loop
                    await asyncio.to_thread(
                        subprocess.run,
                        command,
                        check=True,  # Raise CalledProcessError if the command returns a non-zero exit code
                        capture_output=True, # Capture stdout and stderr
                        text=True # Decode stdout/stderr as text
                    )
                    intermediate_clips.append(temp_clip_path)
                    logger.info(f"Successfully processed shot {i} to {temp_clip_path}")
                except subprocess.CalledProcessError as e:
                    logger.error(f"FFmpeg failed for shot {i} (input: {input_video_path}). Stderr: {e.stderr}")
                    raise RuntimeError(f"Failed to process video clip: {e.stderr}") from e
                except Exception as e:
                    logger.error(f"An unexpected error occurred while processing shot {i}: {e}")
                    raise

            if not intermediate_clips:
                logger.error("No valid video clips were processed from the EDL. Cannot create video.")
                raise ValueError("No valid video clips to concatenate from the provided EDL.")

            # --- Step 2: Concatenate intermediate clips ---
            concat_list_path = temp_dir / "concat_list.txt"
            with open(concat_list_path, "w") as f:
                for clip_path in intermediate_clips:
                    # FFmpeg concat demuxer requires 'file ' followed by the path
                    # Using .as_posix() for cross-platform path compatibility in the list file
                    f.write(f"file '{clip_path.as_posix()}'\n")
            
            concatenated_video_path = temp_dir / "concatenated_video.mp4"
            concat_command = [
                "ffmpeg",
                "-f", "concat",   # Use concat demuxer
                "-safe", "0",     # Allow unsafe file paths (e.g., absolute paths)
                "-i", str(concat_list_path),
                "-c", "copy",     # Copy streams without re-encoding for speed
                "-y",
                str(concatenated_video_path)
            ]
            logger.debug(f"Executing FFmpeg for concatenation: {' '.join(concat_command)}")
            try:
                await asyncio.to_thread(
                    subprocess.run,
                    concat_command,
                    check=True,
                    capture_output=True,
                    text=True
                )
                logger.info(f"Successfully concatenated clips to {concatenated_video_path}")
            except subprocess.CalledProcessError as e:
                logger.error(f"FFmpeg failed during concatenation. Stderr: {e.stderr}")
                raise RuntimeError(f"Failed to concatenate video clips: {e.stderr}") from e
            except Exception as e:
                logger.error(f"An unexpected error occurred during concatenation: {e}")
                raise

            # --- Step 3: Add audio to the concatenated video ---
            final_command = [
                "ffmpeg",
                "-i", str(concatenated_video_path), # First input: video stream
                "-i", str(audio_path_obj),          # Second input: audio stream
                "-map", "0:v",                      # Map video stream from the first input
                "-map", "1:a",                      # Map audio stream from the second input
                "-c:v", "copy",                     # Copy video stream without re-encoding
                "-c:a", "aac",                      # Re-encode audio to AAC for compatibility
                "-b:a", "128k",
                "-shortest",                        # Finish encoding when the shortest input stream ends
                "-y",
                str(output_path_obj)
            ]
            logger.debug(f"Executing FFmpeg for final render: {' '.join(final_command)}")
            try:
                await asyncio.to_thread(
                    subprocess.run,
                    final_command,
                    check=True,
                    capture_output=True,
                    text=True
                )
                logger.info(f"Successfully rendered final video to: {output_path_obj}")
                return output_path_obj.as_posix() # Return the path as a string
            except subprocess.CalledProcessError as e:
                logger.error(f"FFmpeg failed during final audio merge. Stderr: {e.stderr}")
                raise RuntimeError(f"Failed to merge audio and video: {e.stderr}") from e
            except Exception as e:
                logger.error(f"An unexpected error occurred during final render: {e}")
                raise

        finally:
            # --- Cleanup: Remove the temporary directory and its contents ---
            if temp_dir and temp_dir.exists():
                try:
                    shutil.rmtree(temp_dir)
                    logger.debug(f"Cleaned up temporary directory: {temp_dir}")
                except OSError as e:
                    logger.warning(f"Error removing temporary directory {temp_dir}: {e}")