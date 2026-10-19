"""Unit tests for AnchorManager."""
from app.core.models import ContentAnchor, AnchorType
from app.core.timeline import TimelineEngine
from app.core.anchors import AnchorManager


class TestAnchorManager:
    def test_anchor_validity_active(self, sample_timeline, sample_source_media):
        anchor = ContentAnchor(
            type=AnchorType.CAPTION,
            source_media_id=sample_source_media.id,
            source_start_s=42.0,
            source_end_s=44.0
        )
        is_valid, warn = AnchorManager.check_anchor_validity(sample_timeline, anchor)
        assert is_valid is True
        assert warn is None

    def test_anchor_validity_after_cut(self, sample_timeline, sample_source_media):
        anchor = ContentAnchor(
            type=AnchorType.CAPTION,
            source_media_id=sample_source_media.id,
            source_start_s=10.0,
            source_end_s=20.0
        )
        tl_cut = TimelineEngine.cut(sample_timeline, 0.0, 30.0)
        is_valid, warn = AnchorManager.check_anchor_validity(tl_cut, anchor)
        assert is_valid is False
        assert warn is not None

    def test_find_caption_by_reference(self, sample_timeline, sample_source_media):
        a1 = ContentAnchor(type=AnchorType.CAPTION, source_media_id=sample_source_media.id, source_start_s=42.0, source_end_s=44.0, properties={"text": "Welcome to the channel!"})
        a2 = ContentAnchor(type=AnchorType.CAPTION, source_media_id=sample_source_media.id, source_start_s=80.0, source_end_s=82.0, properties={"text": "Subscribe now"})
        tl = TimelineEngine.add_anchor(sample_timeline, a1)
        tl = TimelineEngine.add_anchor(tl, a2)

        matches = AnchorManager.find_caption_by_reference(tl, "welcome")
        assert len(matches) == 1
        assert matches[0].properties["text"] == "Welcome to the channel!"

    def test_find_caption_by_reference_empty(self, sample_timeline):
        matches = AnchorManager.find_caption_by_reference(sample_timeline, "nonexistent")
        assert len(matches) == 0

    def test_get_visible_anchors(self, sample_timeline, sample_source_media):
        a1 = ContentAnchor(type=AnchorType.CAPTION, source_media_id=sample_source_media.id, source_start_s=42.0, source_end_s=44.0, active=True)
        a2 = ContentAnchor(type=AnchorType.CAPTION, source_media_id=sample_source_media.id, source_start_s=10.0, source_end_s=12.0, active=False)
        tl = TimelineEngine.add_anchor(sample_timeline, a1)
        tl.anchors.append(a2)

        visible = AnchorManager.get_visible_anchors(tl)
        assert len(visible) == 1
        assert visible[0].id == a1.id
