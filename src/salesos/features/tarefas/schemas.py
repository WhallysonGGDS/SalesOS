"""Entrada validada da Fase 04 (ADR 0007).

Estado, datas de conclusão e cliente nunca vêm do formulário: só o serviço os define.
"""

from datetime import UTC, date, datetime
from typing import Any, Literal

from pydantic import AwareDatetime, Field, ValidationInfo, field_validator

from salesos.features.clientes.schemas import TEXTO_LONGO_MAX, Entrada, um_de
from salesos.features.tarefas.models import PRIORIDADES, TIPOS_TAREFA
from salesos.formularios import Mensagem
from salesos.periodo import data_do_formulario


class TarefaIn(Entrada):
    tipo: str
    titulo: str = Field(min_length=1, max_length=200)
    descricao: str | None = Field(default=None, max_length=TEXTO_LONGO_MAX)
    prioridade: str = "normal"
    prazo: AwareDatetime  # o router converte o datetime-local no fuso deste computador
    oportunidade_id: int | None = Field(default=None, ge=1, le=2**63 - 1)  # como o IdDep

    @field_validator("tipo")
    @classmethod
    def _tipo(cls, value: str) -> str:
        return um_de(TIPOS_TAREFA, value)

    @field_validator("prioridade")
    @classmethod
    def _prioridade(cls, value: str) -> str:
        return um_de(PRIORIDADES, value)

    @field_validator("prazo")
    @classmethod
    def _prazo(cls, value: datetime) -> datetime:
        # Segundos inteiros: o SQLite compara no formato de `datetime()`, sem frações.
        utc = value.astimezone(UTC).replace(microsecond=0)
        if not 2000 <= utc.year <= 2100:
            raise Mensagem("Informe data e hora válidas")
        return utc


class FiltroTarefas(Entrada):
    estado: Literal["pendente", "concluida", "cancelada", "todas"] = "pendente"
    prioridade: Literal["baixa", "normal", "alta"] | None = None
    tipo: Literal["ligacao", "reuniao", "mensagem", "retorno"] | None = None
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
