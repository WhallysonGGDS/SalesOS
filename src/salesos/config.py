import secrets

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LOOPBACK_HOSTS = ("127.0.0.1", "::1", "localhost")
# Valores aceitos no header Host (proteção contra DNS rebinding). Fixo de propósito: não é
# configurável, para que nenhum .env consiga desligar a proteção.
ALLOWED_HOSTS = ["127.0.0.1", "localhost", "[::1]"]


class Settings(BaseSettings):
    """Configuração lida do ambiente (prefixo SALESOS_) e do arquivo .env."""

    # env_ignore_empty: uma linha "SALESOS_SECRET_KEY=" vazia usa o padrão, nunca uma chave vazia.
    model_config = SettingsConfigDict(
        env_prefix="SALESOS_", env_file=".env", extra="ignore", env_ignore_empty=True
    )

    host: str = "127.0.0.1"
    port: int = 8000
    database_url: str = "sqlite:///data/salesos.db"
    # Sem valor configurado, cada execução gera um segredo novo: os formulários
    # abertos antes de reiniciar o servidor deixam de valer, o que é aceitável localmente.
    secret_key: SecretStr = Field(default_factory=lambda: SecretStr(secrets.token_urlsafe(32)))

    @field_validator("host")
    @classmethod
    def _only_loopback(cls, value: str) -> str:
        if value not in LOOPBACK_HOSTS:
            raise ValueError(f"o SalesOS só escuta em loopback ({', '.join(LOOPBACK_HOSTS)})")
        return value

    @field_validator("secret_key")
    @classmethod
    def _strong_secret(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < 32:
            raise ValueError("SALESOS_SECRET_KEY precisa ter pelo menos 32 caracteres")
        return value
