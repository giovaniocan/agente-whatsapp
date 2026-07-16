"""
Fábrica de adapters de CRM.

Lê `CRMConfig.type` e devolve a implementação certa da CRMPort. Adicionar um
CRM novo (clube_amore, pipedrive…) = registrar aqui + escrever o adapter.
O resto do sistema não muda (RN-03).
"""

from agente.adapters.crm.fake_crm import FakeCRM
from agente.adapters.crm.trivus import TrivusCRM
from agente.domain.ports import CRMPort
from agente.domain.tenant import CRMConfig


def build_crm(config: CRMConfig) -> CRMPort:
    if config.type == "fake":
        return FakeCRM()
    if config.type == "trivus":
        return TrivusCRM(config)
    raise ValueError(
        f"crm.type desconhecido: {config.type!r}. Tipos válidos: 'fake', 'trivus'."
    )
