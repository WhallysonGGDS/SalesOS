"""Entrada validada da Fase 03 (ADR 0006).

Etapa, fechamento e cliente nunca vêm do formulário de oportunidade: só o serviço os define.
"""

from datetime import date
from typing import Any, Literal

from pydantic import Field, StrictInt, ValidationInfo, field_validator

from salesos.dinheiro import MAXIMO_CENTAVOS, centavos
from salesos.features.clientes.schemas import TEXTO_LONGO_MAX, Entrada, um_de
from salesos.features.oportunidades.models import ETAPAS, MOTIVOS_PERDA
from salesos.formularios import Mensagem
from salesos.periodo import data_do_formulario


class OportunidadeIn(Entrada):
    titulo: str = Field(min_length=1, max_length=200)
    valor_centavos: StrictInt | None = Field(default=None, ge=0, le=MAXIMO_CENTAVOS)
    previsao_fechamento: date | None = None
    observacoes: str | None = Field(default=None, max_length=TEXTO_LONGO_MAX)

    @field_validator("valor_centavos", mode="before")
    @classmethod
    def _valor(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        if not value.strip():
            return None
        try:
            return centavos(value)
        except ValueError:
            raise Mensagem("Use o formato 1.234,56") from None

    @field_validator("previsao_fechamento", mode="before")
    @classmethod
    def _previsao(cls, value: Any) -> Any:
        return data_do_formulario(value)


class MudancaEtapaIn(Entrada):
    etapa: str
    motivo_perda: str | None = Field(default=None, validate_default=True)
    motivo_detalhe: str | None = Field(default=None, max_length=500)

    @field_validator("etapa")
    @classmethod
    def _etapa(cls, value: str) -> str:
        return um_de(ETAPAS, value)

    @field_validator("motivo_perda")
    @classmethod
    def _motivo(cls, value: str | None, info: ValidationInfo) -> str | None:
        perdida = info.data.get("etapa") == "perdida"
        if perdida and value is None:
            raise Mensagem("Escolha o motivo da perda")
        if not perdida and value is not None:
            raise Mensagem("O motivo só vale para venda perdida")
        return None if value is None else um_de(MOTIVOS_PERDA, value)

    @field_validator("motivo_detalhe")
    @classmethod
    def _detalhe(cls, value: str | None, info: ValidationInfo) -> str | None:
        if value is not None and info.data.get("etapa") != "perdida":
            raise Mensagem("O detalhe só vale para venda perdida")
        return value


class FiltroFunil(Entrada):
    situacao: Literal["todas", "abertas", "ganhas", "perdidas"] = "todas"
    de: date | None = None
    ate: date | None = None

    @field_validator("de", "ate", mode="before")
    @classmethod
    def _datas(cls, value: Any) -> Any:
        return data_do_formulario(value)

    @field_validator("ate")
    @classmethod
    def _ordem(cls, value: date | None, info: ValidationInfo) -> date | None:
        de = info.data.get("de")
        if value is not None and de is not None and value < de:
            raise Mensagem("A data final é anterior à inicial")
        return value
