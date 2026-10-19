from abc import ABC, abstractmethod
from app.core.models import Transcript


class TranscriptionAdapter(ABC):
    @abstractmethod
    async def transcribe(self, file_path: str) -> Transcript:
        """Transcribe an audio or video file and return a structured Transcript with word-level timings."""
        pass
