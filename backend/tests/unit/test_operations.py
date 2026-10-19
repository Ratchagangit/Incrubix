"""Unit tests for OperationExecutor."""
import pytest
from app.core.models import Operation, OperationType
from app.core.timeline import TimelineEngine
from app.core.operations import OperationExecutor


class TestOperationExecutor:
    def test_execute_cut(self, sample_timeline, sample_transcript, sample_project):
        op = Operation(type=OperationType.CUT, params={"source_start_s": 0.0, "source_end_s": 30.0})
        tl_new, warnings = OperationExecutor.execute(op, sample_timeline, sample_transcript, sample_project)
        assert TimelineEngine.get_duration(tl_new) == 270.0
        assert len(warnings) > 0

    def test_execute_keep(self, sample_timeline, sample_transcript, sample_project):
        op = Operation(type=OperationType.KEEP, params={"source_start_s": 50.0, "source_end_s": 150.0})
        tl_new, warnings = OperationExecutor.execute(op, sample_timeline, sample_transcript, sample_project)
        assert TimelineEngine.get_duration(tl_new) == 100.0

    def test_execute_speed(self, sample_timeline, sample_transcript, sample_project):
        op = Operation(type=OperationType.SPEED, params={"source_start_s": 60.0, "source_end_s": 120.0, "factor": 2.0})
        tl_new, warnings = OperationExecutor.execute(op, sample_timeline, sample_transcript, sample_project)
        assert TimelineEngine.get_duration(tl_new) == 270.0

    def test_execute_add_caption(self, sample_timeline, sample_transcript, sample_project):
        op = Operation(
            type=OperationType.ADD_CAPTION,
            params={
                "text": "Hello World",
                "source_start_s": 42.0,
                "source_end_s": 44.0,
                "color": "white"
            }
        )
        tl_new, warnings = OperationExecutor.execute(op, sample_timeline, sample_transcript, sample_project)
        assert len(tl_new.anchors) == 1
        assert tl_new.anchors[0].properties["text"] == "Hello World"

    def test_execute_mute(self, sample_timeline, sample_transcript, sample_project):
        op = Operation(
            type=OperationType.MUTE,
            params={"source_start_s": 10.0, "source_end_s": 12.0}
        )
        tl_new, warnings = OperationExecutor.execute(op, sample_timeline, sample_transcript, sample_project)
        assert any(a.type.value == "mute" for a in tl_new.anchors)

    def test_execute_bleep(self, sample_timeline, sample_transcript, sample_project):
        op = Operation(
            type=OperationType.BLEEP,
            params={"source_start_s": 88.0, "source_end_s": 88.5}
        )
        tl_new, warnings = OperationExecutor.execute(op, sample_timeline, sample_transcript, sample_project)
        assert any(a.type.value == "bleep" for a in tl_new.anchors)

    def test_execute_invalid_cut_rejected(self, sample_timeline, sample_transcript, sample_project):
        # Attempt to cut beyond duration raises ValueError
        op = Operation(type=OperationType.CUT, params={"source_start_s": 400.0, "source_end_s": 500.0})
        with pytest.raises(ValueError, match="outside current timeline"):
            OperationExecutor.execute(op, sample_timeline, sample_transcript, sample_project)
