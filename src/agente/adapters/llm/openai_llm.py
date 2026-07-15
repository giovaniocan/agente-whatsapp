"""
Adapter OpenAI-compatible — implementa a LLMPort (RN-70/71/72).

Um adapter, muitos provedores: com `base_url` configurável cobre OpenAI, Groq,
DeepSeek e Ollama local sem código novo (RN-72). Traduz a LlmRequest neutra
para o formato `chat.completions` (system message + `function` tools) e volta.
"""

import json
from typing import Any

from agente.domain.llm import LlmRequest, Reply, TokenUsage, ToolCall
from agente.domain.tenant import LlmConfig

_MAX_TOKENS = 1024


class OpenAICompatLLM:
    def __init__(self, config: LlmConfig, client: Any | None = None) -> None:
        self._config = config
        if client is None:  # pragma: no cover - construção real, exercitada em prod
            import openai

            client = openai.AsyncOpenAI(
                api_key=config.api_key or None, base_url=config.base_url or None
            )
        self._client: Any = client

    async def respond(self, request: LlmRequest) -> Reply | ToolCall:
        messages: list[dict[str, str]] = [
            {"role": "system", "content": request.system_prompt}
        ]
        messages += [{"role": m.role, "content": m.content} for m in request.messages]

        tools = [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in request.tools
        ]

        response = await self._client.chat.completions.create(
            model=self._config.model,
            max_tokens=_MAX_TOKENS,
            messages=messages,
            tools=tools or None,
        )

        usage = self._usage(response)
        message = response.choices[0].message
        tool_calls = getattr(message, "tool_calls", None)
        if tool_calls:
            call = tool_calls[0]
            args = json.loads(call.function.arguments or "{}")
            return ToolCall(name=call.function.name, args=args, usage=usage)
        return Reply(text=message.content or "", usage=usage)

    @staticmethod
    def _usage(response: Any) -> TokenUsage:
        u = getattr(response, "usage", None)
        if u is None:
            return TokenUsage()
        details = getattr(u, "prompt_tokens_details", None)
        cached = getattr(details, "cached_tokens", 0) if details else 0
        return TokenUsage(
            input_tokens=getattr(u, "prompt_tokens", 0) or 0,
            cached_input_tokens=cached or 0,
            output_tokens=getattr(u, "completion_tokens", 0) or 0,
        )
