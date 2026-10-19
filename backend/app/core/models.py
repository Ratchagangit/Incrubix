"""Pydantic v2 core data models for IncuBrix video editing timeline, anchors, and operations."""
import uuid
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field, computed_field


class AnchorType(str, Enum):
    CAPTION = "caption"
    MUTE = "mute"
    BLEEP = "bleep"
    AUTO_CAPTION = "auto_caption"


class OperationType(str, Enum):
    CUT = "CUT"
    KEEP = "KEEP"
    REORDER = "REORDER"
    SPEED = "SPEED"
    MUTE = "MUTE"
    BLEEP = "BLEEP"
    ADD_CAPTION = "ADD_CAPTION"
    AUTO_CAPTION = "AUTO_CAPTION"
    REMOVE_FILLERS = "REMOVE_FILLERS"
    REMOVE_SILENCES = "REMOVE_SILENCES"
    ADD_MUSIC = "ADD_MUSIC"
    MODIFY_CAPTION = "MODIFY_CAPTION"
    REMOVE_CAPTION = "REMOVE_CAPTION"
    UNDO = "UNDO"
    REDO = "REDO"
    RESTORE = "RESTORE"
    RENDER = "RENDER"


class InstructionStatus(str, Enum):
    APPLIED = "APPLIED"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    REJECTED = "REJECTED"


class SourceMedia(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    file_hash: str
    duration_s: float
    frame_rate: float
    width: int
    height: int
    has_audio: bool
    codec: str
    file_path: str


class TranscriptWord(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    word: str
    start_s: float
    end_s: float
    speaker: Optional[str] = None
    confidence: float = 1.0
    is_filler: bool = False


class Transcript(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    source_media_id: str
    words: List[TranscriptWord]
    speakers: List[str] = Field(default_factory=list)


class TimelineSegment(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_media_id: str
    source_start_s: float
    source_end_s: float
    speed: float = 1.0

    @computed_field
    @property
    def duration_s(self) -> float:
        if self.speed <= 0:
            return 0.0
        return (self.source_end_s - self.source_start_s) / self.speed


class ContentAnchor(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: AnchorType
    source_media_id: str
    source_start_s: float
    source_end_s: float
    properties: Dict[str, Any] = Field(default_factory=dict)
    active: bool = True
    warning: Optional[str] = None


class BackgroundMusic(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_path: str
    volume: float = 0.3
    duck_volume: float = 0.1
    duck_threshold_db: float = -30.0


class Timeline(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_media_id: str
    segments: List[TimelineSegment]
    anchors: List[ContentAnchor] = Field(default_factory=list)
    background_music: Optional[BackgroundMusic] = None
    auto_captions_enabled: bool = False


class Operation(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    type: OperationType
    params: Dict[str, Any] = Field(default_factory=dict)


class InstructionResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    status: InstructionStatus
    operations: List[Operation] = Field(default_factory=list)
    summary: str = ""
    question: Optional[str] = None
    options: Optional[List[str]] = None
    timeline_hash: str = ""
    duration_s: float = 0.0
    time_policy: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)


class EditTransaction(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    step_index: int
    instruction: str
    result: InstructionResult
    timeline_before_hash: str
    timeline_after_hash: str


class Project(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_media: SourceMedia
    transcript: Optional[Transcript] = None
    timeline: Timeline
    history_stack: List[EditTransaction] = Field(default_factory=list)
    history_position: int = -1
    time_policy: str = "current"
    timeline_snapshots: Dict[str, str] = Field(default_factory=dict)
