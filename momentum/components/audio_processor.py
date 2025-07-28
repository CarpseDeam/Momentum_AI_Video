import librosa
import logging
from pathlib import Path

# Configure logging for the module
logger = logging.getLogger(__name__)
# In a larger project, logging would typically be configured centrally.
# This basic config ensures messages are visible if this module is run standalone.
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class AudioProcessor:
    """
    Provides a dedicated component for audio processing, encapsulating all interactions
    with the 'librosa' library for tasks like beat detection.
    """

    def __init__(self):
        """
        Initializes the AudioProcessor.
        Currently, no specific setup is required for librosa, but this method
        is provided for future extensibility or dependency injection.
        """
        logger.debug("AudioProcessor initialized.")

    def detect_beats(self, audio_path: str) -> list[float]:
        """
        Detects the timestamps of musical beats in an audio file using librosa.

        Args:
            audio_path (str): The file path to the audio clip.

        Returns:
            list[float]: A list of floating-point numbers, where each number is a beat's
                         timestamp in seconds. Returns an empty list if the file is not
                         found or an error occurs during processing.
        """
        audio_file_path = Path(audio_path)

        if not audio_file_path.is_file():
            logger.error(f"FileNotFoundError: Audio file not found at '{audio_file_path}'. Cannot detect beats.")
            return []

        try:
            # Load the audio file. librosa.load returns the audio time series (y)
            # and the sampling rate (sr). By default, it resamples to 22050 Hz.
            y, sr = librosa.load(str(audio_file_path))

            # Perform beat tracking.
            # librosa.beat.beat_track returns the estimated tempo (BPM) and
            # the frame indices of the detected beat events.
            tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)

            # Convert beat frame indices to timestamps in seconds.
            beat_times = librosa.frames_to_time(beat_frames, sr=sr)

            logger.info(f"Successfully detected {len(beat_times)} beats in '{audio_file_path.name}' "
                        f"at an estimated tempo of {tempo:.2f} BPM.")
            
            # Convert the numpy array of timestamps to a standard Python list
            return beat_times.tolist()

        except Exception as e:
            logger.error(f"Error processing audio file '{audio_file_path}' for beat detection: {e}", exc_info=True)
            return []