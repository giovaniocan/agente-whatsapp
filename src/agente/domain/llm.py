"""
Tipos NEUTROS que cruzam a LLMPort (RN-71) — o ACL do cérebro.

O motor fala nestes tipos; cada adapter de LLM traduz de/para o dialeto do seu
provedor (tool_use da Anthropic, function_call da OpenAI, …). Nenhum formato de
provedor vaza para application/domain.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field


class ToolSpec(BaseModel):
    # Ferramenta oferecida ao LLM (parameters = JSON Schema puro).
    name: str
    description: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class LlmMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class LlmRequest(BaseModel):
    """
    O que entra na LLMPort. `system_prompt` + `tools` são o prefixo ESTÁVEL
    (cacheável, RN-76); `messages` é o dinâmico (resumo + últimas N + atual).
    """
    system_prompt: str
    messages: list[LlmMessage]
    tools: list[ToolSpec] = Field(default_factory=list)


class TokenUsage(BaseModel):
    # RN-79: budget de tokens por resposta (o adapter preenche do provedor).
    input_tokens: int = 0
    cached_input_tokens: int = 0
    output_tokens: int = 0


class ToolCall(BaseModel):
    # O LLM decidiu chamar uma ferramenta.
    name: str
    args: dict[str, Any] = Field(default_factory=dict)
    usage: TokenUsage | None = None


class Reply(BaseModel):
    # O LLM respondeu em texto (nenhuma ferramenta chamada).
    text: str
    usage: TokenUsage | None = None
