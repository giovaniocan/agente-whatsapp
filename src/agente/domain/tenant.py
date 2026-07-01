"""
Tenant = a "ficha de configuração" de um cliente (empresa) do agente.

Um único motor de IA atende vários clientes. Tudo o que muda de um cliente
para outro mora aqui: a persona, os serviços, a política de agenda e como
falar com o CRM dele. O domínio e a aplicação leem esta ficha; nunca
dependem de um cliente específico.
"""

from pydantic import BaseModel, Field


class Persona(BaseModel):
    # Como o agente "soa" para este cliente (o cérebro usa isto no prompt).
    name: str                      # nome do assistente, ex.: "Ana, da AutoRevenda"
    tone: str                      # ex.: "cordial e objetivo"
    language: str = "pt-BR"


class Service(BaseModel):
    # Um serviço agendável. Na revenda: "Comprar veículo" / "Vender veículo".
    name: str
    duration_minutes: int          # atendimento dura 60 min neste cliente
    requires_salesperson: bool = True


class Salesperson(BaseModel):
    id: str
    name: str
    specialties: list[str] = Field(default_factory=list)


class WorkingHours(BaseModel):
    # Uma janela de atendimento em um dia da semana.
    # weekday segue o padrão do Python: 0 = segunda ... 6 = domingo.
    weekday: int
    open: str                      # "09:00"
    close: str                     # "18:00"


class SchedulingPolicy(BaseModel):
    """
    Regras de agenda do cliente. É com isto que o agente CALCULA os horários
    livres — o Trivus não tem esse conceito, então a inteligência vive aqui.
    """
    timezone: str = "America/Sao_Paulo"   # fuso da loja (evita o bug do "local naïve")
    slot_minutes: int = 60                # tamanho de cada horário
    capacity_per_slot: int = 1            # atendimentos simultâneos (revenda: 2 a 3)
    min_notice_minutes: int = 0           # antecedência mínima (revenda: 0)
    working_hours: list[WorkingHours] = Field(default_factory=list)


class CRMConfig(BaseModel):
    """
    Como este tenant fala com o CRM dele. `type` é o DISCRIMINADOR: a fábrica
    de adaptadores lê "trivus" e devolve um TrivusCRM. Trocar de CRM no futuro
    é trocar este `type` — o resto do sistema não muda.
    """
    type: str                                          # "trivus" | "fake" | ...
    base_url: str = ""
    api_key: str = ""                                  # em produção vem de env, não do arquivo
    settings: dict[str, str] = Field(default_factory=dict)  # config específica do adapter (ex.: store_id)


class Tenant(BaseModel):
    # A ficha completa. Agrega tudo que varia por cliente.
    id: str
    name: str
    persona: Persona
    services: list[Service]
    scheduling: SchedulingPolicy
    crm: CRMConfig
    salespeople: list[Salesperson] = Field(default_factory=list)
