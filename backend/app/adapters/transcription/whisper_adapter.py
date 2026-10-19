"""Whisper transcription adapter supporting openai-whisper or faster-whisper with word-level timestamps."""
import asyncio
import os
from typing import List, Optional
from app.adapters.transcription.base import TranscriptionAdapter
from app.core.models import Transcript, TranscriptWord
from app.api.errors import VideoError


class WhisperTranscriptionAdapter(TranscriptionAdapter):
    def __init__(self, model_size: str = "base"):
        self.model_size = model_size
        self._model = None

    def _load_model(self):
        if self._model is not None:
            return self._model

        # Attempt to load faster-whisper or openai-whisper
        try:
            from faster_whisper import WhisperModel
            self._model = ("faster_whisper", WhisperModel(self.model_size, device="cpu", compute_type="int8"))
            return self._model
        except ImportError:
            pass

        try:
            import whisper
            self._model = ("whisper", whisper.load_model(self.model_size))
            return self._model
        except ImportError:
            raise VideoError(
                "Neither faster-whisper nor openai-whisper is installed. "
                "Please configure TRANSCRIPTION_PROVIDER='mock' or install whisper."
            )

    async def transcribe(self, file_path: str) -> Transcript:
        """Run whisper transcription in executor to prevent blocking event loop."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._transcribe_sync, file_path)

    def _transcribe_sync(self, file_path: str) -> Transcript:
        if not os.path.exists(file_path):
            raise VideoError(f"Video file not found for transcription: {file_path}")

        engine, model = self._load_model()
        words: List[TranscriptWord] = []
        filler_tokens = {"um", "uh", "er", "ah", "like"}

        try:
            if engine == "faster_whisper":
                segments, info = model.transcribe(file_path, word_timestamps=True)
                for segment in segments:
                    if segment.words:
                        for w in segment.words:
                            clean_text = w.word.strip()
                            is_filler = clean_text.lower() in filler_tokens
                            words.append(
                                TranscriptWord(
                                    word=clean_text,
                                    start_s=round(w.start, 2),
                                    end_s=round(w.end, 2),
                                    speaker="speaker_0",
                                    confidence=round(w.probability, 2),
                                    is_filler=is_filler
                                )
                            )
                    else:
                        # Fallback if word timestamps were unavailable
                        seg_words = segment.text.strip().split()
                        n = len(seg_words)
                        if n > 0:
                            step = (segment.end - segment.start) / n
                            for i, sw in enumerate(seg_words):
                                st = segment.start + i * step
                                et = st + step
                                words.append(
                                    TranscriptWord(
                                        word=sw,
                                        start_s=round(st, 2),
                                        end_s=round(et, 2),
                                        speaker="speaker_0",
                                        confidence=0.85,
                                        is_filler=sw.lower() in filler_tokens
                                    )
                                )
            else:
                # openai-whisper
                result = model.transcribe(file_path, word_timestamps=True)
                for segment in result.get("segments", []):
                    for w in segment.get("words", []):
                        clean_text = w.get("word", "").strip()
                        is_filler = clean_text.lower() in filler_tokens
                        words.append(
                            TranscriptWord(
                                word=clean_text,
                                start_s=round(w.get("start", 0.0), 2),
                                end_s=round(w.get("end", 0.0), 2),
                                speaker="speaker_0",
                                confidence=round(w.get("probability", 0.9), 2),
                                is_filler=is_filler
                            )
                        )
        except Exception as e:
            raise VideoError(f"Whisper transcription failed: {str(e)}")

        return Transcript(
            source_media_id=file_path,
            words=words,
            speakers=["speaker_0"]
        )
