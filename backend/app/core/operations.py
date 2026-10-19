"""OperationExecutor: Dispatches Operation objects to TimelineEngine pure methods."""
import uuid
from typing import Tuple, List, Optional, Dict, Any

from app.core.models import (
    Operation, OperationType, Timeline, Transcript, Project,
    ContentAnchor, AnchorType, BackgroundMusic
)
from app.core.timeline import TimelineEngine
from app.core.anchors import AnchorManager


class OperationExecutor:
    @staticmethod
    def execute(
        operation: Operation,
        timeline: Timeline,
        transcript: Optional[Transcript],
        project: Project
    ) -> Tuple[Timeline, List[str]]:
        """
        Execute an operation on the timeline.
        Returns: (new_timeline, list_of_warning_messages)
        """
        op_type = operation.type
        params = operation.params or {}
        warnings: List[str] = []

        if op_type == OperationType.CUT:
            s_start = float(params.get("source_start_s", 0.0))
            s_end = float(params.get("source_end_s", 0.0))
            new_tl = TimelineEngine.cut(timeline, s_start, s_end)
            warnings.append(f"Cut range {s_start:.2f}s to {s_end:.2f}s.")
            return new_tl, warnings

        elif op_type == OperationType.KEEP:
            s_start = float(params.get("source_start_s", 0.0))
            s_end = float(params.get("source_end_s", 0.0))
            new_tl = TimelineEngine.keep(timeline, s_start, s_end)
            warnings.append(f"Kept only content in range {s_start:.2f}s to {s_end:.2f}s.")
            return new_tl, warnings

        elif op_type == OperationType.REORDER:
            order = params.get("segment_order", [])
            new_tl = TimelineEngine.reorder(timeline, order)
            return new_tl, warnings

        elif op_type == OperationType.SPEED:
            s_start = float(params.get("source_start_s", 0.0))
            s_end = float(params.get("source_end_s", 0.0))
            factor = float(params.get("factor", 1.0))
            new_tl = TimelineEngine.speed_change(timeline, s_start, s_end, factor)
            warnings.append(f"Applied {factor}x speed to range {s_start:.2f}s to {s_end:.2f}s.")
            return new_tl, warnings

        elif op_type == OperationType.ADD_CAPTION:
            text = params.get("text", "")
            s_start = float(params.get("source_start_s", 0.0))
            s_end = float(params.get("source_end_s", s_start + 2.0))
            anchor = ContentAnchor(
                id=str(uuid.uuid4()),
                type=AnchorType.CAPTION,
                source_media_id=timeline.source_media_id,
                source_start_s=s_start,
                source_end_s=s_end,
                properties={
                    "text": text,
                    "color": params.get("color", "white"),
                    "font_size": params.get("font_size", 28),
                    "position": params.get("position", "bottom")
                },
                active=True
            )
            new_tl = TimelineEngine.add_anchor(timeline, anchor)
            warnings.append(f"Added caption '{text}' pinned to {s_start:.2f}s - {s_end:.2f}s.")
            return new_tl, warnings

        elif op_type == OperationType.MODIFY_CAPTION:
            # Modify active captions
            updated_anchors = []
            modified_count = 0
            for a in timeline.anchors:
                if a.type in (AnchorType.CAPTION, AnchorType.AUTO_CAPTION) and a.active:
                    acp = a.model_copy()
                    if "color" in params:
                        acp.properties["color"] = params["color"]
                    if "font_size" in params:
                        acp.properties["font_size"] = params["font_size"]
                    if "position" in params:
                        acp.properties["position"] = params["position"]
                    updated_anchors.append(acp)
                    modified_count += 1
                else:
                    updated_anchors.append(a.model_copy())

            if modified_count == 0:
                raise ValueError("No active captions found to modify")

            new_tl = timeline.model_copy(update={"anchors": updated_anchors})
            warnings.append(f"Updated properties for {modified_count} caption(s).")
            return new_tl, warnings

        elif op_type == OperationType.MUTE:
            s_start = float(params.get("source_start_s", 0.0))
            s_end = float(params.get("source_end_s", s_start + 0.5))
            anchor = ContentAnchor(
                id=str(uuid.uuid4()),
                type=AnchorType.MUTE,
                source_media_id=timeline.source_media_id,
                source_start_s=s_start,
                source_end_s=s_end,
                properties={"word": params.get("word", "")},
                active=True
            )
            new_tl = TimelineEngine.add_anchor(timeline, anchor)
            warnings.append(f"Added mute anchor at {s_start:.2f}s - {s_end:.2f}s.")
            return new_tl, warnings

        elif op_type == OperationType.BLEEP:
            s_start = float(params.get("source_start_s", 0.0))
            s_end = float(params.get("source_end_s", s_start + 0.5))
            anchor = ContentAnchor(
                id=str(uuid.uuid4()),
                type=AnchorType.BLEEP,
                source_media_id=timeline.source_media_id,
                source_start_s=s_start,
                source_end_s=s_end,
                properties={"word": params.get("word", "")},
                active=True
            )
            new_tl = TimelineEngine.add_anchor(timeline, anchor)
            warnings.append(f"Added bleep anchor at {s_start:.2f}s - {s_end:.2f}s.")
            return new_tl, warnings

        elif op_type == OperationType.AUTO_CAPTION:
            new_tl = timeline.model_copy(update={"auto_captions_enabled": True})
            if transcript and transcript.words:
                # Add auto captions for words/sentences
                new_anchors = list(new_tl.anchors)
                for w in transcript.words:
                    if not w.is_filler:
                        new_anchors.append(
                            ContentAnchor(
                                id=str(uuid.uuid4()),
                                type=AnchorType.AUTO_CAPTION,
                                source_media_id=timeline.source_media_id,
                                source_start_s=w.start_s,
                                source_end_s=w.end_s,
                                properties={"text": w.word, "color": "white", "font_size": 26},
                                active=True
                            )
                        )
                new_tl = new_tl.model_copy(update={"anchors": new_anchors})
            warnings.append("Auto captions generated from transcript.")
            return new_tl, warnings

        elif op_type == OperationType.REMOVE_FILLERS:
            if not transcript:
                raise ValueError("Transcript required for filler removal")
            fillers = params.get("filler_words", ["um", "uh"])
            new_tl, intervals = TimelineEngine.remove_filler_words(timeline, transcript, fillers)
            warnings.append(f"Removed {len(intervals)} filler word occurrence(s).")
            return new_tl, warnings

        elif op_type == OperationType.REMOVE_SILENCES:
            if not transcript:
                raise ValueError("Transcript required for silence removal")
            min_silence = float(params.get("min_silence_s", 2.0))
            new_tl, intervals = TimelineEngine.remove_silences(timeline, transcript, min_silence)
            warnings.append(f"Removed {len(intervals)} silence pause(s).")
            return new_tl, warnings

        elif op_type == OperationType.ADD_MUSIC:
            bgm = BackgroundMusic(
                id=str(uuid.uuid4()),
                source_path=params.get("source_path", "audio/bg_music.mp3"),
                volume=float(params.get("volume", 0.3)),
                duck_volume=float(params.get("duck_volume", 0.1)),
                duck_threshold_db=float(params.get("duck_threshold_db", -30.0))
            )
            new_tl = TimelineEngine.add_background_music(timeline, bgm)
            warnings.append("Configured background music track with sidechain ducking.")
            return new_tl, warnings

        elif op_type == OperationType.REMOVE_CAPTION:
            caption_id = params.get("anchor_id")
            if caption_id:
                new_tl = TimelineEngine.remove_anchor(timeline, caption_id)
            else:
                new_anchors = [a for a in timeline.anchors if a.type != AnchorType.CAPTION]
                new_tl = timeline.model_copy(update={"anchors": new_anchors})
            return new_tl, warnings

        else:
            raise ValueError(f"Unsupported operation type: {op_type}")
