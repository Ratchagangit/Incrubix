"""OpenAI LLM Adapter for natural language prompt parsing."""
import json
import asyncio
from typing import Dict, Any, Optional
from app.adapters.llm.base import LLMAdapter
from app.config import get_settings, Settings
from app.api.errors import InstructionError


SYSTEM_PROMPT = """You are the natural language parsing engine for IncuBrix, a prompt-based video editing platform.
Translate user editing instructions into structured operations.
Available OperationTypes:
- CUT: {"source_start_s": float, "source_end_s": float}
- KEEP: {"source_start_s": float, "source_end_s": float}
- REORDER: {"segment_order": list[int]}
- SPEED: {"source_start_s": float, "source_end_s": float, "factor": float}
- MUTE: {"source_start_s": float, "source_end_s": float, "word": str}
- BLEEP: {"source_start_s": float, "source_end_s": float, "word": str}
- ADD_CAPTION: {"text": str, "source_start_s": float, "source_end_s": float, "position": str, "color": str, "font_size": int}
- AUTO_CAPTION: {}
- REMOVE_FILLERS: {"filler_words": list[str]}
- REMOVE_SILENCES: {"min_silence_s": float}
- ADD_MUSIC: {"source_path": str, "volume": float, "duck_volume": float}
- MODIFY_CAPTION: {"color": Optional[str], "font_size": Optional[int], "position": Optional[str]}
- UNDO: {}
- REDO: {}
- RESTORE: {"target": Optional[str], "step_index": Optional[int]}
- RENDER: {}

Return strict JSON with this exact schema:
{
    "operation_type": "CUT" | "KEEP" | ... | null,
    "params": dict,
    "needs_clarification": bool,
    "question": str | null,
    "options": list[str] | null,
    "rejected": bool,
    "reason": str | null,
    "warnings": list[str]
}

Rules:
1. If the instruction is ambiguous, set needs_clarification=true and provide a helpful question with options.
2. If the instruction asks for an impossible action (like cutting the entire video to empty), set rejected=true with a clear reason.
3. For references like "make that caption red", if no captions exist in context, set rejected=true.
4. Output valid JSON only.
"""


class OpenAILLMAdapter(LLMAdapter):
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.api_key = self.settings.OPENAI_API_KEY
        self.model = self.settings.OPENAI_MODEL

    async def parse_instruction(self, instruction: str, context: Dict[str, Any]) -> Dict[str, Any]:
        if not self.api_key:
            # Fallback to mock adapter if API key is not configured
            from app.adapters.llm.mock_adapter import MockLLMAdapter
            return await MockLLMAdapter().parse_instruction(instruction, context)

        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=self.api_key)

            context_summary = {
                "duration_s": context.get("duration_s"),
                "time_policy": context.get("time_policy"),
                "existing_captions_count": len(context.get("existing_captions", [])),
                "existing_captions": context.get("existing_captions", []),
                "answer": context.get("answer")
            }

            user_prompt = f"Instruction: {instruction}\nContext: {json.dumps(context_summary)}"

            # Call with retries
            for attempt in range(3):
                try:
                    response = await client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": user_prompt}
                        ],
                        response_format={"type": "json_object"},
                        temperature=0.0
                    )
                    content = response.choices[0].message.content
                    parsed = json.loads(content)
                    return {
                        "operation_type": parsed.get("operation_type"),
                        "params": parsed.get("params", {}),
                        "needs_clarification": bool(parsed.get("needs_clarification", False)),
                        "question": parsed.get("question"),
                        "options": parsed.get("options"),
                        "rejected": bool(parsed.get("rejected", False)),
                        "reason": parsed.get("reason"),
                        "warnings": parsed.get("warnings", [])
                    }
                except Exception as ex:
                    if attempt == 2:
                        raise ex
                    await asyncio.sleep(1.0)

        except Exception as e:
            # Fallback to mock adapter on OpenAI connection error
            from app.adapters.llm.mock_adapter import MockLLMAdapter
            result = await MockLLMAdapter().parse_instruction(instruction, context)
            result.setdefault("warnings", []).append(f"OpenAI API error fallback: {str(e)}")
            return result
