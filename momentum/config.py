import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import Field, AliasChoices
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
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"  # Ignore environment variables not explicitly defined in the model.
    )

    # --- AI Model Configuration ---
    API_KEY: str = Field(
        ...,
        validation_alias=AliasChoices("GEMINI_API_KEY", "GOOGLE_API_KEY"),
        description="API key for the Google Gemini AI model. Set via GEMINI_API_KEY or GOOGLE_API_KEY env var."
    )
    GEMINI_MODEL: str = Field(
        "gemini-2.5-pro",
        description="Name of the Gemini AI model to use for all tasks. Set to 'gemini-2.5-pro' as requested."
    )

    # --- Analysis Configuration ---
    FRAMES_PER_VIDEO: int = Field(
        10,
        description="Number of evenly spaced frames to extract from each video for analysis."
    )

    def __str__(self) -> str:
        """
        Provides a user-friendly string representation of the configuration.
        Sensitive information like API keys are not fully exposed.
        """
        api_key_status = "SET" if self.API_KEY else "NOT SET"
        return (
            f"Config("
            f"GEMINI_MODEL='{self.GEMINI_MODEL}', "
            f"API_KEY_STATUS='{api_key_status}'"
            f")"
        )

    def __repr__(self) -> str:
        """
        Provides a developer-friendly representation, useful for debugging.
        """
        return self.__str__()