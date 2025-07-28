import sys
import os
import logging
import asyncio

from PyQt6.QtWidgets import QApplication
from qasync import QEventLoop

from momentum.services.ai_client import MultimodalAIClient
from momentum.services.analysis_service import AnalysisService
from momentum.services.director_service import DirectorService
from momentum.services.editor_service import EditorService
from momentum.controller import MomentumController
from momentum.gui.main_window import MainWindow

# Configure basic logging for the application
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    """
    The main entry point for the Momentum application.
    Initializes backend services, the application controller, the GUI,
    and starts the asyncio-compatible Qt event loop.
    """
    # 1. Retrieve API Key from environment variables
    api_key = os.getenv('MOMENTUM_AI_API_KEY')
    if not api_key:
        logging.critical("MOMENTUM_AI_API_KEY environment variable not set. "
                         "Please set it to your AI service API key before running the application.")
        sys.exit(1)

    # 2. Initialize Backend Services
    try:
        ai_client = MultimodalAIClient(api_key=api_key)
        analysis_service = AnalysisService(ai_client=ai_client)
        director_service = DirectorService(ai_client=ai_client)
        editor_service = EditorService()
        logging.info("All backend services initialized successfully.")
    except Exception as e:
        logging.critical(f"Failed to initialize backend services: {e}")
        sys.exit(1)

    # 3. Initialize the Momentum Controller
    try:
        controller = MomentumController(
            analysis_service=analysis_service,
            director_service=director_service,
            editor_service=editor_service
        )
        logging.info("MomentumController initialized.")
    except Exception as e:
        logging.critical(f"Failed to initialize MomentumController: {e}")
        sys.exit(1)

    # 4. Initialize QApplication and integrate with asyncio using QEventLoop
    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop) # Set the asyncio event loop to the Qt event loop

    # 5. Initialize the Main Window (GUI)
    try:
        main_window = MainWindow(controller=controller)
        main_window.show()
        logging.info("MainWindow initialized and displayed.")
    except Exception as e:
        logging.critical(f"Failed to initialize MainWindow: {e}")
        sys.exit(1)

    # 6. Start the Qt application event loop
    # The 'with loop:' context manager ensures the asyncio loop is properly managed
    # and integrated with Qt's event loop via app.exec().
    with loop:
        sys.exit(app.exec())

if __name__ == '__main__':
    main()