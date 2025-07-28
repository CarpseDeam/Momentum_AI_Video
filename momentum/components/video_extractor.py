import logging
from pathlib import Path
import cv2

# Configure logging for this module
logger = logging.getLogger(__name__)

class VideoFrameExtractor:
    """
    Provides a dedicated component for video processing, responsible for extracting
    frames from video files using libraries like OpenCV.
    """

    def __init__(self):
        """
        Initializes the VideoFrameExtractor.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info("VideoFrameExtractor initialized.")

    def extract_evenly_spaced_frames(self, video_path: str, num_frames: int) -> list[bytes]:
        """
        Extracts a specified number of evenly spaced frames from a video file.

        Args:
            video_path (str): The path to the video file.
            num_frames (int): The number of frames to extract.

        Returns:
            list[bytes]: A list of extracted frames, each as bytes (JPEG encoded).
                         Returns an empty list if the video cannot be opened,
                         no frames can be extracted, or num_frames is invalid.
        """
        video_file = Path(video_path)
        extracted_frames: list[bytes] = []

        if not video_file.is_file():
            self.logger.error(f"Video file not found: {video_path}")
            return []

        if num_frames <= 0:
            self.logger.warning(f"Invalid number of frames requested: {num_frames}. Must be positive.")
            return []

        # OpenCV's VideoCapture expects a string path
        cap = cv2.VideoCapture(str(video_file))

        if not cap.isOpened():
            self.logger.error(f"Failed to open video file: {video_path}")
            return []

        try:
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if total_frames <= 0:
                self.logger.warning(f"Video file {video_path} contains no frames or could not retrieve frame count.")
                return []

            # Determine the indices of frames to extract
            indices_to_extract = []
            if num_frames >= total_frames:
                # If requested frames are more than or equal to total frames, extract all.
                indices_to_extract = list(range(total_frames))
            else:
                # Calculate evenly spaced indices across the video duration.
                # For num_frames > 1, this includes the first and last frame.
                # For num_frames = 1, it picks the middle frame.
                for i in range(num_frames):
                    if num_frames == 1:
                        index = total_frames // 2
                    else:
                        # Calculate index to span from 0 to total_frames - 1
                        index = int(i * (total_frames - 1) / (num_frames - 1))
                    indices_to_extract.append(index)

            for index in indices_to_extract:
                # Set the frame position
                cap.set(cv2.CAP_PROP_POS_FRAMES, index)
                ret, frame = cap.read()

                if ret:
                    # Encode frame to JPEG bytes. Default quality is usually fine.
                    success, buffer = cv2.imencode('.jpg', frame)
                    if success:
                        extracted_frames.append(buffer.tobytes())
                    else:
                        self.logger.warning(f"Failed to encode frame at index {index} from {video_path}.")
                else:
                    self.logger.warning(f"Failed to read frame at index {index} from {video_path}. Skipping.")

        except Exception as e:
            self.logger.exception(f"An unexpected error occurred during frame extraction from {video_path}: {e}")
            extracted_frames = [] # Ensure an empty list is returned on critical error
        finally:
            cap.release() # Always release the video capture object

        return extracted_frames