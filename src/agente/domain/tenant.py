"""
Tenant = a "ficha de configuração" de um cliente (empresa) do agente.

Um único motor de IA atende vários clientes. Tudo o que muda de um cliente
para outro mora aqui: a persona, os serviços, a política de agenda e como
falar com o CRM dele. O domínio e a aplicação leem esta ficha; nunca
dependem de um cliente específico.
"""

from pydantic import BaseModel, Field, model_validator


class Persona(BaseModel):
    # Como o agente "soa" para este cliente (o cérebro usa isto no prompt).
    name: str                      # nome do assistente, ex.: "Ana, da AutoRevenda"
    tone: str                      # ex.: "cordial e objetivo"
    language: str = "pt-BR"


class Service(BaseModel):
    # Um serviço agendável. Na revenda: "Comprar veículo" / "Vender veículo".
    name: str
    intent: str                    # RN-02: aponta para uma intent declarada na ficha
    duration_minutes: int          # duração deste serviço (revenda: 60)
    capacity: int = 1              # RN-11: atendimentos simultâneos (salão manicure: 1)
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
    # Capacidade da LOJA em vez de por serviço: TODA ocupação conta contra a
    # capacidade, independente da intent (caso revenda; também cobre CRMs que
    # não registram qual serviço o agendamento é — ex.: Trivus).
    shared_capacity: bool = False
    working_hours: list[WorkingHours] = Field(default_factory=list)


class LlmConfig(BaseModel):
    """
    Cérebro do tenant (RN-70). `type` discrimina o provedor; o resto controla
    custo/economia de token (RN-74/75/76).
    """
    type: str = "anthropic"                    # "anthropic" | "openai_compat" | ...
    model: str = "claude-opus-4-8"
    summary_model: str = "claude-haiku-4-5"    # modelo barato p/ resumir (RN-75)
    recent_window: int = 10                    # últimas N mensagens verbatim (RN-74)
    prompt_cache: bool = True                  # cachear prefixo estável (RN-76)
    base_url: str = ""                         # openai_compat: Groq/Ollama/…
    api_key: str = ""                          # via env (RN-63)
    settings: dict[str, str] = Field(default_factory=dict)


class HandoffConfig(BaseModel):
    # Escalonamento para humano (RN-31).
    team_phone: str = ""                   # número interno do time (WhatsApp)
    auto_resume_hours: int = 4             # sem humano em X horas, a IA retoma
    message: str = "Vou te transferir para um atendente, um instante 🙂"


class FollowUpConfig(BaseModel):
    # Follow-up de lead frio (RN-51) — desligado por padrão.
    enabled: bool = False
    delay_hours: int = 4                   # sem resposta do cliente por X horas
    message: str = "Oi! Ainda posso te ajudar com o agendamento? 🙂"


class CRMConfig(BaseModel):
    """
    Como este tenant fala com o CRM dele. `type` é o DISCRIMINADOR: a fábrica
    de adaptadores lê "trivus" e devolve um TrivusCRM. Trocar de CRM no futuro
    é trocar este `type` — o resto do sistema não muda.
    """
    type: str                                          # "trivus" | "fake" | ...
    base_url: str = ""
    api_key: str = ""                                  # em produção vem de env, não do arquivo
    # config específica do adapter (ex.: store_id)
    settings: dict[str, str] = Field(default_factory=dict)


class ChannelConfig(BaseModel):
    """
    Canal de WhatsApp do tenant (RN-40b). `type` discrimina o gateway:
    "zapi" | "evolution". `settings` leva o específico (ex.: instance_id).
    """
    type: str = "zapi"
    base_url: str = "https://api.z-api.io"
    api_key: str = ""                                  # token da instância (via env)
    settings: dict[str, str] = Field(default_factory=dict)


class Tenant(BaseModel):
    # A ficha completa. Agrega tudo que varia por cliente.
    id: str
    name: str
    webhook_token: str = ""        # token que identifica o tenant no webhook (RN-40)
    # Piloto (plano 11.5): "shadow" = a IA só SUGERE (mensagem vai ao time,
    # nunca ao cliente); "autonomous" = produção de verdade.
    mode: str = "autonomous"
    persona: Persona
    intents: list[str]             # RN-02: vocabulário de intenções deste tenant
    services: list[Service]
    scheduling: SchedulingPolicy
    crm: CRMConfig
    channel: ChannelConfig = Field(default_factory=ChannelConfig)
    llm: LlmConfig = Field(default_factory=LlmConfig)
    handoff: HandoffConfig = Field(default_factory=HandoffConfig)
    follow_up: FollowUpConfig = Field(default_factory=FollowUpConfig)
    salespeople: list[Salesperson] = Field(default_factory=list)

    def service_for(self, intent: str) -> Service | None:
        # RN-11: o serviço (duração/capacidade) da intent, ou None se não houver.
        return next((s for s in self.services if s.intent == intent), None)

    @model_validator(mode="after")
    def _services_reference_declared_intents(self) -> "Tenant":
        # RN-02: nenhum serviço pode apontar para intent fora das declaradas.
        declared = set(self.intents)
        unknown = [s.intent for s in self.services if s.intent not in declared]
        if unknown:
            raise ValueError(
                f"serviços apontam para intents não declaradas: {sorted(set(unknown))}; "
                f"declaradas: {sorted(declared)}"
            )
        return self
