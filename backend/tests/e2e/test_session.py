"""End-to-End verification of the 8-Step Worked Example."""
import pytest
from app.core.models import (
    SourceMedia, TranscriptWord, Transcript, InstructionStatus, AnchorType
)
from app.core.timeline import TimelineEngine
from app.core.hasher import canonical_hash
from app.core.models import Project
from app.services.instruction_service import InstructionService


@pytest.mark.asyncio
class TestWorkedExampleEndToEnd:
    async def test_complete_8_step_worked_example(self, sample_source_media):
        # 1. Setup media & transcript
        words = [
            TranscriptWord(word="welcome", start_s=42.0, end_s=42.4, speaker="host", confidence=0.99),
            TranscriptWord(word="to", start_s=42.4, end_s=42.6, speaker="host", confidence=0.99),
            TranscriptWord(word="the", start_s=42.6, end_s=42.8, speaker="host", confidence=0.99),
            TranscriptWord(word="channel", start_s=42.8, end_s=43.5, speaker="host", confidence=0.98),
            TranscriptWord(word="pricing", start_s=65.0, end_s=65.8, speaker="host", confidence=0.92),
            TranscriptWord(word="pricing", start_s=160.0, end_s=160.7, speaker="guest", confidence=0.94),
            TranscriptWord(word="pricing", start_s=195.0, end_s=195.6, speaker="host", confidence=0.93)
        ]
        tr = Transcript(source_media_id=sample_source_media.id, words=words, speakers=["host", "guest"])
        tl = TimelineEngine.create_initial(sample_source_media)
        project = Project(source_media=sample_source_media, transcript=tr, timeline=tl)
        service = InstructionService()

        # Step 1: Add caption 'Welcome!' when I say welcome to the channel
        r1 = await service.process_instruction(
            project, "Add a caption 'Welcome!' when I say welcome to the channel"
        )
        assert r1.status == InstructionStatus.APPLIED
        assert len(project.timeline.anchors) == 1
        pos1 = TimelineEngine.resolve_anchor_positions(project.timeline)[0]
        assert pos1["timeline_start_s"] == 42.0
        assert pos1["timeline_end_s"] == 43.5
        assert r1.duration_s == 300.0

        # Step 2: Cut the first 30 seconds
        r2 = await service.process_instruction(project, "Cut the first 30 seconds")
        assert r2.status == InstructionStatus.APPLIED
        assert r2.duration_s == 270.0
        # CRITICAL: Verify caption shifted to 12.0s - 13.5s
        pos2 = TimelineEngine.resolve_anchor_positions(project.timeline)[0]
        assert pos2["timeline_start_s"] == 12.0
        assert pos2["timeline_end_s"] == 13.5
        assert pos2["active"] is True

        # Step 3: Remove the part about pricing -> Needs Clarification
        r3 = await service.process_instruction(project, "Remove the part about pricing")
        assert r3.status == InstructionStatus.NEEDS_CLARIFICATION
        assert r3.question is not None
        assert "3 times" in r3.question
        # Timeline remains unchanged at 270.0s
        assert TimelineEngine.get_duration(project.timeline) == 270.0

        # Step 3a: Answer "the second one"
        r3a = await service.process_instruction(project, "Remove the part about pricing", answer="the second one")
        assert r3a.status == InstructionStatus.APPLIED
        assert r3a.duration_s == 265.0  # 5 seconds cut (158-163)

        # Step 4: Speed up from 1:00 to 1:30 by 2x
        r4 = await service.process_instruction(project, "Speed up from 1:00 to 1:30 by 2x")
        assert r4.status == InstructionStatus.APPLIED
        assert r4.duration_s == 250.0  # 30s cut in half -> -15s
        assert any("time policy" in w.lower() for w in r4.warnings)

        # Step 5: Actually, put the intro back
        r5 = await service.process_instruction(project, "Actually, put the intro back")
        assert r5.status == InstructionStatus.APPLIED
        assert r5.duration_s == 280.0  # +30s intro restored
        # Caption returned to original 42.0s
        pos5 = TimelineEngine.resolve_anchor_positions(project.timeline)[0]
        assert pos5["timeline_start_s"] == 42.0

        # Step 6: Undo
        r6 = await service.process_instruction(project, "Undo")
        assert r6.status == InstructionStatus.APPLIED
        assert r6.duration_s == 250.0  # Intro cut again
        pos6 = TimelineEngine.resolve_anchor_positions(project.timeline)[0]
        assert pos6["timeline_start_s"] == 12.0

        # Step 7: Make that caption red
        r7 = await service.process_instruction(project, "Make that caption red")
        assert r7.status == InstructionStatus.APPLIED
        pos7 = TimelineEngine.resolve_anchor_positions(project.timeline)[0]
        assert pos7["properties"]["color"] == "red"

        # Step 8: Render
        r8 = await service.process_instruction(project, "Render")
        assert r8.status == InstructionStatus.APPLIED
        assert any(op.type.value == "RENDER" for op in r8.operations)
