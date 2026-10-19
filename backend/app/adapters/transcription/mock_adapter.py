"""Mock transcription adapter providing realistic 5-minute two-speaker interview transcript."""
import asyncio
from typing import List, Optional
from app.adapters.transcription.base import TranscriptionAdapter
from app.core.models import Transcript, TranscriptWord


class MockTranscriptionAdapter(TranscriptionAdapter):
    """Generates a realistic test transcript matching assessment requirements and worked examples."""

    def __init__(self, source_media_id: str = "mock-source-id"):
        self.source_media_id = source_media_id

    def build_mock_words(self) -> List[TranscriptWord]:
        words_data = [
            # 0-10s: Intro banter / cold open
            ("Hello", 0.5, 0.9, "host", 0.99, False),
            ("everyone", 1.0, 1.5, "host", 0.98, False),
            ("and", 1.8, 2.0, "host", 0.95, False),
            ("um", 2.2, 2.6, "host", 0.65, True),
            ("welcome", 2.8, 3.3, "host", 0.99, False),
            ("to", 3.4, 3.6, "host", 0.99, False),
            ("our", 3.7, 4.0, "host", 0.98, False),
            ("podcast", 4.1, 4.8, "host", 0.97, False),
            ("today", 5.0, 5.5, "host", 0.99, False),
            ("we", 6.0, 6.3, "host", 0.98, False),
            ("have", 6.4, 6.7, "host", 0.98, False),
            ("a", 6.8, 7.0, "host", 0.99, False),
            ("very", 7.1, 7.5, "host", 0.96, False),
            ("special", 7.6, 8.2, "host", 0.95, False),
            ("guest", 8.3, 8.8, "host", 0.99, False),

            # 12-25s: Sound check and filler banter
            ("testing", 12.0, 12.5, "guest", 0.95, False),
            ("audio", 12.6, 13.0, "guest", 0.97, False),
            ("levels", 13.1, 13.6, "guest", 0.98, False),
            ("uh", 14.0, 14.5, "host", 0.60, True),
            ("can", 15.0, 15.3, "host", 0.98, False),
            ("you", 15.4, 15.6, "host", 0.99, False),
            ("hear", 15.7, 16.1, "host", 0.98, False),
            ("me", 16.2, 16.5, "host", 0.99, False),
            ("clearly", 16.6, 17.2, "host", 0.95, False),
            ("yes", 18.0, 18.4, "guest", 0.99, False),
            ("sounds", 18.5, 19.0, "guest", 0.97, False),
            ("like", 19.2, 19.5, "guest", 0.58, True),
            ("great", 19.6, 20.2, "guest", 0.98, False),
            ("um", 22.0, 22.5, "guest", 0.62, True),
            ("ready", 23.0, 23.5, "guest", 0.99, False),

            # 30-40s: Pre-intro section (often targeted for cuts)
            ("let", 30.0, 30.3, "host", 0.99, False),
            ("me", 30.4, 30.6, "host", 0.99, False),
            ("adjust", 30.7, 31.2, "host", 0.96, False),
            ("the", 31.3, 31.5, "host", 0.99, False),
            ("lighting", 31.6, 32.3, "host", 0.95, False),
            ("here", 32.5, 33.0, "host", 0.98, False),
            ("alright", 35.0, 35.6, "host", 0.99, False),
            ("starting", 36.0, 36.6, "host", 0.98, False),
            ("countdown", 37.0, 37.8, "host", 0.96, False),

            # 42-45s: KEY PHRASE "welcome to the channel"
            ("welcome", 42.0, 42.5, "host", 0.99, False),
            ("to", 42.6, 42.8, "host", 0.99, False),
            ("the", 42.9, 43.1, "host", 0.99, False),
            ("channel", 43.2, 43.9, "host", 0.99, False),
            ("everybody", 44.0, 44.7, "host", 0.98, False),

            # 48-58s: Topic discussion
            ("today", 48.0, 48.4, "host", 0.99, False),
            ("we", 48.5, 48.7, "host", 0.99, False),
            ("dive", 48.8, 49.3, "host", 0.95, False),
            ("into", 49.4, 49.7, "host", 0.98, False),
            ("video", 49.8, 50.3, "host", 0.99, False),
            ("editing", 50.4, 51.0, "host", 0.99, False),
            ("automation", 51.2, 52.0, "host", 0.96, False),

            # 60s: First "thanks" occurrence
            ("thanks", 59.8, 60.4, "host", 0.99, False),
            ("for", 60.5, 60.8, "host", 0.99, False),
            ("joining", 60.9, 61.5, "host", 0.98, False),

            # 64-75s: First "pricing" mention
            ("let", 64.0, 64.3, "guest", 0.98, False),
            ("us", 64.4, 64.7, "guest", 0.99, False),
            ("talk", 64.8, 65.2, "guest", 0.99, False),
            ("about", 65.3, 65.7, "guest", 0.98, False),
            ("pricing", 65.8, 66.5, "guest", 0.99, False),
            ("and", 66.7, 67.0, "guest", 0.97, False),
            ("how", 67.1, 67.4, "guest", 0.99, False),
            ("our", 67.5, 67.8, "guest", 0.98, False),
            ("cost", 67.9, 68.4, "guest", 0.99, False),
            ("structure", 68.5, 69.2, "guest", 0.97, False),
            ("works", 69.4, 70.0, "guest", 0.99, False),

            # 80-110s: Mid-interview section
            ("our", 80.0, 80.3, "guest", 0.98, False),
            ("system", 80.4, 80.9, "guest", 0.99, False),
            ("processes", 81.0, 81.7, "guest", 0.96, False),
            ("hundreds", 82.0, 82.6, "guest", 0.98, False),
            ("of", 82.7, 82.9, "guest", 0.99, False),
            ("videos", 83.0, 83.6, "guest", 0.99, False),
            ("per", 83.7, 84.0, "guest", 0.98, False),
            ("hour", 84.1, 84.6, "guest", 0.97, False),
            ("uh", 88.0, 88.5, "guest", 0.63, True),
            ("with", 90.0, 90.3, "guest", 0.99, False),
            ("extreme", 90.4, 91.0, "guest", 0.95, False),
            ("precision", 91.1, 91.8, "guest", 0.94, False),

            # 120s: Second "thanks" occurrence
            ("many", 118.8, 119.3, "guest", 0.98, False),
            ("thanks", 119.6, 120.3, "guest", 0.99, False),
            ("to", 120.5, 120.8, "guest", 0.98, False),
            ("the", 120.9, 121.2, "guest", 0.99, False),
            ("community", 121.3, 122.0, "guest", 0.96, False),

            # 130-155s: Deep dive
            ("what", 135.0, 135.4, "host", 0.99, False),
            ("about", 135.5, 135.9, "host", 0.98, False),
            ("scalability", 136.0, 136.9, "host", 0.95, False),
            ("it", 140.0, 140.3, "guest", 0.99, False),
            ("scales", 140.4, 141.0, "guest", 0.98, False),
            ("horizontally", 141.1, 142.1, "guest", 0.94, False),
            ("across", 142.3, 142.8, "guest", 0.97, False),
            ("nodes", 143.0, 143.6, "guest", 0.96, False),

            # 160s: Second "pricing" mention
            ("how", 158.5, 158.8, "host", 0.99, False),
            ("does", 158.9, 159.2, "host", 0.98, False),
            ("the", 159.3, 159.6, "host", 0.99, False),
            ("pricing", 159.8, 160.6, "host", 0.99, False),
            ("scale", 160.8, 161.4, "host", 0.98, False),
            ("with", 161.6, 161.9, "host", 0.99, False),
            ("users", 162.0, 162.7, "host", 0.97, False),

            # 180s: Third "thanks" occurrence
            ("thanks", 179.6, 180.4, "host", 0.99, False),
            ("for", 180.5, 180.8, "host", 0.99, False),
            ("clarifying", 180.9, 181.7, "host", 0.96, False),
            ("that", 181.8, 182.2, "host", 0.99, False),

            # 195s: Third "pricing" mention
            ("for", 193.5, 193.8, "guest", 0.99, False),
            ("enterprise", 194.0, 194.8, "guest", 0.96, False),
            ("pricing", 195.0, 195.8, "guest", 0.99, False),
            ("we", 196.0, 196.3, "guest", 0.99, False),
            ("offer", 196.4, 196.8, "guest", 0.98, False),
            ("volume", 197.0, 197.6, "guest", 0.97, False),
            ("discounts", 197.7, 198.5, "guest", 0.95, False),

            # 210-235s: Feature discussion
            ("our", 215.0, 215.3, "guest", 0.99, False),
            ("rendering", 215.4, 216.1, "guest", 0.98, False),
            ("pipeline", 216.2, 216.9, "guest", 0.97, False),
            ("is", 217.0, 217.3, "guest", 0.99, False),
            ("deterministic", 217.5, 218.6, "guest", 0.94, False),
            ("and", 220.0, 220.3, "host", 0.99, False),
            ("um", 220.5, 221.0, "host", 0.64, True),
            ("captions", 221.5, 222.2, "host", 0.98, False),
            ("are", 222.3, 222.6, "host", 0.99, False),
            ("pixel", 222.7, 223.2, "host", 0.97, False),
            ("accurate", 223.4, 224.1, "host", 0.96, False),

            # 240s: Fourth "thanks" occurrence
            ("thanks", 239.5, 240.3, "guest", 0.99, False),
            ("for", 240.4, 240.7, "guest", 0.99, False),
            ("having", 240.8, 241.3, "guest", 0.98, False),
            ("me", 241.4, 241.7, "guest", 0.99, False),
            ("on", 241.8, 242.0, "guest", 0.99, False),
            ("the", 242.1, 242.3, "guest", 0.99, False),
            ("show", 242.4, 242.9, "guest", 0.98, False),

            # 250-300s: Conclusion and wrap up
            ("don't", 270.0, 270.4, "host", 0.98, False),
            ("forget", 270.5, 271.0, "host", 0.99, False),
            ("to", 271.1, 271.3, "host", 0.99, False),
            ("like", 271.4, 271.8, "host", 0.99, False),
            ("and", 272.0, 272.2, "host", 0.99, False),
            ("subscribe", 272.3, 273.1, "host", 0.98, False),
            ("goodbye", 290.0, 290.8, "host", 0.99, False),
            ("everyone", 291.0, 291.7, "host", 0.99, False)
        ]

        return [
            TranscriptWord(
                word=w,
                start_s=round(s, 2),
                end_s=round(e, 2),
                speaker=spk,
                confidence=conf,
                is_filler=is_f
            )
            for w, s, e, spk, conf, is_f in words_data
        ]

    async def transcribe(self, file_path: str) -> Transcript:
        """Asynchronously return mock transcript."""
        await asyncio.sleep(0.01)
        words = self.build_mock_words()
        return Transcript(
            source_media_id=self.source_media_id,
            words=words,
            speakers=["host", "guest"]
        )
