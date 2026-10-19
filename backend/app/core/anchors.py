"""AnchorManager: Manages semantic content anchors attached to source time coordinates."""
from typing import List, Optional, Tuple, Dict, Any
from app.core.models import Timeline, ContentAnchor, AnchorType


class AnchorManager:
    @staticmethod
    def check_anchor_validity(timeline: Timeline, anchor: ContentAnchor) -> Tuple[bool, Optional[str]]:
        """Check if an anchor's source content still exists in the timeline segments."""
        if not anchor.active:
            return False, "Anchor is marked inactive"

        # Check overlap with any remaining segment
        total_overlap = 0.0
        for seg in timeline.segments:
            overlap_start = max(anchor.source_start_s, seg.source_start_s)
            overlap_end = min(anchor.source_end_s, seg.source_end_s)
            if overlap_start < overlap_end:
                total_overlap += (overlap_end - overlap_start)

        expected_duration = anchor.source_end_s - anchor.source_start_s
        if total_overlap <= 0:
            return False, "Content removed by cut"
        elif total_overlap < expected_duration - 1e-4:
            return True, f"Content partially cut ({total_overlap:.2f}s of {expected_duration:.2f}s remaining)"
        return True, None

    @staticmethod
    def update_anchors_after_cut(timeline: Timeline, cut_start: float, cut_end: float) -> List[ContentAnchor]:
        """Update anchor states and ranges after a cut in [cut_start, cut_end)."""
        updated_anchors: List[ContentAnchor] = []
        for anchor in timeline.anchors:
            acp = anchor.model_copy()
            # If already inactive, keep inactive
            if not acp.active:
                updated_anchors.append(acp)
                continue

            a_start = acp.source_start_s
            a_end = acp.source_end_s

            # Fully within cut range
            if cut_start <= a_start and a_end <= cut_end:
                acp.active = False
                acp.warning = "Content removed by cut"
            # Fully before or fully after
            elif a_end <= cut_start or a_start >= cut_end:
                pass
            # Partial overlap on left
            elif cut_start <= a_start < cut_end:
                acp.source_start_s = cut_end
                acp.warning = f"Anchor start trimmed to remaining content ({cut_end:.2f}s)"
            # Partial overlap on right
            elif cut_start < a_end <= cut_end:
                acp.source_end_s = cut_start
                acp.warning = f"Anchor end trimmed to remaining content ({cut_start:.2f}s)"
            # Cut is strictly inside anchor
            elif a_start < cut_start and cut_end < a_end:
                acp.warning = f"Middle of anchor content removed from {cut_start:.2f}s to {cut_end:.2f}s"

            # Re-verify validity
            is_valid, warning = AnchorManager.check_anchor_validity(timeline, acp)
            if not is_valid:
                acp.active = False
                acp.warning = warning or "Content removed by cut"
            elif warning and not acp.warning:
                acp.warning = warning

            updated_anchors.append(acp)
        return updated_anchors

    @staticmethod
    def find_caption_by_reference(timeline: Timeline, reference: str) -> List[ContentAnchor]:
        """Find captions matching a text reference (exact or fuzzy)."""
        ref_clean = reference.strip().lower()
        matches = []
        for a in timeline.anchors:
            if a.type in (AnchorType.CAPTION, AnchorType.AUTO_CAPTION) and a.active:
                text = str(a.properties.get("text", "")).lower()
                if ref_clean in text or text in ref_clean:
                    matches.append(a)
        return matches

    @staticmethod
    def get_visible_anchors(timeline: Timeline) -> List[ContentAnchor]:
        """Return only active anchors whose underlying source content exists."""
        visible = []
        for a in timeline.anchors:
            if a.active:
                is_valid, _ = AnchorManager.check_anchor_validity(timeline, a)
                if is_valid:
                    visible.append(a)
        return visible

    @staticmethod
    def resolve_single_anchor(timeline: Timeline, anchor: ContentAnchor) -> Optional[Dict[str, Any]]:
        """Map a single anchor's source time coordinates to current timeline time coordinates."""
        if not anchor.active:
            return None

        t_start = None
        t_end = None
        current_t = 0.0

        for seg in timeline.segments:
            seg_dur = (seg.source_end_s - seg.source_start_s) / seg.speed
            overlap_start = max(anchor.source_start_s, seg.source_start_s)
            overlap_end = min(anchor.source_end_s, seg.source_end_s)

            if overlap_start < overlap_end:
                mapped_start = current_t + (overlap_start - seg.source_start_s) / seg.speed
                mapped_end = current_t + (overlap_end - seg.source_start_s) / seg.speed
                if t_start is None or mapped_start < t_start:
                    t_start = mapped_start
                if t_end is None or mapped_end > t_end:
                    t_end = mapped_end

            current_t += seg_dur

        if t_start is not None and t_end is not None:
            return {
                "id": anchor.id,
                "type": anchor.type.value if hasattr(anchor.type, "value") else str(anchor.type),
                "timeline_start_s": t_start,
                "timeline_end_s": t_end,
                "duration_s": t_end - t_start,
                "properties": anchor.properties,
                "active": True,
                "warning": anchor.warning
            }
        return None
