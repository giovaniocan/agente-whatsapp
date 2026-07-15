"""Fábrica de LLM (RN-70) + suíte de CONTRATO compartilhada (Plano 07.6).

O contrato roda a MESMA bateria contra Claude e GPT com SDK mockada: prova que
trocar de provedor não muda o comportamento observável (a agnosticidade)."""

import json
from types import SimpleNamespace

import pytest

from agente.adapters.llm.anthropic_llm import AnthropicLLM
from agente.adapters.llm.factory import build_llm
from agente.adapters.llm.openai_llm import OpenAICompatLLM
from agente.domain.llm import LlmMessage, LlmRequest, Reply, ToolCall
from agente.domain.tenant import LlmConfig

# --- Fábrica ---


def test_anthropic_type_returns_anthropic_adapter() -> None:
    assert isinstance(build_llm(LlmConfig(type="anthropic", api_key="x")), AnthropicLLM)


def test_openai_compat_type_returns_openai_adapter() -> None:
    assert isinstance(
        build_llm(LlmConfig(type="openai_compat", api_key="x")), OpenAICompatLLM
    )


def test_gemini_is_not_implemented_yet() -> None:
    with pytest.raises(NotImplementedError, match="07"):
        build_llm(LlmConfig(type="gemini"))


def test_unknown_type_raises_value_error() -> None:
    with pytest.raises(ValueError, match="anthropic"):
        build_llm(LlmConfig(type="llama_local"))


# --- Contrato compartilhado (parametrizado sobre os dois provedores) ---


def _anthropic_with(resp: SimpleNamespace) -> AnthropicLLM:
    client = SimpleNamespace(
        messages=SimpleNamespace(create=_async_return(resp))
    )
    return AnthropicLLM(LlmConfig(type="anthropic"), client=client)


def _openai_with(resp: SimpleNamespace) -> OpenAICompatLLM:
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=_async_return(resp)))
    )
    return OpenAICompatLLM(LlmConfig(type="openai_compat"), client=client)


def _async_return(value: object):  # type: ignore[no-untyped-def]
    async def _create(**_: object) -> object:
        return value

    return _create


_ANTHROPIC_TEXT = SimpleNamespace(content=[SimpleNamespace(type="text", text="oi!")], usage=None)
_ANTHROPIC_TOOL = SimpleNamespace(
    content=[SimpleNamespace(type="tool_use", name="qualify_lead", input={"priority": "high"})],
    usage=None,
)
_OPENAI_TEXT = SimpleNamespace(
    choices=[SimpleNamespace(message=SimpleNamespace(content="oi!", tool_calls=None))], usage=None
)
_OPENAI_TOOL = SimpleNamespace(
    choices=[
        SimpleNamespace(
            message=SimpleNamespace(
                content=None,
                tool_calls=[
                    SimpleNamespace(
                        function=SimpleNamespace(
                            name="qualify_lead", arguments=json.dumps({"priority": "high"})
                        )
                    )
                ],
            )
        )
    ],
    usage=None,
)


def _req() -> LlmRequest:
    return LlmRequest(system_prompt="s", messages=[LlmMessage(role="user", content="oi")])


@pytest.mark.parametrize(
    ("llm", "expected_text"),
    [(_anthropic_with(_ANTHROPIC_TEXT), "oi!"), (_openai_with(_OPENAI_TEXT), "oi!")],
)
async def test_contract_text_reply(llm: object, expected_text: str) -> None:
    result = await llm.respond(_req())  # type: ignore[attr-defined]
    assert isinstance(result, Reply)
    assert result.text == expected_text


@pytest.mark.parametrize(
    "llm", [_anthropic_with(_ANTHROPIC_TOOL), _openai_with(_OPENAI_TOOL)]
)
async def test_contract_tool_call(llm: object) -> None:
    result = await llm.respond(_req())  # type: ignore[attr-defined]
    assert isinstance(result, ToolCall)
    assert result.name == "qualify_lead"
    assert result.args == {"priority": "high"}
