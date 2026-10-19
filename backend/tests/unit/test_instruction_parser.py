"""Unit tests for MockLLMAdapter natural-language parser."""
import pytest
from app.adapters.llm.mock_adapter import MockLLMAdapter, parse_time_token


@pytest.mark.asyncio
class TestMockLLMAdapter:
    @pytest.fixture
    def adapter(self):
        return MockLLMAdapter()

    @pytest.fixture
    def context(self, sample_transcript, sample_timeline):
        return {
            "transcript": sample_transcript,
            "timeline": sample_timeline,
            "duration_s": 300.0,
            "time_policy": "current",
            "existing_captions": [{"id": "c1", "text": "Welcome!"}]
        }

    async def test_parse_cut_first_30s(self, adapter, context):
        res = await adapter.parse_instruction("Cut the first 30 seconds", context)
        assert res["operation_type"] == "CUT"
        assert res["params"]["source_start_s"] == 0.0
        assert res["params"]["source_end_s"] == 30.0
        assert not res["needs_clarification"]
        assert not res["rejected"]

    async def test_parse_cut_range_dash(self, adapter, context):
        res = await adapter.parse_instruction("Remove 0:30-0:40", context)
        assert res["operation_type"] == "CUT"
        assert res["params"]["source_start_s"] == 30.0
        assert res["params"]["source_end_s"] == 40.0

    async def test_parse_speed_up(self, adapter, context):
        res = await adapter.parse_instruction("Speed up from 1:00 to 1:30 by 2x", context)
        assert res["operation_type"] == "SPEED"
        assert res["params"]["source_start_s"] == 60.0
        assert res["params"]["source_end_s"] == 90.0
        assert res["params"]["factor"] == 2.0

    async def test_parse_add_caption_when_say(self, adapter, context):
        res = await adapter.parse_instruction(
            "Add a caption 'Welcome!' when I say welcome to the channel",
            context
        )
        assert res["operation_type"] == "ADD_CAPTION"
        assert res["params"]["text"] == "Welcome!"
        assert res["params"]["source_start_s"] == 42.0

    async def test_parse_pricing_needs_clarification(self, adapter, context):
        res = await adapter.parse_instruction("Remove the part about pricing", context)
        assert res["needs_clarification"] is True
        assert res["question"] is not None
        assert len(res["options"]) >= 3

    async def test_parse_pricing_with_answer(self, adapter, context):
        ctx = dict(context, answer="the second one")
        res = await adapter.parse_instruction("Remove the part about pricing", ctx)
        assert res["needs_clarification"] is False
        assert res["operation_type"] == "CUT"
        assert res["params"]["source_start_s"] == 158.0

    async def test_parse_undo(self, adapter, context):
        res = await adapter.parse_instruction("Undo", context)
        assert res["operation_type"] == "UNDO"

    async def test_parse_redo(self, adapter, context):
        res = await adapter.parse_instruction("Redo", context)
        assert res["operation_type"] == "REDO"

    async def test_parse_render(self, adapter, context):
        res = await adapter.parse_instruction("Render", context)
        assert res["operation_type"] == "RENDER"

    async def test_parse_make_caption_red(self, adapter, context):
        res = await adapter.parse_instruction("Make that caption red", context)
        assert res["operation_type"] == "MODIFY_CAPTION"
        assert res["params"]["color"] == "red"

    async def test_parse_make_caption_with_no_captions_rejected(self, adapter, context):
        ctx = dict(context, existing_captions=[])
        res = await adapter.parse_instruction("Make that caption red", ctx)
        assert res["rejected"] is True

    async def test_parse_cut_everything_rejected(self, adapter, context):
        res = await adapter.parse_instruction("Cut everything", context)
        assert res["rejected"] is True
        assert "empty timeline" in res["reason"].lower()

    async def test_parse_time_tokens(self):
        assert parse_time_token("1:20") == 80.0
        assert parse_time_token("0:30") == 30.0
        assert parse_time_token("80s") == 80.0
        assert parse_time_token("80 seconds") == 80.0
        assert parse_time_token("a minute twenty") == 80.0
