"""EditHistory: Tracks timeline state transitions, linear undo/redo, and non-destructive branch restore."""
import uuid
from typing import List
from app.core.models import Timeline, EditTransaction, InstructionResult
from app.core.hasher import canonical_hash


class EditHistory:
    def __init__(self, initial_timeline: Timeline):
        self._initial_timeline = initial_timeline.model_copy(deep=True)
        self._transactions: List[EditTransaction] = []
        self._timeline_states: List[Timeline] = [initial_timeline.model_copy(deep=True)]
        self._position: int = 0

    def apply(
        self,
        instruction: str,
        step_index: int,
        result: InstructionResult,
        new_timeline: Timeline
    ) -> EditTransaction:
        """Apply a new state transition. Clears redo history after current position."""
        # Truncate any redo branches
        self._timeline_states = self._timeline_states[: self._position + 1]
        self._transactions = self._transactions[: self._position]

        before_hash = canonical_hash(self.get_current_timeline())
        after_hash = canonical_hash(new_timeline)

        tx = EditTransaction(
            id=str(uuid.uuid4()),
            step_index=step_index,
            instruction=instruction,
            result=result,
            timeline_before_hash=before_hash,
            timeline_after_hash=after_hash
        )

        self._transactions.append(tx)
        self._timeline_states.append(new_timeline.model_copy(deep=True))
        self._position += 1

        return tx

    def undo(self) -> Timeline:
        """Step back one state in history."""
        if not self.can_undo():
            raise ValueError("Cannot undo: already at initial timeline state")
        self._position -= 1
        return self.get_current_timeline()

    def redo(self) -> Timeline:
        """Step forward one state in history."""
        if not self.can_redo():
            raise ValueError("Cannot redo: already at latest timeline state")
        self._position += 1
        return self.get_current_timeline()

    def restore(self, step_index: int) -> Timeline:
        """Restore specific earlier state as a new edit appended at current position."""
        if step_index < 0 or step_index >= len(self._timeline_states):
            raise ValueError(f"Invalid step index {step_index} for history of length {len(self._timeline_states)}")

        target_state = self._timeline_states[step_index].model_copy(deep=True)
        return target_state

    def get_current_timeline(self) -> Timeline:
        return self._timeline_states[self._position].model_copy(deep=True)

    def can_undo(self) -> bool:
        return self._position > 0

    def can_redo(self) -> bool:
        return self._position < len(self._timeline_states) - 1

    def get_transactions(self) -> List[EditTransaction]:
        return list(self._transactions)

    def get_position(self) -> int:
        return self._position
