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

    # Optional partner keys, "label:key,label2:key2". The server stays public —
    # keys are never required and a wrong key is never rejected. A matching key
    # (Authorization: Bearer <key> or X-API-Key: <key>) only labels that
    # partner's traffic in the usage logs, for clients whose UI demands a key.
    partner_keys: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
