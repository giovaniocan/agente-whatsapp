"""Tool specs neutros, escopados pela ficha do tenant (Plano 07.2)."""

from collections.abc import Callable

from agente.application.tools import FORBIDDEN_TOOLS, build_tool_specs
from agente.domain.tenant import Tenant


def _by_name(tenant: Tenant) -> dict[str, dict]:
    return {s.name: s.parameters for s in build_tool_specs(tenant)}


def test_intent_params_use_tenant_intents_as_enum(
    make_tenant: Callable[..., Tenant],
) -> None:
    # RN-02: o schema oferecido ao LLM só permite as intents da ficha.
    params = _by_name(make_tenant(intents=["haircut", "nails"]))
    assert params["schedule_appointment"]["properties"]["intent"]["enum"] == [
        "haircut",
        "nails",
    ]
    assert params["qualify_lead"]["properties"]["intent"]["enum"] == ["haircut", "nails"]


def test_priority_enum_is_the_lead_priorities(make_tenant: Callable[..., Tenant]) -> None:
    params = _by_name(make_tenant())
    assert params["qualify_lead"]["properties"]["priority"]["enum"] == [
        "high",
        "medium",
        "low",
    ]


def test_toolset_excludes_forbidden_actions(make_tenant: Callable[..., Tenant]) -> None:
    # RN-30: fronteira humana por design — o schema neutro nunca expõe estas.
    names = {s.name for s in build_tool_specs(make_tenant())}
    assert names.isdisjoint(FORBIDDEN_TOOLS)


def test_every_tool_has_a_json_schema_object(make_tenant: Callable[..., Tenant]) -> None:
    for spec in build_tool_specs(make_tenant()):
        assert spec.parameters["type"] == "object"
        assert "properties" in spec.parameters
