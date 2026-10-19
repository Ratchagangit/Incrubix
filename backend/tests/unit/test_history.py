"""Unit tests for EditHistory and linear/branch restoration."""
import pytest
from app.core.models import InstructionStatus, InstructionResult
from app.core.timeline import TimelineEngine
from app.core.history import EditHistory
from app.core.hasher import canonical_hash


class TestEditHistory:
    def test_initial_state(self, sample_timeline):
        hist = EditHistory(sample_timeline)
        assert hist.get_position() == 0
        assert not hist.can_undo()
        assert not hist.can_redo()
        assert len(hist.get_transactions()) == 0

    def test_apply_single_edit(self, sample_timeline):
        hist = EditHistory(sample_timeline)
        tl2 = TimelineEngine.cut(sample_timeline, 0.0, 30.0)
        res = InstructionResult(
            status=InstructionStatus.APPLIED,
            summary="Cut first 30s",
            timeline_hash=canonical_hash(tl2),
            duration_s=270.0
        )
        tx = hist.apply("Cut the first 30 seconds", 1, res, tl2)

        assert hist.get_position() == 1
        assert hist.can_undo()
        assert not hist.can_redo()
        assert len(hist.get_transactions()) == 1
        assert tx.step_index == 1
        assert TimelineEngine.get_duration(hist.get_current_timeline()) == 270.0

    def test_undo_restores_previous(self, sample_timeline):
        hist = EditHistory(sample_timeline)
        tl2 = TimelineEngine.cut(sample_timeline, 0.0, 30.0)
        res = InstructionResult(
            status=InstructionStatus.APPLIED,
            summary="Cut first 30s",
            timeline_hash=canonical_hash(tl2),
            duration_s=270.0
        )
        hist.apply("Cut first 30s", 1, res, tl2)

        undone_tl = hist.undo()
        assert hist.get_position() == 0
        assert TimelineEngine.get_duration(undone_tl) == 300.0
        assert not hist.can_undo()
        assert hist.can_redo()

    def test_redo_reapplies(self, sample_timeline):
        hist = EditHistory(sample_timeline)
        tl2 = TimelineEngine.cut(sample_timeline, 0.0, 30.0)
        res = InstructionResult(
            status=InstructionStatus.APPLIED,
            summary="Cut first 30s",
            timeline_hash=canonical_hash(tl2),
            duration_s=270.0
        )
        hist.apply("Cut first 30s", 1, res, tl2)

        hist.undo()
        redone_tl = hist.redo()
        assert hist.get_position() == 1
        assert TimelineEngine.get_duration(redone_tl) == 270.0
        assert hist.can_undo()
        assert not hist.can_redo()

    def test_undo_at_start_raises(self, sample_timeline):
        hist = EditHistory(sample_timeline)
        with pytest.raises(ValueError, match="Cannot undo"):
            hist.undo()

    def test_redo_at_end_raises(self, sample_timeline):
        hist = EditHistory(sample_timeline)
        with pytest.raises(ValueError, match="Cannot redo"):
            hist.redo()

    def test_new_edit_clears_redo(self, sample_timeline):
        hist = EditHistory(sample_timeline)
        # Apply Edit 1
        tl1 = TimelineEngine.cut(sample_timeline, 0.0, 30.0)
        res1 = InstructionResult(status=InstructionStatus.APPLIED, summary="Edit 1", timeline_hash=canonical_hash(tl1), duration_s=270.0)
        hist.apply("Edit 1", 1, res1, tl1)

        # Apply Edit 2
        tl2 = TimelineEngine.cut(tl1, 100.0, 150.0)
        res2 = InstructionResult(status=InstructionStatus.APPLIED, summary="Edit 2", timeline_hash=canonical_hash(tl2), duration_s=220.0)
        hist.apply("Edit 2", 2, res2, tl2)

        # Undo Edit 2
        hist.undo()
        assert hist.can_redo()

        # Apply new Edit 3 -> should clear redo history
        tl3 = TimelineEngine.cut(tl1, 200.0, 250.0)
        res3 = InstructionResult(status=InstructionStatus.APPLIED, summary="Edit 3", timeline_hash=canonical_hash(tl3), duration_s=220.0)
        hist.apply("Edit 3", 3, res3, tl3)

        assert not hist.can_redo()
        assert hist.get_position() == 2

    def test_restore_specific_earlier_edit(self, sample_timeline):
        hist = EditHistory(sample_timeline)
        # Edit 1: Cut 0-30s
        tl1 = TimelineEngine.cut(sample_timeline, 0.0, 30.0)
        res1 = InstructionResult(status=InstructionStatus.APPLIED, summary="Cut 0-30", timeline_hash=canonical_hash(tl1), duration_s=270.0)
        hist.apply("Cut 0-30", 1, res1, tl1)

        # Edit 2: Cut 100-150
        tl2 = TimelineEngine.cut(tl1, 100.0, 150.0)
        res2 = InstructionResult(status=InstructionStatus.APPLIED, summary="Cut 100-150", timeline_hash=canonical_hash(tl2), duration_s=220.0)
        hist.apply("Cut 100-150", 2, res2, tl2)

        # Restore step index 1 (after Edit 1)
        restored = hist.restore(1)
        assert TimelineEngine.get_duration(restored) == 270.0
