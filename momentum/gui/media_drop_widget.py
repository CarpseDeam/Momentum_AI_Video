"""
Defines the MediaDropWidget, a reusable QWidget for handling file drag-and-drop operations.
This component is decoupled via a signal, allowing it to notify parent widgets of dropped files
without direct coupling.
"""

import PySide6.QtWidgets
import PySide6.QtCore
import PySide6.QtGui


class MediaDropWidget(PySide6.QtWidgets.QWidget):
    """
    A QWidget subclass designed to accept drag-and-drop operations for files.

    It provides visual feedback during drag events and emits a signal with a list
    of dropped file paths upon a successful drop.
    """

    filesDropped = PySide6.QtCore.Signal(list) # Emits a list[str] of file paths.

    _DEFAULT_STYLE = """
        MediaDropWidget {
            border: 2px dashed #808080;
            border-radius: 5px;
            background-color: #2b2b2b;
        }
        QLabel {
            color: #a0a0a0;
            font-size: 14px;
        }
    """
    _HIGHLIGHT_STYLE = """
        MediaDropWidget {
            border: 2px solid #4CAF50; /* Brighter green border */
            border-radius: 5px;
            background-color: #3a3a3a; /* Slightly lighter background */
        }
        QLabel {
            color: #ffffff; /* White text on highlight */
            font-size: 14px;
        }
    """

    def __init__(self, parent: PySide6.QtWidgets.QWidget | None = None) -> None:
        """
        Initializes the MediaDropWidget.

        Sets up drag-and-drop acceptance, initial styling, and a placeholder label.
        """
        super().__init__(parent)
        self.setAcceptDrops(True)

        self.setStyleSheet(self._DEFAULT_STYLE)

        # Setup internal layout and label
        self._layout = PySide6.QtWidgets.QVBoxLayout(self)
        self._label = PySide6.QtWidgets.QLabel("Drag Video & Audio Files Here")
        self._label.setAlignment(PySide6.QtCore.Qt.AlignmentFlag.AlignCenter)
        self._layout.addWidget(self._label)
        self._layout.setContentsMargins(20, 20, 20, 20) # Add some padding around the label

    def dragEnterEvent(self, event: PySide6.QtGui.QDragEnterEvent) -> None:
        """
        Handles the drag enter event.

        If the event contains URLs, it accepts the proposed action and applies
        a highlight style to the widget.
        """
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet(self._HIGHLIGHT_STYLE)
        else:
            event.ignore()

    def dragLeaveEvent(self, event: PySide6.QtGui.QDragLeaveEvent) -> None:
        """
        Handles the drag leave event.

        Reverts the widget's style back to the default dashed border.
        """
        self.setStyleSheet(self._DEFAULT_STYLE)
        event.accept()

    def dropEvent(self, event: PySide6.QtGui.QDropEvent) -> None:
        """
        Handles the drop event.

        Extracts local file paths from the dropped URLs, emits the filesDropped signal,
        and reverts the widget's style.
        """
        file_paths: list[str] = []
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    file_paths.append(url.toLocalFile())
            event.acceptProposedAction()
            self.filesDropped.emit(file_paths)
        else:
            event.ignore()

        self.setStyleSheet(self._DEFAULT_STYLE) # Revert style after drop