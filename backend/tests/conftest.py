"""Pytest fixtures and configuration for IncuBrix test suite."""
import os
import sys
from pathlib import Path
import pytest

# Ensure backend package is in python path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.models import (
    SourceMedia, TranscriptWord, Transcript, Timeline, ContentAnchor, AnchorType, Project
)
from app.core.timeline import TimelineEngine


@pytest.fixture
def sample_source_media() -> SourceMedia:
    return SourceMedia(
        id="test-media-001",
        filename="interview.mp4",
        file_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        duration_s=300.0,
        frame_rate=30.0,
        width=1920,
        height=1080,
        has_audio=True,
        codec="h264",
        file_path="fixtures/test_video.mp4"
    )


@pytest.fixture
def sample_transcript(sample_source_media) -> Transcript:
    words = [
        TranscriptWord(word="Hello", start_s=1.0, end_s=1.5, speaker="host", confidence=0.98),
        TranscriptWord(word="everyone", start_s=1.6, end_s=2.2, speaker="host", confidence=0.97),
        TranscriptWord(word="um", start_s=15.0, end_s=15.5, speaker="host", confidence=0.88, is_filler=True),
        TranscriptWord(word="uh", start_s=25.0, end_s=25.4, speaker="host", confidence=0.85, is_filler=True),
        TranscriptWord(word="like", start_s=35.0, end_s=35.4, speaker="host", confidence=0.80, is_filler=True),
        # Phrase for Step 1
        TranscriptWord(word="welcome", start_s=42.0, end_s=42.4, speaker="host", confidence=0.99),
        TranscriptWord(word="to", start_s=42.4, end_s=42.6, speaker="host", confidence=0.99),
        TranscriptWord(word="the", start_s=42.6, end_s=42.8, speaker="host", confidence=0.99),
        TranscriptWord(word="channel", start_s=42.8, end_s=43.5, speaker="host", confidence=0.98),
        # Fillers & phrases
        TranscriptWord(word="um", start_s=50.0, end_s=50.5, speaker="guest", confidence=0.82, is_filler=True),
        TranscriptWord(word="thanks", start_s=60.0, end_s=60.5, speaker="host", confidence=0.95),
        # Pricing occurrence 1
        TranscriptWord(word="pricing", start_s=65.0, end_s=65.8, speaker="host", confidence=0.92),
        TranscriptWord(word="cost", start_s=68.0, end_s=68.5, speaker="host", confidence=0.91),
        TranscriptWord(word="uh", start_s=70.0, end_s=70.4, speaker="guest", confidence=0.87, is_filler=True),
        TranscriptWord(word="um", start_s=90.0, end_s=90.5, speaker="guest", confidence=0.89, is_filler=True),
        # Legitimate "like" (not a filler)
        TranscriptWord(word="like", start_s=100.0, end_s=100.4, speaker="guest", confidence=0.96, is_filler=False),
        TranscriptWord(word="thanks", start_s=120.0, end_s=120.5, speaker="guest", confidence=0.96),
        # Pricing occurrence 2 (target for "the second one")
        TranscriptWord(word="pricing", start_s=160.0, end_s=160.7, speaker="guest", confidence=0.94),
        TranscriptWord(word="cost", start_s=162.0, end_s=162.6, speaker="guest", confidence=0.90),
        TranscriptWord(word="thanks", start_s=180.0, end_s=180.5, speaker="host", confidence=0.95),
        # Pricing occurrence 3
        TranscriptWord(word="pricing", start_s=195.0, end_s=195.6, speaker="host", confidence=0.93),
        TranscriptWord(word="thanks", start_s=240.0, end_s=240.5, speaker="guest", confidence=0.97)
    ]
    return Transcript(
        source_media_id=sample_source_media.id,
        words=words,
        speakers=["host", "guest"]
    )


@pytest.fixture
def sample_timeline(sample_source_media) -> Timeline:
    return TimelineEngine.create_initial(sample_source_media)


@pytest.fixture
def sample_project(sample_source_media, sample_transcript, sample_timeline) -> Project:
    return Project(
        source_media=sample_source_media,
        transcript=sample_transcript,
        timeline=sample_timeline
    )
