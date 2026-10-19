"""Unit tests for deterministic canonical timeline hashing."""
import copy
from app.core.models import ContentAnchor, AnchorType
from app.core.timeline import TimelineEngine
from app.core.hasher import canonical_hash


class TestCanonicalHasher:
    def test_same_timeline_same_hash(self, sample_timeline):
        h1 = canonical_hash(sample_timeline)
        h2 = canonical_hash(sample_timeline)
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex string

    def test_different_timeline_different_hash(self, sample_timeline):
        h1 = canonical_hash(sample_timeline)
        tl2 = TimelineEngine.cut(sample_timeline, 0.0, 30.0)
        h2 = canonical_hash(tl2)
        assert h1 != h2

    def test_hash_ignores_ephemeral_segment_ids(self, sample_timeline):
        # Create identical timeline content but with fresh segment IDs
        h1 = canonical_hash(sample_timeline)
        tl_copy = sample_timeline.model_copy(deep=True)
        for s in tl_copy.segments:
            s.id = "completely-different-random-uuid"
        h2 = canonical_hash(tl_copy)
        assert h1 == h2

    def test_hash_deterministic_across_repeated_runs(self, sample_timeline, sample_source_media):
        # Build identical timeline through sequence of operations 3 times
        hashes = []
        for _ in range(3):
            tl = TimelineEngine.create_initial(sample_source_media)
            anchor = ContentAnchor(
                type=AnchorType.CAPTION,
                source_media_id=sample_source_media.id,
                source_start_s=42.0,
                source_end_s=44.0,
                properties={"text": "Welcome!"}
            )
            tl = TimelineEngine.add_anchor(tl, anchor)
            tl = TimelineEngine.cut(tl, 0.0, 30.0)
            tl = TimelineEngine.speed_change(tl, 60.0, 90.0, factor=2.0)
            hashes.append(canonical_hash(tl))

        assert hashes[0] == hashes[1] == hashes[2]

    def test_hash_deterministic_anchor_ordering(self, sample_timeline, sample_source_media):
        # Adding anchors in different order produces the exact same hash
        a1 = ContentAnchor(type=AnchorType.CAPTION, source_media_id=sample_source_media.id, source_start_s=10.0, source_end_s=12.0)
        a2 = ContentAnchor(type=AnchorType.MUTE, source_media_id=sample_source_media.id, source_start_s=20.0, source_end_s=22.0)

        tl1 = TimelineEngine.add_anchor(sample_timeline, a1)
        tl1 = TimelineEngine.add_anchor(tl1, a2)

        tl2 = TimelineEngine.add_anchor(sample_timeline, a2)
        tl2 = TimelineEngine.add_anchor(tl2, a1)

        assert canonical_hash(tl1) == canonical_hash(tl2)
