from functools import lru_cache
from typing import List, Optional, Any
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False
    )

    APP_NAME: str = Field(default="IncuBrix", description="Application name")
    APP_VERSION: str = Field(default="1.0.0", description="Application version")
    DEBUG: bool = Field(default=False, description="Debug mode")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")

    STORAGE_TYPE: str = Field(default="local", description="Storage provider (local or s3)")
    STORAGE_PATH: str = Field(default="./data/storage", description="Path for local file storage")
    S3_ENDPOINT: Optional[str] = Field(default=None, description="S3/MinIO endpoint URL")
    S3_BUCKET: str = Field(default="incubrix-videos", description="S3 bucket name")
    S3_ACCESS_KEY: Optional[str] = Field(default=None, description="S3 access key ID")
    S3_SECRET_KEY: Optional[str] = Field(default=None, description="S3 secret access key")

    TRANSCRIPTION_PROVIDER: str = Field(default="mock", description="Transcription provider (mock, whisper, api)")
    WHISPER_MODEL_SIZE: str = Field(default="base", description="Whisper model size (tiny, base, small, medium, large)")

    LLM_PROVIDER: str = Field(default="mock", description="LLM provider (mock, openai)")
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API Key")
    OPENAI_MODEL: str = Field(default="gpt-4o", description="OpenAI model identifier")

    MAX_UPLOAD_SIZE_MB: int = Field(default=500, description="Max upload size in Megabytes")
    ALLOWED_EXTENSIONS: Any = Field(
        default=[".mp4", ".mov", ".mkv", ".avi", ".webm"],
        description="Allowed video file extensions"
    )
    MAX_VIDEO_DURATION_S: float = Field(default=7200.0, description="Max video duration in seconds")

    FFMPEG_PATH: str = Field(default="ffmpeg", description="Path to ffmpeg binary")
    FFPROBE_PATH: str = Field(default="ffprobe", description="Path to ffprobe binary")

    TIME_POLICY: str = Field(default="current", description="Default time policy ('current' or 'original')")
    HOST: str = Field(default="0.0.0.0", description="Host to bind server")
    PORT: int = Field(default=8000, description="Port to bind server")

    CALLBACK_SECRET: str = Field(default="incubrix-webhook-secret-key-321", description="Secret key for signing webhook callbacks")

    @field_validator("ALLOWED_EXTENSIONS", mode="before")
    @classmethod
    def validate_allowed_extensions(cls, v):
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [ext.strip() for ext in v.split(",") if ext.strip()]
        return v

    @field_validator("STORAGE_TYPE")
    @classmethod
    def validate_storage_type(cls, v: str) -> str:
        val = v.lower()
        if val not in ("local", "s3"):
            raise ValueError("STORAGE_TYPE must be 'local' or 's3'")
        return val

    @field_validator("TRANSCRIPTION_PROVIDER")
    @classmethod
    def validate_transcription_provider(cls, v: str) -> str:
        val = v.lower()
        if val not in ("mock", "whisper", "api"):
            raise ValueError("TRANSCRIPTION_PROVIDER must be 'mock', 'whisper', or 'api'")
        return val

    @field_validator("LLM_PROVIDER")
    @classmethod
    def validate_llm_provider(cls, v: str) -> str:
        val = v.lower()
        if val not in ("mock", "openai"):
            raise ValueError("LLM_PROVIDER must be 'mock' or 'openai'")
        return val

    @field_validator("TIME_POLICY")
    @classmethod
    def validate_time_policy(cls, v: str) -> str:
        val = v.lower()
        if val not in ("current", "original"):
            raise ValueError("TIME_POLICY must be 'current' or 'original'")
        return val


@lru_cache()
def get_settings() -> Settings:
    settings = Settings()
    return settings
