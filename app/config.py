"""Application configuration module.

Manages environment variables and application settings using Pydantic.
"""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support.

    All settings can be configured via environment variables or .env file.
    Environment variable names are case-insensitive.
    """
    openrouter_api_key: str = Field(
        ...,
        description="OpenRouter API key for LLM access",
    )
    model_name: str = Field(
        default="anthropic/claude-sonnet-4-20250514",
        description="LLM model to use for extraction",
    )
    max_tokens: int = Field(
        default=4096,
        ge=1,
        le=32000,
        description="Maximum tokens in LLM response",
    )
    api_port: int = Field(
        default=8000,
        ge=1024,
        le=65535,
        description="Port to run the API server on",
    )
    workers: int = Field(
        default=4,
        ge=1,
        le=32,
        description="Number of worker processes",
    )
    max_upload_size: int = Field(
        default=5242880,
        ge=1024,
        le=104857600,
        description="Maximum upload size in bytes (default: 5MB)",
    )
    allowed_mime_types: list[str] = Field(
        default=["image/jpeg", "image/jpg", "image/png", "application/pdf"],
        description="Allowed MIME types for uploads",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        protected_namespaces=("settings_",),
    )

    @field_validator("openrouter_api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Validate that API key is properly configured.

        Args:
            v: API key value from environment.

        Returns:
            Validated API key.

        Raises:
            ValueError: If API key is missing or placeholder.
        """
        if not v or v.startswith("your_"):
            msg = "OPENROUTER_API_KEY must be set in environment or .env file"
            raise ValueError(msg)
        return v

settings = Settings()
