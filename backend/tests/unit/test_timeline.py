"""Comprehensive unit tests for TimelineEngine (40+ scenarios)."""
import pytest
from app.core.models import (
    SourceMedia, Timeline, ContentAnchor, AnchorType, BackgroundMusic, Transcript
)
from app.core.timeline import TimelineEngine


class TestTimelineCreation:
    def test_create_initial(self, sample_source_media):
        tl = TimelineEngine.create_initial(sample_source_media)
        assert tl.source_media_id == sample_source_media.id
        assert len(tl.segments) == 1
        assert tl.segments[0].source_start_s == 0.0
        assert tl.segments[0].source_end_s == 300.0
        assert tl.segments[0].speed == 1.0

    def test_initial_duration(self, sample_timeline):
        assert TimelineEngine.get_duration(sample_timeline) == 300.0


class TestCutOperations:
    def test_cut_beginning(self, sample_timeline):
        tl = TimelineEngine.cut(sample_timeline, 0.0, 30.0)
        assert TimelineEngine.get_duration(tl) == 270.0
        assert len(tl.segments) == 1
        assert tl.segments[0].source_start_s == 30.0
        assert tl.segments[0].source_end_s == 300.0

    def test_cut_middle(self, sample_timeline):
        tl = TimelineEngine.cut(sample_timeline, 100.0, 150.0)
        assert TimelineEngine.get_duration(tl) == 250.0
        assert len(tl.segments) == 2
        assert tl.segments[0].source_start_s == 0.0
        assert tl.segments[0].source_end_s == 100.0
        assert tl.segments[1].source_start_s == 150.0
        assert tl.segments[1].source_end_s == 300.0

    def test_cut_end(self, sample_timeline):
        tl = TimelineEngine.cut(sample_timeline, 250.0, 300.0)
        assert TimelineEngine.get_duration(tl) == 250.0
        assert len(tl.segments) == 1
        assert tl.segments[0].source_end_s == 250.0

    def test_cut_preserves_remaining_content(self, sample_timeline):
        tl = TimelineEngine.cut(sample_timeline, 50.0, 80.0)
        assert TimelineEngine.get_duration(tl) == 270.0
        assert tl.segments[0].source_end_s == 50.0
        assert tl.segments[1].source_start_s == 80.0

    def test_cut_multiple_sequential(self, sample_timeline):
        tl1 = TimelineEngine.cut(sample_timeline, 0.0, 30.0)
        tl2 = TimelineEngine.cut(tl1, 100.0, 150.0)
        tl3 = TimelineEngine.cut(tl2, 280.0, 300.0)
        assert TimelineEngine.get_duration(tl3) == 200.0
        assert len(tl3.segments) == 2

    def test_cut_entire_video_raises(self, sample_timeline):
        with pytest.raises(ValueError, match="empty timeline"):
            TimelineEngine.cut(sample_timeline, 0.0, 300.0)

    def test_cut_out_of_range_raises(self, sample_timeline):
        with pytest.raises(ValueError, match="outside current timeline"):
            TimelineEngine.cut(sample_timeline, 350.0, 400.0)

    def test_cut_zero_range_raises(self, sample_timeline):
        with pytest.raises(ValueError, match="Invalid cut range"):
            TimelineEngine.cut(sample_timeline, 50.0, 50.0)

    def test_cut_inverted_range_raises(self, sample_timeline):
        with pytest.raises(ValueError, match="Invalid cut range"):
            TimelineEngine.cut(sample_timeline, 60.0, 40.0)


class TestKeepOperations:
    def test_keep_middle(self, sample_timeline):
        tl = TimelineEngine.keep(sample_timeline, 100.0, 200.0)
        assert TimelineEngine.get_duration(tl) == 100.0
        assert len(tl.segments) == 1
        assert tl.segments[0].source_start_s == 100.0
        assert tl.segments[0].source_end_s == 200.0

    def test_keep_beginning(self, sample_timeline):
        tl = TimelineEngine.keep(sample_timeline, 0.0, 60.0)
        assert TimelineEngine.get_duration(tl) == 60.0
        assert tl.segments[0].source_start_s == 0.0
        assert tl.segments[0].source_end_s == 60.0

    def test_keep_end(self, sample_timeline):
        tl = TimelineEngine.keep(sample_timeline, 240.0, 300.0)
        assert TimelineEngine.get_duration(tl) == 60.0
        assert tl.segments[0].source_start_s == 240.0
        assert tl.segments[0].source_end_s == 300.0

    def test_keep_out_of_range_raises(self, sample_timeline):
        with pytest.raises(ValueError, match="contains no existing"):
            TimelineEngine.keep(sample_timeline, 400.0, 500.0)


