"""TimelineEngine: Pure functional engine for non-destructive, content-anchored video timeline editing."""
import copy
import uuid
from typing import List, Optional, Tuple, Dict, Any

from app.core.models import (
    SourceMedia, Timeline, TimelineSegment, ContentAnchor,
    AnchorType, BackgroundMusic, Transcript
)
from app.core.anchors import AnchorManager


class TimelineEngine:
    @staticmethod
    def create_initial(source_media: SourceMedia) -> Timeline:
        """Create initial timeline covering the entire duration of the source media."""
        initial_segment = TimelineSegment(
            id=str(uuid.uuid4()),
            source_media_id=str(source_media.id),
            source_start_s=0.0,
            source_end_s=round(source_media.duration_s, 6),
            speed=1.0
        )
        return Timeline(
            id=str(uuid.uuid4()),
            source_media_id=str(source_media.id),
            segments=[initial_segment],
            anchors=[],
            background_music=None,
            auto_captions_enabled=False
        )

    @staticmethod
    def get_duration(timeline: Timeline) -> float:
        """Sum of all segment durations in current timeline."""
        return sum(s.duration_s for s in timeline.segments)

    @staticmethod
    def cut(timeline: Timeline, source_start: float, source_end: float) -> Timeline:
        """
        Pure function: Cut the interval [source_start, source_end) in source time.
        Splits affected segments, removes covered segments, updates anchors.
        """
        if source_start >= source_end:
            raise ValueError(f"Invalid cut range: start ({source_start}s) >= end ({source_end}s)")

        # Validate that cut range overlaps with some current content
        has_overlap = any(
            max(source_start, s.source_start_s) < min(source_end, s.source_end_s)
            for s in timeline.segments
        )
        if not has_overlap:
            raise ValueError(f"Cut range [{source_start:.2f}s, {source_end:.2f}s) is outside current timeline content")

        new_segments: List[TimelineSegment] = []
        for s in timeline.segments:
            s_start = s.source_start_s
            s_end = s.source_end_s

            # Disjoint
            if s_end <= source_start or s_start >= source_end:
                new_segments.append(s.model_copy())
            # Cut covers entire segment
            elif source_start <= s_start and s_end <= source_end:
                continue
            # Cut inside segment -> splits into two
            elif s_start < source_start and source_end < s_end:
                left = TimelineSegment(
                    id=str(uuid.uuid4()),
                    source_media_id=s.source_media_id,
                    source_start_s=s_start,
                    source_end_s=source_start,
                    speed=s.speed
                )
                right = TimelineSegment(
                    id=str(uuid.uuid4()),
                    source_media_id=s.source_media_id,
                    source_start_s=source_end,
                    source_end_s=s_end,
                    speed=s.speed
                )
                new_segments.extend([left, right])
            # Partial cut on left
            elif source_start <= s_start < source_end:
                right = TimelineSegment(
                    id=str(uuid.uuid4()),
                    source_media_id=s.source_media_id,
                    source_start_s=source_end,
                    source_end_s=s_end,
                    speed=s.speed
                )
                new_segments.append(right)
            # Partial cut on right
            elif source_start < s_end <= source_end:
                left = TimelineSegment(
                    id=str(uuid.uuid4()),
                    source_media_id=s.source_media_id,
                    source_start_s=s_start,
                    source_end_s=source_start,
                    speed=s.speed
                )
                new_segments.append(left)

        if not new_segments:
            raise ValueError("Cutting this range would leave an empty timeline, which is not permitted")

        temp_tl = timeline.model_copy(update={"segments": new_segments})
        updated_anchors = AnchorManager.update_anchors_after_cut(temp_tl, source_start, source_end)

        return timeline.model_copy(update={
            "segments": new_segments,
            "anchors": updated_anchors
        })

    @staticmethod
    def keep(timeline: Timeline, source_start: float, source_end: float) -> Timeline:
        """Pure function: Keep ONLY the content in [source_start, source_end). Inverse of cut."""
        if source_start >= source_end:
            raise ValueError(f"Invalid keep range: start ({source_start}s) >= end ({source_end}s)")

        new_segments: List[TimelineSegment] = []
        for s in timeline.segments:
            overlap_start = max(s.source_start_s, source_start)
            overlap_end = min(s.source_end_s, source_end)
            if overlap_start < overlap_end:
                new_segments.append(
                    TimelineSegment(
                        id=str(uuid.uuid4()),
                        source_media_id=s.source_media_id,
                        source_start_s=overlap_start,
                        source_end_s=overlap_end,
                        speed=s.speed
                    )
                )

        if not new_segments:
            raise ValueError(f"Keep range [{source_start:.2f}s, {source_end:.2f}s) contains no existing timeline content")

        temp_tl = timeline.model_copy(update={"segments": new_segments})
        # Invalidate anchors outside kept segments
        updated_anchors: List[ContentAnchor] = []
        for a in timeline.anchors:
            acp = a.model_copy()
            is_valid, warn = AnchorManager.check_anchor_validity(temp_tl, acp)
            if not is_valid:
                acp.active = False
                acp.warning = warn or "Content removed by keep operation"
            elif warn:
                acp.warning = warn
            updated_anchors.append(acp)

        return timeline.model_copy(update={
            "segments": new_segments,
            "anchors": updated_anchors
        })

    @staticmethod
    def reorder(timeline: Timeline, segment_order: List[int]) -> Timeline:
        """Pure function: Reorder segments by index. Anchors remain pinned to source content."""
        n = len(timeline.segments)
        if len(segment_order) != n or set(segment_order) != set(range(n)):
            raise ValueError(f"Invalid segment_order {segment_order} for {n} segments")

        new_segments = [timeline.segments[idx].model_copy() for idx in segment_order]
        return timeline.model_copy(update={"segments": new_segments})

    @staticmethod
    def speed_change(timeline: Timeline, source_start: float, source_end: float, factor: float) -> Timeline:
        """
        Pure function: Change playback speed for [source_start, source_end) by factor.
        Speed factor must be between 0.25 and 10.0.
        """
        if factor < 0.25 or factor > 10.0:
            raise ValueError(f"Speed factor {factor} must be between 0.25 and 10.0")

        new_segments: List[TimelineSegment] = []
        for s in timeline.segments:
            s_start = s.source_start_s
            s_end = s.source_end_s

            if s_end <= source_start or s_start >= source_end:
                new_segments.append(s.model_copy())
            elif source_start <= s_start and s_end <= source_end:
                new_speed = s.speed * factor
                new_segments.append(s.model_copy(update={"speed": new_speed}))
            elif s_start < source_start and source_end < s_end:
                new_segments.extend([
                    TimelineSegment(
                        id=str(uuid.uuid4()),
                        source_media_id=s.source_media_id,
                        source_start_s=s_start,
                        source_end_s=source_start,
                        speed=s.speed
                    ),
                    TimelineSegment(
                        id=str(uuid.uuid4()),
                        source_media_id=s.source_media_id,
                        source_start_s=source_start,
                        source_end_s=source_end,
                        speed=s.speed * factor
                    ),
                    TimelineSegment(
                        id=str(uuid.uuid4()),
                        source_media_id=s.source_media_id,
                        source_start_s=source_end,
                        source_end_s=s_end,
                        speed=s.speed
                    )
                ])
            elif source_start <= s_start < source_end:
                new_segments.extend([
                    TimelineSegment(
                        id=str(uuid.uuid4()),
                        source_media_id=s.source_media_id,
                        source_start_s=s_start,
                        source_end_s=source_end,
                        speed=s.speed * factor
                    ),
                    TimelineSegment(
                        id=str(uuid.uuid4()),
                        source_media_id=s.source_media_id,
                        source_start_s=source_end,
                        source_end_s=s_end,
                        speed=s.speed
                    )
                ])
            elif source_start < s_end <= source_end:
                new_segments.extend([
                    TimelineSegment(
                        id=str(uuid.uuid4()),
                        source_media_id=s.source_media_id,
                        source_start_s=s_start,
                        source_end_s=source_start,
                        speed=s.speed
                    ),
                    TimelineSegment(
                        id=str(uuid.uuid4()),
                        source_media_id=s.source_media_id,
                        source_start_s=source_start,
                        source_end_s=s_end,
                        speed=s.speed * factor
                    )
                ])

        temp_tl = timeline.model_copy(update={"segments": new_segments})
        # Check anchors in affected range: warn if caption duration < 0.7s
        updated_anchors: List[ContentAnchor] = []
        for a in timeline.anchors:
            acp = a.model_copy()
            if acp.type in (AnchorType.CAPTION, AnchorType.AUTO_CAPTION) and acp.active:
                pos = AnchorManager.resolve_single_anchor(temp_tl, acp)
                if pos and pos["duration_s"] < 0.7:
                    acp.warning = f"Caption duration ({pos['duration_s']:.2f}s) is shorter than 0.7s due to speed change"
            updated_anchors.append(acp)

        return timeline.model_copy(update={
            "segments": new_segments,
            "anchors": updated_anchors
        })

    @staticmethod
    def add_anchor(timeline: Timeline, anchor: ContentAnchor) -> Timeline:
        """Add semantic content anchor if its source content exists."""
        is_valid, _ = AnchorManager.check_anchor_validity(timeline, anchor)
        if not is_valid:
            raise ValueError(f"Cannot attach anchor: source content [{anchor.source_start_s:.2f}s, {anchor.source_end_s:.2f}s) is not in timeline")

        new_anchors = [a.model_copy() for a in timeline.anchors] + [anchor.model_copy()]
        return timeline.model_copy(update={"anchors": new_anchors})

    @staticmethod
    def remove_anchor(timeline: Timeline, anchor_id: str) -> Timeline:
        new_anchors = [a.model_copy() for a in timeline.anchors if a.id != anchor_id]
        return timeline.model_copy(update={"anchors": new_anchors})

    @staticmethod
    def update_anchor(timeline: Timeline, anchor_id: str, properties: Dict[str, Any]) -> Timeline:
        new_anchors = []
        found = False
        for a in timeline.anchors:
            if a.id == anchor_id:
                found = True
                acp = a.model_copy()
                acp.properties.update(properties)
                new_anchors.append(acp)
            else:
                new_anchors.append(a.model_copy())
        if not found:
            raise ValueError(f"Anchor '{anchor_id}' not found")
        return timeline.model_copy(update={"anchors": new_anchors})

    @staticmethod
    def add_background_music(timeline: Timeline, music: BackgroundMusic) -> Timeline:
        return timeline.model_copy(update={"background_music": music.model_copy()})

    @staticmethod
    def remove_background_music(timeline: Timeline) -> Timeline:
        return timeline.model_copy(update={"background_music": None})

    @staticmethod
    def remove_filler_words(
        timeline: Timeline,
        transcript: Transcript,
        filler_words: Optional[List[str]] = None
    ) -> Tuple[Timeline, List[Dict[str, Any]]]:
        """Detect filler words ('um', 'uh', 'like' if is_filler) and cut intervals."""
        target_fillers = set(filler_words or ["um", "uh"])
        removed_intervals = []
        curr_tl = timeline

        for word in transcript.words:
            w_text = word.word.lower().strip(".,!?")
            is_target = w_text in target_fillers or (w_text == "like" and word.is_filler)
            if is_target or word.is_filler:
                try:
                    curr_tl = TimelineEngine.cut(curr_tl, word.start_s, word.end_s)
                    removed_intervals.append({
                        "word": word.word,
                        "source_start_s": word.start_s,
                        "source_end_s": word.end_s
                    })
                except Exception:
                    pass

        return curr_tl, removed_intervals

    @staticmethod
    def remove_silences(
        timeline: Timeline,
        transcript: Transcript,
        min_silence_s: float = 2.0
    ) -> Tuple[Timeline, List[Dict[str, Any]]]:
        """Detect gaps between words > min_silence_s, preserve 0.3s padding, and cut the middle."""
        removed_intervals = []
        curr_tl = timeline
        words = sorted(transcript.words, key=lambda w: w.start_s)

        for i in range(len(words) - 1):
            gap_start = words[i].end_s
            gap_end = words[i + 1].start_s
            gap_duration = gap_end - gap_start

            if gap_duration > min_silence_s:
                # Keep 0.3s padding each side
                cut_start = gap_start + 0.3
                cut_end = gap_end - 0.3
                if cut_start < cut_end:
                    try:
                        curr_tl = TimelineEngine.cut(curr_tl, cut_start, cut_end)
                        removed_intervals.append({
                            "source_start_s": cut_start,
                            "source_end_s": cut_end,
                            "gap_duration": gap_duration
                        })
                    except Exception:
                        pass

        return curr_tl, removed_intervals

    @staticmethod
    def source_to_timeline(timeline: Timeline, source_time: float) -> Optional[float]:
        """Walk segments in order; return timeline time corresponding to source_time or None if cut."""
        current_offset = 0.0
        for seg in timeline.segments:
            seg_duration = (seg.source_end_s - seg.source_start_s) / seg.speed
            if seg.source_start_s <= source_time < seg.source_end_s:
                return current_offset + (source_time - seg.source_start_s) / seg.speed
            current_offset += seg_duration
        return None

    @staticmethod
    def timeline_to_source(timeline: Timeline, timeline_time: float) -> Optional[Tuple[str, float]]:
        """Walk segments to find which contains timeline_time; return (source_media_id, source_time)."""
        current_offset = 0.0
        for seg in timeline.segments:
            seg_duration = (seg.source_end_s - seg.source_start_s) / seg.speed
            if current_offset <= timeline_time < current_offset + seg_duration:
                elapsed = timeline_time - current_offset
                source_t = seg.source_start_s + elapsed * seg.speed
                return seg.source_media_id, source_t
            current_offset += seg_duration
        return None

    @staticmethod
    def resolve_anchor_positions(timeline: Timeline) -> List[Dict[str, Any]]:
        """Compute timeline position for every active anchor."""
        resolved = []
        for anchor in timeline.anchors:
            pos = AnchorManager.resolve_single_anchor(timeline, anchor)
            if pos:
                resolved.append(pos)
            else:
                resolved.append({
                    "id": anchor.id,
                    "type": anchor.type.value if hasattr(anchor.type, "value") else str(anchor.type),
                    "timeline_start_s": None,
                    "timeline_end_s": None,
                    "properties": anchor.properties,
                    "active": False,
                    "warning": anchor.warning or "Anchor content is currently cut"
                })
        return resolved

    @staticmethod
    def validate_timeline(timeline: Timeline) -> List[str]:
        """Verify timeline integrity: no overlapping or inverted segments, valid speeds."""
        issues: List[str] = []
        if not timeline.segments:
            issues.append("Timeline has no segments")
            return issues

        for i, seg in enumerate(timeline.segments):
            if seg.source_start_s >= seg.source_end_s:
                issues.append(f"Segment {i} has start >= end ({seg.source_start_s} >= {seg.source_end_s})")
            if seg.speed <= 0:
                issues.append(f"Segment {i} has non-positive speed ({seg.speed})")

        return issues
