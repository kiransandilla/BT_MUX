"""BT-Mux Application Settings.

Loads configurations from environment variables or .env file with type validation.
"""
from functools import lru_cache
from typing import Literal
# pyrefly: ignore [missing-import]
from pydantic_settings import BaseSettings, SettingsConfigDict
try:
    from .constants import DEFAULT_T_SLICE_MS
except ImportError:
    from constants import DEFAULT_T_SLICE_MS



class Settings(BaseSettings):
    """Runtime application settings for BT-Mux server."""
    
    # Server network bindings
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    
    # Database settings (MongoDB Motor)
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "bt_mux"
    
    # Hardware Abstraction Layer (HAL) Transport
    BLE_TRANSPORT: Literal["simulated", "winrt", "linux-bluez"] = "simulated"
    
    # Scheduler defaults
    DEFAULT_T_SLICE_MS: int = DEFAULT_T_SLICE_MS
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings singleton."""
    return Settings()
