import asyncio
from typing import Optional
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton,
    QFrame # QFrame is not strictly needed for the drop area, but can be used for visual styling
)
from PyQt6.QtCore import Qt, QMimeData, QUrl
from PyQt6.QtGui import QDragEnterEvent, QDropEvent

from momentum.controller import MomentumController


class MainWindow(QMainWindow):
    """
    Defines the main window of the Momentum application. It handles user interactions
    like file drops and button clicks, and updates its state based on signals
    from the controller.
    """
    def __init__(self, controller: MomentumController, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.controller = controller
        self.dropped_file_paths: list[Path] = []

        self.setWindowTitle("Momentum Video Generator")
        self.setGeometry(100, 100, 800, 600)

        self._setup_ui()
        self._connect_signals()

        # Enable drag and drop for the main window
        self.setAcceptDrops(True)

    def _setup_ui(self):
        """Initializes and lays out the UI elements."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Drop Area Label
        self.drop_area_label = QLabel("Drag & Drop Audio/Video Files Here")
        self.drop_area_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_area_label.setStyleSheet("""
            QLabel {
                border: 2px dashed #aaa;
                border-radius: 10px;
                padding: 20px;
                font-size: 18px;
                color: #555;
                background-color: #f8f8f8;
            }
        """)
        self.drop_area_label.setMinimumHeight(200)
        main_layout.addWidget(self.drop_area_label)

        # Status Label
        self.status_label = QLabel("Drop media files to begin.")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("font-size: 16px; margin-top: 10px; color: #333;")
        main_layout.addWidget(self.status_label)

        # Generate Button
        self.generate_button = QPushButton("Generate Video")
        self.generate_button.setEnabled(False)  # Initially disabled
        self.generate_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 15px 30px;
                border-radius: 8px;
                font-size: 20px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        main_layout.addWidget(self.generate_button, alignment=Qt.AlignmentFlag.AlignCenter)

        main_layout.addStretch()  # Push content to the top

    def _connect_signals(self):
        """Connects UI signals to their respective slots and controller signals."""
        self.generate_button.clicked.connect(self._on_generate_clicked)
        self.controller.generation_started.connect(self._on_generation_started)
        self.controller.generation_finished.connect(self._on_generation_finished)

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handles drag enter events to accept file URLs."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        """Handles drop events, processing dropped file URLs."""
        mime_data: QMimeData = event.mimeData()
        if mime_data.hasUrls():
            file_paths: list[Path] = []
            for url in mime_data.urls():
                if url.isLocalFile():
                    path = Path(url.toLocalFile())
                    # Basic check for common audio/video extensions
                    if path.suffix.lower() in ['.mp3', '.wav', '.mp4', '.mov', '.avi', '.mkv']:
                        file_paths.append(path)
            
            if file_paths:
                self.dropped_file_paths = file_paths
                self._handle_files_dropped(file_paths)
                event.acceptProposedAction()
            else:
                self.status_label.setText("No valid audio/video files dropped. Please drop .mp3, .wav, .mp4, .mov, etc.")
                event.ignore()
        else:
            event.ignore()

    def _handle_files_dropped(self, file_paths: list[Path]):
        """
        Called after files are successfully dropped.
        Enables the generate button and updates the status.
        """
        self.generate_button.setEnabled(True)
        file_names = [p.name for p in file_paths]
        self.status_label.setText(f"Media loaded: {', '.join(file_names)}. Ready to generate.")
        self.drop_area_label.setText("Files Loaded. Drop more to replace.")

    def _on_generate_clicked(self):
        """
        Slot for the 'Generate Video' button click.
        Disables the button, updates status, and initiates video generation via the controller.
        """
        if not self.dropped_file_paths:
            self.status_label.setText("No files loaded. Please drop audio/video files first.")
            return

        self.generate_button.setEnabled(False)
        self.status_label.setText("Generating video... this may take a moment.")
        
        # Convert Path objects to strings as the controller expects list[str]
        self.controller.start_video_generation(
            [str(p) for p in self.dropped_file_paths]
        )

    def _on_generation_started(self):
        """
        Slot for the controller's `generation_started` signal.
        Updates the UI to reflect that generation has begun.
        """
        self.status_label.setText("Generation process started by controller...")
        self.generate_button.setEnabled(False) # Ensure button is disabled

    def _on_generation_finished(self, video_path: str):
        """
        Slot for the controller's `generation_finished` signal.
        Re-enables the button and updates the status with the result.
        """
        self.generate_button.setEnabled(True)
        self.status_label.setText(f"Video created successfully: {video_path}")
        # Optionally, you could add logic here to open the video file or its directory
        # For example:
        # from PyQt6.QtGui import QDesktopServices
        # QDesktopServices.openUrl(QUrl.fromLocalFile(video_path))