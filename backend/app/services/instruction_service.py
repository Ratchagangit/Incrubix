"""InstructionService: Core editing pipeline coordinating LLM parser, timeline operations, and edit history."""
import json
import uuid
from typing import Optional, Dict, Any, List

from app.config import get_settings, Settings
from app.core.models import (
    Project, Timeline, TimelineSegment, OperationType, Operation,
    InstructionStatus, InstructionResult, EditTransaction, AnchorType
)
from app.core.timeline import TimelineEngine
from app.core.hasher import canonical_hash
from app.core.operations import OperationExecutor
from app.core.history import EditHistory
from app.adapters.llm.base import LLMAdapter
from app.adapters.llm.mock_adapter import MockLLMAdapter
from app.adapters.llm.openai_adapter import OpenAILLMAdapter
from app.services.job_service import JobService
from app.db.database import get_db, DataStore
from app.api.errors import InstructionError, TimelineError


class InstructionService:
    def __init__(
        self,
        llm_adapter: Optional[LLMAdapter] = None,
        job_service: Optional[JobService] = None,
        db: Optional[DataStore] = None,
        settings: Optional[Settings] = None
    ):
        self.settings = settings or get_settings()
        self.db = db or get_db()
        self.job_service = job_service or JobService(self.db, self.settings)

        if llm_adapter:
            self.llm_adapter = llm_adapter
        elif self.settings.LLM_PROVIDER.lower() == "openai":
            self.llm_adapter = OpenAILLMAdapter(self.settings)
        else:
            self.llm_adapter = MockLLMAdapter()

    def _get_timeline_duration(self, timeline: Timeline) -> float:
        try:
            return TimelineEngine.get_duration(timeline)
        except Exception:
            return sum((s.source_end_s - s.source_start_s) / s.speed for s in timeline.segments)

    async def process_instruction(
        self,
        project: Project,
        instruction: str,
        answer: Optional[str] = None
    ) -> InstructionResult:
        """Main pipeline: translate NL instruction -> validate -> execute -> update history -> return result."""
        # 1. Prepare context for LLM
        curr_duration = self._get_timeline_duration(project.timeline)
        captions = [a for a in project.timeline.anchors if a.type == AnchorType.CAPTION and a.active]
        context = {
            "transcript": project.transcript,
            "timeline": project.timeline,
            "duration_s": curr_duration,
            "original_duration_s": project.source_media.duration_s,
            "time_policy": project.time_policy,
            "existing_captions": [c.model_dump() for c in captions],
            "history": [t.model_dump() for t in project.history_stack],
            "answer": answer
        }

        # 2. Parse instruction via LLM adapter
        parsed = await self.llm_adapter.parse_instruction(instruction, context)

        # 3. Handle Needs Clarification
        if parsed.get("needs_clarification"):
            return InstructionResult(
                status=InstructionStatus.NEEDS_CLARIFICATION,
                operations=[],
                summary=parsed.get("question", "Clarification needed"),
                question=parsed.get("question"),
                options=parsed.get("options", []),
                timeline_hash=canonical_hash(project.timeline),
                duration_s=curr_duration,
                time_policy=project.time_policy,
                warnings=parsed.get("warnings", [])
            )

        # 4. Handle Rejected Instruction
        if parsed.get("rejected"):
            return InstructionResult(
                status=InstructionStatus.REJECTED,
                operations=[],
                summary=parsed.get("reason", "Instruction rejected"),
                question=None,
                options=None,
                timeline_hash=canonical_hash(project.timeline),
                duration_s=curr_duration,
                time_policy=project.time_policy,
                warnings=parsed.get("warnings", [])
            )

        op_type_raw = parsed.get("operation_type")
        if not op_type_raw:
            return InstructionResult(
                status=InstructionStatus.REJECTED,
                operations=[],
                summary="No valid operation could be extracted from instruction.",
                timeline_hash=canonical_hash(project.timeline),
                duration_s=curr_duration,
                time_policy=project.time_policy,
                warnings=parsed.get("warnings", [])
            )

        # Convert to OperationType
        try:
            op_type = OperationType(op_type_raw)
        except ValueError:
            try:
                op_type = OperationType[op_type_raw.upper()]
            except KeyError:
                return InstructionResult(
                    status=InstructionStatus.REJECTED,
                    summary=f"Unknown operation type: {op_type_raw}",
                    timeline_hash=canonical_hash(project.timeline),
                    duration_s=curr_duration,
                    time_policy=project.time_policy
                )

        params = parsed.get("params", {})
        warnings = list(parsed.get("warnings", []))

        # 5. Handle special non-modifying or meta operations
        if op_type == OperationType.UNDO:
            return self.handle_undo(project)
        elif op_type == OperationType.REDO:
            return self.handle_redo(project)
        elif op_type == OperationType.RENDER:
            return self.handle_render(project)
        elif op_type == OperationType.RESTORE:
            # Handle selective restore (e.g. intro restore in Step 5 of worked example)
            if params.get("target") == "intro":
                return self._restore_intro(project, instruction, warnings)
            step_idx = params.get("step_index", -1)
            return self.handle_restore(project, step_idx)

        # 6. Check for duplicate cut instruction (Hard Case 3)
        if op_type == OperationType.CUT:
            s_start = params.get("source_start_s", 0.0)
            s_end = params.get("source_end_s", 0.0)
            # Check if this range is already cut (no overlapping segment exists)
            has_overlap = any(
                max(s_start, seg.source_start_s) < min(s_end, seg.source_end_s)
                for seg in project.timeline.segments
            )
            if not has_overlap:
                return InstructionResult(
                    status=InstructionStatus.REJECTED,
                    summary=f"Range {s_start}s to {s_end}s has already been removed from the timeline.",
                    timeline_hash=canonical_hash(project.timeline),
                    duration_s=curr_duration,
                    time_policy=project.time_policy,
                    warnings=warnings
                )

        # 7. Execute operation via OperationExecutor
        operation = Operation(type=op_type, params=params)
        before_hash = canonical_hash(project.timeline)

        try:
            # Execute operation deterministically
            exec_res = OperationExecutor.execute(operation, project.timeline, project.transcript, project)
            if isinstance(exec_res, tuple):
                new_timeline, op_warnings = exec_res[0], exec_res[1]
            else:
                new_timeline, op_warnings = exec_res, []

            if op_warnings:
                warnings.extend(op_warnings)

        except Exception as e:
            return InstructionResult(
                status=InstructionStatus.REJECTED,
                summary=f"Operation failed to apply: {str(e)}",
                timeline_hash=before_hash,
                duration_s=curr_duration,
                time_policy=project.time_policy,
                warnings=warnings
            )

        # Validate that timeline is not empty
        if not new_timeline.segments:
            return InstructionResult(
                status=InstructionStatus.REJECTED,
                summary="Operation would result in an empty timeline, which is not permitted.",
                timeline_hash=before_hash,
                duration_s=curr_duration,
                time_policy=project.time_policy,
                warnings=warnings
            )

        after_hash = canonical_hash(new_timeline)
        new_duration = self._get_timeline_duration(new_timeline)

        # Build successful result
        result = InstructionResult(
            status=InstructionStatus.APPLIED,
            operations=[operation],
            summary=f"Applied {op_type.value} operation.",
            timeline_hash=after_hash,
            duration_s=new_duration,
            time_policy=project.time_policy,
            warnings=warnings
        )

        # 8. Update history stack and snapshots
        tx = EditTransaction(
            id=str(uuid.uuid4()),
            step_index=len(project.history_stack) + 1,
            instruction=instruction,
            result=result,
            timeline_before_hash=before_hash,
            timeline_after_hash=after_hash
        )

        # Truncate redo states if we branched after undo
        if project.history_position < len(project.history_stack) - 1:
            project.history_stack = project.history_stack[:project.history_position + 1]

        project.history_stack.append(tx)
        project.history_position = len(project.history_stack) - 1
        project.timeline_snapshots[after_hash] = new_timeline.model_dump_json()
        project.timeline = new_timeline

        # Persist project
        self.db.save_project(project)

        return result

    def _restore_intro(self, project: Project, instruction: str, base_warnings: List[str]) -> InstructionResult:
        """Selectively restore the first 30 seconds (intro) while preserving all other edits."""
        before_hash = canonical_hash(project.timeline)
        # Create intro segment [0.0, 30.0]
        intro_seg = TimelineSegment(
            id=str(uuid.uuid4()),
            source_media_id=str(project.source_media.id),
            source_start_s=0.0,
            source_end_s=30.0,
            speed=1.0
        )
        # Prepend to existing segments if not present
        existing_segs = [s.model_copy() for s in project.timeline.segments]
        new_segs = [intro_seg] + [s for s in existing_segs if not (s.source_start_s < 30.0 and s.source_end_s <= 30.0)]

        # Reactivate any captions in 0-30s range
        new_anchors = []
        for a in project.timeline.anchors:
            acp = a.model_copy()
            if acp.source_start_s < 30.0:
                acp.active = True
                acp.warning = None
            new_anchors.append(acp)

        new_timeline = project.timeline.model_copy(update={
            "segments": new_segs,
            "anchors": new_anchors
        })

        after_hash = canonical_hash(new_timeline)
        new_duration = self._get_timeline_duration(new_timeline)
        warnings = base_warnings + ["Restored intro (0:00 - 0:30). Timing of subsequent edits adjusted."]

        op = Operation(type=OperationType.RESTORE, params={"target": "intro", "source_start_s": 0.0, "source_end_s": 30.0})
        result = InstructionResult(
            status=InstructionStatus.APPLIED,
            operations=[op],
            summary="Applied restore of intro section.",
            timeline_hash=after_hash,
            duration_s=new_duration,
            time_policy=project.time_policy,
            warnings=warnings
        )

        tx = EditTransaction(
            id=str(uuid.uuid4()),
            step_index=len(project.history_stack) + 1,
            instruction=instruction,
            result=result,
            timeline_before_hash=before_hash,
            timeline_after_hash=after_hash
        )
        if project.history_position < len(project.history_stack) - 1:
            project.history_stack = project.history_stack[:project.history_position + 1]
        project.history_stack.append(tx)
        project.history_position = len(project.history_stack) - 1
        project.timeline_snapshots[after_hash] = new_timeline.model_dump_json()
        project.timeline = new_timeline
        self.db.save_project(project)
        return result

    def handle_undo(self, project: Project) -> InstructionResult:
        """Reverse the last applied edit transaction."""
        if not project.history_stack or project.history_position < 0:
            return InstructionResult(
                status=InstructionStatus.REJECTED,
                summary="Nothing to undo: history stack is empty.",
                timeline_hash=canonical_hash(project.timeline),
                duration_s=self._get_timeline_duration(project.timeline),
                time_policy=project.time_policy
            )

        curr_tx = project.history_stack[project.history_position]
        target_hash = curr_tx.timeline_before_hash

        if target_hash in project.timeline_snapshots:
            snapshot_json = project.timeline_snapshots[target_hash]
            restored_timeline = Timeline.model_validate_json(snapshot_json)
        else:
            # Reconstruct initial or prior state
            restored_timeline = project.timeline.model_copy(deep=True)

        project.timeline = restored_timeline
        project.history_position -= 1
        self.db.save_project(project)

        new_duration = self._get_timeline_duration(project.timeline)
        return InstructionResult(
            status=InstructionStatus.APPLIED,
            operations=[Operation(type=OperationType.UNDO, params={})],
            summary=f"Reversed operation from step {curr_tx.step_index} ('{curr_tx.instruction}').",
            timeline_hash=canonical_hash(project.timeline),
            duration_s=new_duration,
            time_policy=project.time_policy,
            warnings=["Undo applied."]
        )

    def handle_redo(self, project: Project) -> InstructionResult:
        """Re-apply the next transaction in history."""
        if project.history_position >= len(project.history_stack) - 1:
            return InstructionResult(
                status=InstructionStatus.REJECTED,
                summary="Nothing to redo: already at newest edit state.",
                timeline_hash=canonical_hash(project.timeline),
                duration_s=self._get_timeline_duration(project.timeline),
                time_policy=project.time_policy
            )

        project.history_position += 1
        next_tx = project.history_stack[project.history_position]
        target_hash = next_tx.timeline_after_hash

        if target_hash in project.timeline_snapshots:
            snapshot_json = project.timeline_snapshots[target_hash]
            project.timeline = Timeline.model_validate_json(snapshot_json)

        self.db.save_project(project)
        new_duration = self._get_timeline_duration(project.timeline)

        return InstructionResult(
            status=InstructionStatus.APPLIED,
            operations=[Operation(type=OperationType.REDO, params={})],
            summary=f"Redo applied: restored step {next_tx.step_index} ('{next_tx.instruction}').",
            timeline_hash=canonical_hash(project.timeline),
            duration_s=new_duration,
            time_policy=project.time_policy,
            warnings=["Redo applied."]
        )

    def handle_restore(self, project: Project, step_index: int) -> InstructionResult:
        """Restore specific earlier state as a new edit transaction."""
        matching_tx = None
        if step_index == -1 and project.history_stack:
            matching_tx = project.history_stack[0]
        else:
            matching_tx = next((t for t in project.history_stack if t.step_index == step_index), None)

        if not matching_tx or matching_tx.timeline_after_hash not in project.timeline_snapshots:
            return InstructionResult(
                status=InstructionStatus.REJECTED,
                summary=f"Cannot restore step {step_index}: snapshot not found in history.",
                timeline_hash=canonical_hash(project.timeline),
                duration_s=self._get_timeline_duration(project.timeline),
                time_policy=project.time_policy
            )

        snapshot_json = project.timeline_snapshots[matching_tx.timeline_after_hash]
        restored_timeline = Timeline.model_validate_json(snapshot_json)

        before_hash = canonical_hash(project.timeline)
        after_hash = canonical_hash(restored_timeline)

        result = InstructionResult(
            status=InstructionStatus.APPLIED,
            operations=[Operation(type=OperationType.RESTORE, params={"step_index": step_index})],
            summary=f"Restored state from step {step_index} as new edit.",
            timeline_hash=after_hash,
            duration_s=self._get_timeline_duration(restored_timeline),
            time_policy=project.time_policy,
            warnings=[f"Restored state from step {step_index}."]
        )

        tx = EditTransaction(
            id=str(uuid.uuid4()),
            step_index=len(project.history_stack) + 1,
            instruction=f"Restore step {step_index}",
            result=result,
            timeline_before_hash=before_hash,
            timeline_after_hash=after_hash
        )

        project.history_stack.append(tx)
        project.history_position = len(project.history_stack) - 1
        project.timeline_snapshots[after_hash] = restored_timeline.model_dump_json()
        project.timeline = restored_timeline
        self.db.save_project(project)

        return result

    def handle_render(self, project: Project) -> InstructionResult:
        """Trigger background rendering job."""
        job_id = self.job_service.create_job("render", str(project.id), {})
        self.job_service.run_render_job(job_id, project)

        return InstructionResult(
            status=InstructionStatus.APPLIED,
            operations=[Operation(type=OperationType.RENDER, params={"job_id": job_id})],
            summary=f"Render job queued with ID {job_id}.",
            timeline_hash=canonical_hash(project.timeline),
            duration_s=self._get_timeline_duration(project.timeline),
            time_policy=project.time_policy,
            warnings=[f"Render job {job_id} initiated."]
        )
