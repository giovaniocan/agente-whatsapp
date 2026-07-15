"""System prompt renderizado da ficha + camada de segurança (Plano 07.3)."""

from collections.abc import Callable

from agente.application.prompt import build_system_prompt
from agente.domain.tenant import Service, Tenant


def test_prompt_is_rendered_from_tenant_config(make_tenant: Callable[..., Tenant]) -> None:
    prompt = build_system_prompt(make_tenant())
    assert "Bia" in prompt                       # persona da ficha
    assert "Corte" in prompt                      # serviço da ficha
    assert "acolhedor" in prompt                  # tom da ficha


def test_prompt_has_human_boundary_instruction(
    make_tenant: Callable[..., Tenant],
) -> None:
    # RN-30: instrução explícita de nunca negociar valores.
    prompt = build_system_prompt(make_tenant()).lower()
    assert "não" in prompt and ("valor" in prompt or "preço" in prompt or "desconto" in prompt)
    assert "atendente" in prompt or "humano" in prompt


def test_prompt_has_injection_defense(make_tenant: Callable[..., Tenant]) -> None:
    # RN-78: instruir a ignorar instruções embutidas na mensagem do usuário.
    prompt = build_system_prompt(make_tenant()).lower()
    assert "instruç" in prompt and "mensagem" in prompt


def test_prompt_is_agnostic_no_hardcoded_industry(
    make_tenant: Callable[..., Tenant],
) -> None:
    # RN-01: roda com salão e revenda sem termo de ramo fixo no template.
    revenda = make_tenant(
        id="revenda",
        intents=["buy_vehicle"],
        services=[Service(name="Comprar veículo", intent="buy_vehicle", duration_minutes=60)],
    )
    prompt = build_system_prompt(revenda)
    assert "Comprar veículo" in prompt            # vem da ficha, não do código
