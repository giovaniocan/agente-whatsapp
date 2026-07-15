"""Adapter Anthropic — traduz tipos neutros ↔ dialeto Claude (Plano 07.4).
SDK mockada: sem chave, sem rede."""

from types import SimpleNamespace

from agente.adapters.llm.anthropic_llm import AnthropicLLM
from agente.domain.llm import LlmMessage, LlmRequest, Reply, ToolCall
from agente.domain.tenant import LlmConfig


class _Msgs:
    def __init__(self, resp: object) -> None:
        self._resp = resp
        self.last_kwargs: dict = {}

    async def create(self, **kwargs: object) -> object:
        self.last_kwargs = kwargs
        return self._resp


class _FakeClient:
    def __init__(self, resp: object) -> None:
        self.messages = _Msgs(resp)


def _usage() -> SimpleNamespace:
    return SimpleNamespace(input_tokens=100, cache_read_input_tokens=80, output_tokens=20)


def _req() -> LlmRequest:
    return LlmRequest(
        system_prompt="Você é a Bia.",
        messages=[LlmMessage(role="user", content="quero agendar")],
        tools=[],
    )


async def test_text_response_becomes_reply() -> None:
    resp = SimpleNamespace(
        content=[SimpleNamespace(type="text", text="Olá! Como ajudo?")], usage=_usage()
    )
    llm = AnthropicLLM(LlmConfig(type="anthropic"), client=_FakeClient(resp))

    result = await llm.respond(_req())

    assert isinstance(result, Reply)
    assert result.text == "Olá! Como ajudo?"
    assert result.usage is not None and result.usage.cached_input_tokens == 80


async def test_tool_use_response_becomes_tool_call() -> None:
    resp = SimpleNamespace(
        content=[
            SimpleNamespace(
                type="tool_use", name="schedule_appointment", input={"start": "2026-07-20T11:00"}
            )
        ],
        usage=_usage(),
    )
    llm = AnthropicLLM(LlmConfig(type="anthropic"), client=_FakeClient(resp))

    result = await llm.respond(_req())

    assert isinstance(result, ToolCall)
    assert result.name == "schedule_appointment"
    assert result.args == {"start": "2026-07-20T11:00"}


async def test_prompt_cache_marks_stable_prefix() -> None:
    # RN-76: com prompt_cache, o system vai com cache_control.
    resp = SimpleNamespace(content=[SimpleNamespace(type="text", text="oi")], usage=_usage())
    client = _FakeClient(resp)
    llm = AnthropicLLM(LlmConfig(type="anthropic", prompt_cache=True), client=client)

    await llm.respond(_req())

    system = client.messages.last_kwargs["system"]
    assert isinstance(system, list)
    assert system[0]["cache_control"] == {"type": "ephemeral"}
