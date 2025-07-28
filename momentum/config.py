import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load environment variables from .env file.
# This ensures that environment variables defined in a .env file
# are loaded into the process's environment before Pydantic's BaseSettings
# attempts to read them.
load_dotenv()

class Config(BaseSettings):
    """
    Manages application configuration by loading settings from environment variables.

    Settings are loaded from environment variables, with an optional .env file
    providing default or development values.
    """

    # Pydantic v2 configuration for settings management.
    # This specifies how settings are loaded, including the .env file.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"  # Ignore environment variables not explicitly defined in the model.
    )

    # --- AI Model Configuration ---
    GEMINI_API_KEY: str = Field(
        ...,  # Ellipsis indicates this field is required.
        description="API key for the Google Gemini AI model. Must be set as an environment variable."
    )
    GEMINI_MODEL_NAME: str = Field(
        "gemini-pro-vision",  # Default value if not specified in environment.
        description="Name of the Gemini AI model to use for video analysis (e.g., 'gemini-pro-vision')."
    )

    # --- General Application Configuration (add as needed) ---
    # Example: A base directory for data storage, defaulting to a 'data' folder
    # relative to the project root.
    # BASE_DATA_DIR: Path = Field(
    #     Path("./data"),
    #     description="Base directory for storing application data (e.g., processed files, logs)."
    # )

    def __str__(self) -> str:
        """
        Provides a user-friendly string representation of the configuration.
        Sensitive information like API keys are not fully exposed.
        """
        api_key_status = "SET" if self.GEMINI_API_KEY else "NOT SET"
        return (
            f"Config("
            f"GEMINI_MODEL_NAME='{self.GEMINI_MODEL_NAME}', "
            f"GEMINI_API_KEY_STATUS='{api_key_status}'"
            # f", BASE_DATA_DIR='{self.BASE_DATA_DIR}'" # Uncomment if BASE_DATA_DIR is added
            f")"
        )

    def __repr__(self) -> str:
        """
        Provides a developer-friendly representation, useful for debugging.
        """
        return self.__str__()