class TestSpeedChange:
    def test_speed_2x(self, sample_timeline):
        tl = TimelineEngine.speed_change(sample_timeline, 60.0, 120.0, factor=2.0)
        # 0-60 @ 1x = 60s
        # 60-120 @ 2x = 30s
        # 120-300 @ 1x = 180s
        # Total = 60 + 30 + 180 = 270s
        assert TimelineEngine.get_duration(tl) == 270.0
        assert len(tl.segments) == 3
        assert tl.segments[1].speed == 2.0

    def test_speed_half(self, sample_timeline):
        tl = TimelineEngine.speed_change(sample_timeline, 0.0, 30.0, factor=0.5)
        # 0-30 @ 0.5x = 60s, 30-300 @ 1x = 270s -> Total = 330s
        assert TimelineEngine.get_duration(tl) == 330.0

    def test_speed_extreme_10x(self, sample_timeline):
        tl = TimelineEngine.speed_change(sample_timeline, 100.0, 200.0, factor=10.0)
        # 100-200 @ 10x = 10s, remaining 200s @ 1x = 200s -> Total = 210s
        assert TimelineEngine.get_duration(tl) == 210.0

    def test_speed_invalid_zero_raises(self, sample_timeline):
        with pytest.raises(ValueError, match="must be between 0.25 and 10.0"):
            TimelineEngine.speed_change(sample_timeline, 0.0, 10.0, factor=0.0)

    def test_speed_invalid_negative_raises(self, sample_timeline):
        with pytest.raises(ValueError, match="must be between 0.25 and 10.0"):
            TimelineEngine.speed_change(sample_timeline, 0.0, 10.0, factor=-1.5)


class TestReorder:
    def test_reorder_segments(self, sample_timeline):
        # Create 3 segments: 0-100, 100-200, 200-300
        tl1 = TimelineEngine.cut(sample_timeline, 99.999, 100.0)
        # Simpler: cut two points
        tl = TimelineEngine.speed_change(sample_timeline, 100.0, 200.0, factor=1.0)
        assert len(tl.segments) == 3
        # Reorder to [2, 0, 1]
        reordered = TimelineEngine.reorder(tl, [2, 0, 1])
        assert reordered.segments[0].source_start_s == 200.0
        assert reordered.segments[1].source_start_s == 0.0
        assert reordered.segments[2].source_start_s == 100.0

    def test_reorder_invalid_length_raises(self, sample_timeline):
        with pytest.raises(ValueError, match="Invalid segment_order"):
            TimelineEngine.reorder(sample_timeline, [0, 1])

    def test_reorder_invalid_indices_raises(self, sample_timeline):
        with pytest.raises(ValueError, match="Invalid segment_order"):
            TimelineEngine.reorder(sample_timeline, [5])


