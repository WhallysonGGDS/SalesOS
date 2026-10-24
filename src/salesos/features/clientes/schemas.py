"""Entrada validada da Fase 02.

Sem `documento` nem telefone: CPF, CNPJ e telefone seguem bloqueados (D6, D11, D12).
`extra="forbid"` recusa esses e quaisquer campos internos.
"""

from datetime import UTC, datetime
from typing import Any

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

from salesos.features.clientes.models import ORIGENS, TIPOS_CLIENTE, TIPOS_INTERACAO
from salesos.features.clientes.normalize import normalize_email

TEXTO_LONGO_MAX = 5000


class _Entrada(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("*", mode="before")
    @classmethod
    def _vazio_vira_none(cls, value: Any) -> Any:
        return None if isinstance(value, str) and not value.strip() else value

    @field_validator("email", mode="after", check_fields=False)
    @classmethod
    def _normaliza_email(cls, value: str | None) -> str | None:
        return None if value is None else normalize_email(value)


def _um_de(valores: tuple[str, ...], value: str) -> str:
    if value not in valores:
        raise ValueError(f"valor fora de {valores}")
    return value


class ClienteIn(_Entrada):
    tipo: str
    nome: str = Field(min_length=1, max_length=200)
    nome_fantasia: str | None = Field(default=None, max_length=200)
    email: str | None = None
    origem: str
    observacoes: str | None = Field(default=None, max_length=TEXTO_LONGO_MAX)

    @field_validator("tipo")
    @classmethod
    def _tipo(cls, value: str) -> str:
        return _um_de(TIPOS_CLIENTE, value)

    @field_validator("origem")
    @classmethod
    def _origem(cls, value: str) -> str:
        return _um_de(ORIGENS, value)


class ContatoIn(_Entrada):
    nome: str = Field(min_length=1, max_length=200)
    cargo: str | None = Field(default=None, max_length=100)
    email: str | None = None


class InteracaoIn(_Entrada):
    tipo: str
    ocorrida_em: AwareDatetime
    resumo: str = Field(min_length=1, max_length=TEXTO_LONGO_MAX)
    contato_id: int | None = None

    @field_validator("tipo")
    @classmethod
    def _tipo(cls, value: str) -> str:
        # "sistema" é reservado aos eventos gerados pelo serviço (D4).
        return _um_de(tuple(t for t in TIPOS_INTERACAO if t != "sistema"), value)

    @field_validator("ocorrida_em")
    @classmethod
    def _utc(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)
