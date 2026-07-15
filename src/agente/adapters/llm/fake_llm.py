"""FakeLLM — LLMPort roteirizado para testes (devolve respostas na fila)."""

from agente.domain.llm import LlmRequest, Reply, ToolCall


class FakeLLM:
    def __init__(self, scripted: list[Reply | ToolCall]) -> None:
        self._queue: list[Reply | ToolCall] = list(scripted)
        self.calls = 0
        self.last_request: LlmRequest | None = None

    async def respond(self, request: LlmRequest) -> Reply | ToolCall:
        self.calls += 1
        self.last_request = request
        return self._queue.pop(0)
