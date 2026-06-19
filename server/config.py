"""Configuration for Sage MCP Public server."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Server settings loaded from environment variables."""

    # Supabase
    supabase_url: str = ""  # e.g., https://xxx.supabase.co
    supabase_service_key: str = ""  # service_role JWT

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
