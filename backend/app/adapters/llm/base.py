from abc import ABC, abstractmethod
from typing import Dict, Any


class LLMAdapter(ABC):
    """Abstract base class for LLM natural language instruction parsers."""

    @abstractmethod
    async def parse_instruction(self, instruction: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse natural language instruction into structured editing operations.

        Args:
            instruction: User prompt instruction string.
            context: Dictionary containing:
                - transcript: Transcript object or list of transcript words.
                - timeline: Current Timeline object.
                - duration_s: Current timeline duration in seconds.
                - original_duration_s: Source media duration.
                - time_policy: 'current' or 'original'.
                - existing_captions: List of existing caption anchors.
                - history: List of prior transactions.
                - pending_clarification: Previous question or state if answering.
                - answer: Optional user answer to previous clarification.

        Returns:
            Dict containing:
                - operation_type: str (e.g. 'CUT', 'ADD_CAPTION', etc.) or None if clarification/rejected.
                - operations: list of dicts (for multi-part operations).
                - params: dict of parameters for the operation.
                - needs_clarification: bool.
                - question: Optional[str].
                - options: Optional[list[str]].
                - rejected: bool.
                - reason: Optional[str].
                - warnings: list[str].
        """
        pass
