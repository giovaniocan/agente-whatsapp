from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    database_url: str = ""
    evolution_api_url: str = "http://localhost:8080"
    evolution_api_key: str = ""


settings = Settings()
