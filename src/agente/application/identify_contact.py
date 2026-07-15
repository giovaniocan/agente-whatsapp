"""
Use case: identificar o contato pelo telefone ou criar se for novo.

Padrão da camada de aplicação: 1 classe = 1 caso de uso; dependências (ports)
entram no construtor; a ação fica em `execute()`. Nada de I/O concreto aqui —
só a orquestração sobre a CRMPort.
"""

from agente.domain.crm import Contact
from agente.domain.ports import CRMPort


class IdentifyOrCreateContact:
    def __init__(self, crm: CRMPort) -> None:
        self._crm = crm

    async def execute(
        self, full_name: str, phone: str, email: str | None = None
    ) -> Contact:
        existing = await self._crm.find_contact_by_phone(phone)
        if existing is not None:
            return existing
        return await self._crm.create_contact(full_name, phone, email)
