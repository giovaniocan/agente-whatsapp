"""
Tipos NEUTROS que cruzam a LLMPort (RN-71) — o ACL do cérebro.

O motor fala nestes tipos; cada adapter de LLM traduz de/para o dialeto de
function calling do seu provedor (tool_use da Anthropic, function_call da
OpenAI, …). Nenhum formato de provedor vaza para application/domain.
"""

from typing import Any

from pydantic import BaseModel, Field


class ToolSpec(BaseModel):
    # Descrição de uma ferramenta oferecida ao LLM (parameters = JSON Schema).
    name: str
    description: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class ToolCall(BaseModel):
    # O LLM decidiu chamar uma ferramenta.
    name: str
    args: dict[str, Any] = Field(default_factory=dict)


class Reply(BaseModel):
    # O LLM respondeu em texto (nenhuma ferramenta chamada).
    text: str
