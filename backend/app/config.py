from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = (
        "postgresql+asyncpg://temujanji:temujanji@localhost:5432/temujanji"
    )
    timezone: str = "Asia/Dubai"
    agent_api_key: str = "dev-agent-key"
    jwt_secret: str = "dev-jwt-secret-change-me"
    jwt_access_token_expire_minutes: int = 480
    qr_signing_secret: str = "dev-qr-secret"
    admin_bootstrap_password: str = "admin123"
    antrian_base_url: str = "http://localhost:8001/api"
    antrian_api_key: str = "dev-antrian-key"
    public_web_base: str = "http://localhost:3000"
    cors_origins: str = "http://localhost:3000"


settings = Settings()