class TestCoordinateMappings:
    def test_source_to_timeline_basic(self, sample_timeline):
        pos = TimelineEngine.source_to_timeline(sample_timeline, 42.0)
        assert pos == 42.0

    def test_source_to_timeline_after_cut(self, sample_timeline):
        # Cut first 30 seconds
        tl = TimelineEngine.cut(sample_timeline, 0.0, 30.0)
        # Source 42s must map to timeline 12s
        pos = TimelineEngine.source_to_timeline(tl, 42.0)
        assert pos == 12.0

    def test_source_to_timeline_removed_content_returns_none(self, sample_timeline):
        tl = TimelineEngine.cut(sample_timeline, 0.0, 30.0)
        assert TimelineEngine.source_to_timeline(tl, 15.0) is None

    def test_source_to_timeline_after_speed(self, sample_timeline):
        # Speed up 0-60 by 2x
        tl = TimelineEngine.speed_change(sample_timeline, 0.0, 60.0, factor=2.0)
        # Source 30s in 2x segment should map to 15s
        pos = TimelineEngine.source_to_timeline(tl, 30.0)
        assert pos == 15.0
        # Source 90s (in 1x segment after 60s) -> 30s + (90-60) = 60s
        pos90 = TimelineEngine.source_to_timeline(tl, 90.0)
        assert pos90 == 60.0

    def test_source_to_timeline_after_cut_and_speed(self, sample_timeline):
        # Cut 0-30s
        tl = TimelineEngine.cut(sample_timeline, 0.0, 30.0)
        # Speed up 30-60s by 2x
        tl2 = TimelineEngine.speed_change(tl, 30.0, 60.0, factor=2.0)
        # Source 40s: (40 - 30)/2 = 5s on timeline
        assert TimelineEngine.source_to_timeline(tl2, 40.0) == 5.0

    def test_timeline_to_source_basic(self, sample_timeline):
        media_id, src_t = TimelineEngine.timeline_to_source(sample_timeline, 42.0)
        assert src_t == 42.0

    def test_timeline_to_source_after_cut(self, sample_timeline):
        tl = TimelineEngine.cut(sample_timeline, 0.0, 30.0)
        media_id, src_t = TimelineEngine.timeline_to_source(tl, 12.0)
        assert src_t == 42.0


