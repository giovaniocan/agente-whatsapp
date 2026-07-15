"""Adapter OpenAI-compatible (GPT/Groq/Ollama) — LLMPort (Plano 07.5).
SDK mockada: sem chave, sem rede."""

import json
from types import SimpleNamespace

from agente.adapters.llm.openai_llm import OpenAICompatLLM
from agente.domain.llm import LlmMessage, LlmRequest, Reply, ToolCall
from agente.domain.tenant import LlmConfig


class _Completions:
    def __init__(self, resp: object) -> None:
        self._resp = resp
        self.last_kwargs: dict = {}

    async def create(self, **kwargs: object) -> object:
        self.last_kwargs = kwargs
        return self._resp


class _FakeClient:
    def __init__(self, resp: object) -> None:
        self.chat = SimpleNamespace(completions=_Completions(resp))


def _usage() -> SimpleNamespace:
    return SimpleNamespace(
        prompt_tokens=100,
        completion_tokens=20,
        prompt_tokens_details=SimpleNamespace(cached_tokens=80),
    )


def _resp(message: SimpleNamespace) -> SimpleNamespace:
    return SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=_usage())


def _req() -> LlmRequest:
    return LlmRequest(
        system_prompt="Você é a Bia.",
        messages=[LlmMessage(role="user", content="quero agendar")],
    )


async def test_text_response_becomes_reply() -> None:
    msg = SimpleNamespace(content="Olá! Como ajudo?", tool_calls=None)
    llm = OpenAICompatLLM(LlmConfig(type="openai_compat"), client=_FakeClient(_resp(msg)))

    result = await llm.respond(_req())

    assert isinstance(result, Reply)
    assert result.text == "Olá! Como ajudo?"
    assert result.usage is not None and result.usage.cached_input_tokens == 80


async def test_tool_call_response_becomes_tool_call() -> None:
    tool_call = SimpleNamespace(
        function=SimpleNamespace(
            name="schedule_appointment",
            arguments=json.dumps({"start": "2026-07-20T11:00"}),
        )
    )
    msg = SimpleNamespace(content=None, tool_calls=[tool_call])
    llm = OpenAICompatLLM(LlmConfig(type="openai_compat"), client=_FakeClient(_resp(msg)))

    result = await llm.respond(_req())

    assert isinstance(result, ToolCall)
    assert result.name == "schedule_appointment"
    assert result.args == {"start": "2026-07-20T11:00"}


async def test_system_prompt_is_first_message() -> None:
    msg = SimpleNamespace(content="oi", tool_calls=None)
    client = _FakeClient(_resp(msg))
    llm = OpenAICompatLLM(LlmConfig(type="openai_compat"), client=client)

    await llm.respond(_req())

    sent = client.chat.completions.last_kwargs["messages"]
    assert sent[0] == {"role": "system", "content": "Você é a Bia."}
