"""
Adapter Anthropic (Claude) — implementa a LLMPort (RN-70/71).

Traduz a LlmRequest neutra para o dialeto da Anthropic (blocos `tool_use`,
`system` com `cache_control`) e volta. Marca o prefixo estável como cacheável
(RN-76) e reporta o uso de tokens (RN-79). Nenhum tipo da Anthropic vaza para
fora deste arquivo.
"""

from typing import Any

from agente.domain.llm import LlmRequest, Reply, TokenUsage, ToolCall
from agente.domain.tenant import LlmConfig

_MAX_TOKENS = 1024


class AnthropicLLM:
    def __init__(self, config: LlmConfig, client: Any | None = None) -> None:
        self._config = config
        if client is None:  # pragma: no cover - construção real, exercitada em prod
            import anthropic

            client = anthropic.AsyncAnthropic(api_key=config.api_key or None)
        self._client: Any = client

    async def respond(self, request: LlmRequest) -> Reply | ToolCall:
        system: Any = request.system_prompt
        if self._config.prompt_cache:
            # RN-76: prefixo estável cacheável.
            system = [
                {
                    "type": "text",
                    "text": request.system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ]

        tools = [
            {"name": t.name, "description": t.description, "input_schema": t.parameters}
            for t in request.tools
        ]
        messages = [{"role": m.role, "content": m.content} for m in request.messages]

        response = await self._client.messages.create(
            model=self._config.model,
            max_tokens=_MAX_TOKENS,
            system=system,
            tools=tools,
            messages=messages,
        )

        usage = self._usage(response)
        for block in response.content:
            if block.type == "tool_use":
                return ToolCall(name=block.name, args=dict(block.input), usage=usage)
        text = "".join(b.text for b in response.content if b.type == "text")
        return Reply(text=text, usage=usage)

    @staticmethod
    def _usage(response: Any) -> TokenUsage:
        u = getattr(response, "usage", None)
        if u is None:
            return TokenUsage()
        return TokenUsage(
            input_tokens=getattr(u, "input_tokens", 0) or 0,
            cached_input_tokens=getattr(u, "cache_read_input_tokens", 0) or 0,
            output_tokens=getattr(u, "output_tokens", 0) or 0,
        )
