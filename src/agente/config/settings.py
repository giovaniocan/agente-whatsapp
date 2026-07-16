from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    database_url: str = "postgresql+asyncpg://agente:agente@localhost:5439/agente"
    evolution_api_url: str = "http://localhost:8080"
    evolution_api_key: str = ""

    # produção (plano 11)
    tenants_dir: str = "src/agente/config/tenants"
    debounce_seconds: float = 6.0                  # RN-43
    webhook_rate_limit_per_minute: int = 120       # 11.3


settings = Settings()
