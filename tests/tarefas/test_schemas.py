"""Entrada validada da Fase 04: tipos, prioridades, prazo com hora e filtros da agenda."""

from datetime import UTC, date, datetime, timedelta, timezone
from typing import Any, get_args

import pytest
from pydantic import ValidationError

from salesos.features.tarefas.models import ESTADOS, PRIORIDADES, TIPOS_TAREFA
from salesos.features.tarefas.schemas import FiltroTarefas, TarefaIn
from salesos.formularios import erros

PRAZO = datetime(2026, 11, 3, 10, 0, tzinfo=timezone(timedelta(hours=-3)))


def _erros(modelo: type[Any], **dados: Any) -> dict[str, str]:
    with pytest.raises(ValidationError) as erro:
        modelo.model_validate(dados)
    return erros(erro.value)


def test_task_input_defaults_and_utc_deadline() -> None:
    tarefa = TarefaIn.model_validate(
        {"tipo": "ligacao", "titulo": " Ligar ", "prazo": PRAZO, "descricao": ""}
    )
    assert (tarefa.titulo, tarefa.prioridade, tarefa.descricao) == ("Ligar", "normal", None)
    assert tarefa.prazo == datetime(2026, 11, 3, 13, 0, tzinfo=UTC)
    assert tarefa.oportunidade_id is None


def test_deadline_is_kept_in_whole_seconds() -> None:
    # Python e SQLite comparam em segundos inteiros; frações fariam os dois discordarem.
    tarefa = TarefaIn.model_validate(
        {"tipo": "ligacao", "titulo": "X", "prazo": "2026-11-03T10:00:00.900000-03:00"}
    )
    assert tarefa.prazo == datetime(2026, 11, 3, 13, 0, tzinfo=UTC)


@pytest.mark.parametrize("tipo", ["ligacao", "reuniao", "mensagem", "retorno"])
@pytest.mark.parametrize("prioridade", ["baixa", "normal", "alta"])
def test_accepted_types_and_priorities(tipo: str, prioridade: str) -> None:
    TarefaIn.model_validate({"tipo": tipo, "titulo": "X", "prazo": PRAZO, "prioridade": prioridade})


@pytest.mark.parametrize(
    ("dados", "campo", "mensagem"),
    [
        ({"tipo": "email"}, "tipo", "Valor inválido"),
        ({"prioridade": "urgente"}, "prioridade", "Valor inválido"),
        ({"titulo": " "}, "titulo", "Preencha este campo"),
        ({"titulo": "x" * 201}, "titulo", "Máximo de 200 caracteres"),
        ({"descricao": "x" * 5001}, "descricao", "Máximo de 5000 caracteres"),
        ({"prazo": None}, "prazo", "Informe data e hora válidas"),
        ({"prazo": "amanhã"}, "prazo", "Informe data e hora válidas"),
        ({"prazo": datetime(2026, 11, 3, 10, 0)}, "prazo", "Informe data e hora válidas"),
        (
            {"prazo": datetime(1999, 12, 31, 10, 0, tzinfo=UTC)},
            "prazo",
            "Informe data e hora válidas",
        ),
        # O limite de anos vale para o valor gravado, em UTC.
        ({"prazo": "2000-01-01T00:30:00+03:00"}, "prazo", "Informe data e hora válidas"),
        ({"prazo": "2100-12-31T23:00:00-03:00"}, "prazo", "Informe data e hora válidas"),
        ({"prazo": "1700000000"}, "prazo", "Informe data e hora válidas"),
        ({"prazo": 1700000000}, "prazo", "Informe data e hora válidas"),
        ({"oportunidade_id": 0}, "oportunidade_id", "Valor inválido"),
        ({"oportunidade_id": 2**63}, "oportunidade_id", "Valor inválido"),
    ],
)
def test_task_input_errors_are_per_field(dados: dict[str, Any], campo: str, mensagem: str) -> None:
    base = {"tipo": "ligacao", "titulo": "Ligar", "prazo": PRAZO}
    assert _erros(TarefaIn, **(base | dados))[campo] == mensagem


def test_internal_fields_are_refused() -> None:
    for campo in ("estado", "concluida_em", "cancelada_em", "cliente_id"):
        with pytest.raises(ValidationError):
            TarefaIn.model_validate({"tipo": "ligacao", "titulo": "X", "prazo": PRAZO, campo: "x"})


def test_filter_defaults_to_pending_agenda() -> None:
    filtro = FiltroTarefas.model_validate({})
    assert (filtro.estado, filtro.prioridade, filtro.tipo, filtro.de, filtro.ate) == (
        "pendente",
        None,
        None,
        None,
        None,
    )
    cheio = FiltroTarefas.model_validate(
        {"estado": "todas", "prioridade": "alta", "tipo": "reuniao", "de": "2026-11-01", "ate": ""}
    )
    assert (cheio.estado, cheio.prioridade, cheio.tipo, cheio.de, cheio.ate) == (
        "todas",
        "alta",
        "reuniao",
        date(2026, 11, 1),
        None,
    )


@pytest.mark.parametrize(
    ("dados", "campo", "mensagem"),
    [
        ({"de": "2026-11-02", "ate": "2026-11-01"}, "ate", "A data final é anterior à inicial"),
        ({"de": "2026-02-30"}, "de", "Data inválida"),
        ({"ate": "03/11/2026"}, "ate", "Data inválida"),
        ({"estado": "atrasada"}, "estado", "Valor inválido"),
        ({"prioridade": "urgente"}, "prioridade", "Valor inválido"),
        ({"tipo": "email"}, "tipo", "Valor inválido"),
    ],
)
def test_filter_errors(dados: dict[str, str], campo: str, mensagem: str) -> None:
    assert _erros(FiltroTarefas, **dados)[campo] == mensagem


def test_filter_choices_match_the_model() -> None:
    # Os Literals do filtro repetem as listas do modelo; este teste mantém uma fonte de verdade.
    campos = FiltroTarefas.model_fields
    assert get_args(get_args(campos["tipo"].annotation)[0]) == TIPOS_TAREFA
    assert get_args(get_args(campos["prioridade"].annotation)[0]) == PRIORIDADES
    assert get_args(campos["estado"].annotation) == (*ESTADOS, "todas")