class TestContentAnchors:
    def test_add_caption_anchor(self, sample_timeline, sample_source_media):
        anchor = ContentAnchor(
            type=AnchorType.CAPTION,
            source_media_id=sample_source_media.id,
            source_start_s=42.0,
            source_end_s=44.0,
            properties={"text": "Welcome!", "color": "white"}
        )
        tl = TimelineEngine.add_anchor(sample_timeline, anchor)
        assert len(tl.anchors) == 1
        pos = TimelineEngine.resolve_anchor_positions(tl)[0]
        assert pos["timeline_start_s"] == 42.0
        assert pos["timeline_end_s"] == 44.0

    def test_add_anchor_outside_timeline_raises(self, sample_timeline, sample_source_media):
        # Cut 0-100s
        tl = TimelineEngine.cut(sample_timeline, 0.0, 100.0)
        anchor = ContentAnchor(
            type=AnchorType.CAPTION,
            source_media_id=sample_source_media.id,
            source_start_s=42.0,
            source_end_s=44.0
        )
        with pytest.raises(ValueError, match="Cannot attach anchor"):
            TimelineEngine.add_anchor(tl, anchor)

    def test_anchor_survives_unrelated_cut(self, sample_timeline, sample_source_media):
        anchor = ContentAnchor(
            type=AnchorType.CAPTION,
            source_media_id=sample_source_media.id,
            source_start_s=42.0,
            source_end_s=44.0,
            properties={"text": "Welcome!"}
        )
        tl = TimelineEngine.add_anchor(sample_timeline, anchor)
        # Cut 100-150s (after anchor)
        tl2 = TimelineEngine.cut(tl, 100.0, 150.0)
        pos = TimelineEngine.resolve_anchor_positions(tl2)[0]
        assert pos["timeline_start_s"] == 42.0
        assert pos["active"] is True

    def test_anchor_follows_content_after_cut(self, sample_timeline, sample_source_media):
        anchor = ContentAnchor(
            type=AnchorType.CAPTION,
            source_media_id=sample_source_media.id,
            source_start_s=42.0,
            source_end_s=44.0,
            properties={"text": "Welcome!"}
        )
        tl = TimelineEngine.add_anchor(sample_timeline, anchor)
        # Cut first 30s
        tl2 = TimelineEngine.cut(tl, 0.0, 30.0)
        pos = TimelineEngine.resolve_anchor_positions(tl2)[0]
        assert pos["timeline_start_s"] == 12.0
        assert pos["timeline_end_s"] == 14.0
        assert pos["active"] is True

    def test_anchor_deactivated_on_full_cut(self, sample_timeline, sample_source_media):
        anchor = ContentAnchor(
            type=AnchorType.CAPTION,
            source_media_id=sample_source_media.id,
            source_start_s=42.0,
            source_end_s=44.0,
            properties={"text": "Welcome!"}
        )
        tl = TimelineEngine.add_anchor(sample_timeline, anchor)
        # Cut 40-50s containing the anchor
        tl2 = TimelineEngine.cut(tl, 40.0, 50.0)
        pos = TimelineEngine.resolve_anchor_positions(tl2)[0]
        assert pos["active"] is False
        assert any(w in pos.get("warning", "").lower() for w in ("inactive", "removed", "cut"))

    def test_anchor_partial_cut_adjusts_range(self, sample_timeline, sample_source_media):
        anchor = ContentAnchor(
            type=AnchorType.CAPTION,
            source_media_id=sample_source_media.id,
            source_start_s=40.0,
            source_end_s=50.0,
            properties={"text": "Long caption"}
        )
        tl = TimelineEngine.add_anchor(sample_timeline, anchor)
        # Cut 45-60s (cutting second half of caption)
        tl2 = TimelineEngine.cut(tl, 45.0, 60.0)
        pos = TimelineEngine.resolve_anchor_positions(tl2)[0]
        assert pos["active"] is True
        assert pos["timeline_end_s"] == 45.0

    def test_anchor_with_speed_change(self, sample_timeline, sample_source_media):
        anchor = ContentAnchor(
            type=AnchorType.CAPTION,
            source_media_id=sample_source_media.id,
            source_start_s=40.0,
            source_end_s=44.0,
            properties={"text": "Sped up caption"}
        )
        tl = TimelineEngine.add_anchor(sample_timeline, anchor)
        # Speed up 40-44s by 2x
        tl2 = TimelineEngine.speed_change(tl, 40.0, 44.0, factor=2.0)
        pos = TimelineEngine.resolve_anchor_positions(tl2)[0]
        assert pos["timeline_start_s"] == 40.0
        assert pos["timeline_end_s"] == 42.0
        assert pos["duration_s"] == 2.0

    def test_caption_minimum_duration_warning(self, sample_timeline, sample_source_media):
        # 1.0s caption sped up 2x -> 0.5s (<0.7s)
        anchor = ContentAnchor(
            type=AnchorType.CAPTION,
            source_media_id=sample_source_media.id,
            source_start_s=40.0,
            source_end_s=41.0,
            properties={"text": "Short caption"}
        )
        tl = TimelineEngine.add_anchor(sample_timeline, anchor)
        tl2 = TimelineEngine.speed_change(tl, 40.0, 41.0, factor=2.0)
        assert any("shorter than 0.7s" in (a.warning or "") for a in tl2.anchors)


class TestFillerAndSilenceRemoval:
    def test_remove_filler_words(self, sample_timeline, sample_transcript):
        tl, removed = TimelineEngine.remove_filler_words(sample_timeline, sample_transcript)
        assert len(removed) >= 4  # um, uh, like(filler)
        assert TimelineEngine.get_duration(tl) < 300.0

    def test_remove_fillers_preserves_legitimate_like(self, sample_timeline, sample_transcript):
        tl, removed = TimelineEngine.remove_filler_words(sample_timeline, sample_transcript)
        # 'like' at 100.0s is is_filler=False
        like_100_removed = any(r["source_start_s"] == 100.0 for r in removed)
        assert not like_100_removed

    def test_remove_silences(self, sample_timeline, sample_transcript):
        tl, removed = TimelineEngine.remove_silences(sample_timeline, sample_transcript, min_silence_s=2.0)
        assert len(removed) > 0
        assert TimelineEngine.get_duration(tl) < 300.0


class TestTimelineValidation:
    def test_validate_timeline_healthy(self, sample_timeline):
        issues = TimelineEngine.validate_timeline(sample_timeline)
        assert len(issues) == 0

    def test_validate_timeline_empty(self, sample_source_media):
        tl = Timeline(
            source_media_id=sample_source_media.id,
            segments=[],
            anchors=[]
        )
        issues = TimelineEngine.validate_timeline(tl)
        assert any("no segments" in i.lower() for i in issues)
