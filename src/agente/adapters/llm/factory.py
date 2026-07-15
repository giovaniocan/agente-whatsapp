"""
Fábrica de adapters de LLM (RN-70).

Lê `LlmConfig.type` e devolve o cérebro. Adicionar um provedor = registrar aqui
+ escrever o adapter cumprindo a LLMPort. O motor não muda.
"""

from agente.adapters.llm.anthropic_llm import AnthropicLLM
from agente.adapters.llm.openai_llm import OpenAICompatLLM
from agente.domain.ports import LLMPort
from agente.domain.tenant import LlmConfig


def build_llm(config: LlmConfig) -> LLMPort:
    if config.type == "anthropic":
        return AnthropicLLM(config)
    if config.type == "openai_compat":
        return OpenAICompatLLM(config)
    if config.type == "gemini":
        raise NotImplementedError(
            "adapter 'gemini' ainda não implementado — ver docs/plans/07-cerebro-llm.md"
        )
    raise ValueError(
        f"llm.type desconhecido: {config.type!r}. "
        "Válidos: 'anthropic', 'openai_compat'."
    )
