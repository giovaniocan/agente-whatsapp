"""FakeLLM — LLMPort roteirizado para testes (devolve respostas na fila)."""

from agente.domain.conversation import Conversation
from agente.domain.llm import Reply, ToolCall, ToolSpec


class FakeLLM:
    def __init__(self, scripted: list[Reply | ToolCall]) -> None:
        self._queue: list[Reply | ToolCall] = list(scripted)
        self.calls = 0

    async def respond(
        self, conversation: Conversation, tools: list[ToolSpec]
    ) -> Reply | ToolCall:
        self.calls += 1
        return self._queue.pop(0)
