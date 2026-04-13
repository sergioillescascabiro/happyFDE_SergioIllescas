from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5433/happyrobot"
    AGENT_API_KEY: str = "hr-agent-key-change-in-production"
    DASHBOARD_TOKEN: str = "hr-dashboard-token-change-in-production"
    FMCSA_API_KEY: str = ""
    FMCSA_MOCK: bool = True
    APP_ENV: str = "development"

    class Config:
        env_file = ".env"

settings = Settings()
