"""Transcription adapters module."""
from app.adapters.transcription.base import TranscriptionAdapter
from app.adapters.transcription.mock_adapter import MockTranscriptionAdapter
from app.adapters.transcription.whisper_adapter import WhisperTranscriptionAdapter

__all__ = [
    "TranscriptionAdapter",
    "MockTranscriptionAdapter",
    "WhisperTranscriptionAdapter"
]
