"""Entrada validada da Fase 03: valores pt-BR, datas estritas e regras de motivo."""

from datetime import date
from typing import Any

import pytest
from pydantic import ValidationError

from salesos.features.oportunidades.schemas import FiltroFunil, MudancaEtapaIn, OportunidadeIn
from salesos.formularios import erros


def _campos_com_erro(modelo: type[Any], **dados: Any) -> dict[str, str]:
    with pytest.raises(ValidationError) as erro:
        modelo.model_validate(dados)
    return erros(erro.value)


def test_opportunity_input_converts_money_and_empty_fields() -> None:
    entrada = OportunidadeIn.model_validate(
        {
            "titulo": " Projeto ",
            "valor_centavos": "1.234,56",
            "previsao_fechamento": "2026-12-01",
            "observacoes": "",
        }
    )
    assert entrada.titulo == "Projeto"
    assert entrada.valor_centavos == 123456
    assert entrada.previsao_fechamento == date(2026, 12, 1)
    assert entrada.observacoes is None
    assert (
        OportunidadeIn.model_validate({"titulo": "X", "valor_centavos": ""}).valor_centavos is None
    )


@pytest.mark.parametrize(
    ("dados", "campo", "mensagem"),
    [
        ({"titulo": ""}, "titulo", "Preencha este campo"),
        ({"titulo": "x" * 201}, "titulo", "Máximo de 200 caracteres"),
        ({"titulo": "X", "valor_centavos": "1,234.56"}, "valor_centavos", "Use o formato 1.234,56"),
        ({"titulo": "X", "valor_centavos": "-5"}, "valor_centavos", "Use o formato 1.234,56"),
        (
            {"titulo": "X", "previsao_fechamento": "25/10/2026"},
            "previsao_fechamento",
            "Data inválida",
        ),
        (
            {"titulo": "X", "previsao_fechamento": "2026-02-30"},
            "previsao_fechamento",
            "Data inválida",
        ),
        (
            {"titulo": "X", "previsao_fechamento": "1700000000"},
            "previsao_fechamento",
            "Data inválida",
        ),
        ({"titulo": "X", "observacoes": "x" * 5001}, "observacoes", "Máximo de 5000 caracteres"),
    ],
)
def test_opportunity_input_errors_are_per_field(
    dados: dict[str, str], campo: str, mensagem: str
) -> None:
    assert _campos_com_erro(OportunidadeIn, **dados)[campo] == mensagem


def test_opportunity_input_refuses_internal_fields() -> None:
    for campo in ("etapa", "fechada_em", "motivo_perda", "cliente_id"):
        with pytest.raises(ValidationError):
            OportunidadeIn.model_validate({"titulo": "X", campo: "ganha"})


def test_stage_change_requires_reason_only_when_lost() -> None:
    perda = MudancaEtapaIn.model_validate(
        {"etapa": "perdida", "motivo_perda": "preco", "motivo_detalhe": " caro "}
    )
    assert (perda.motivo_perda, perda.motivo_detalhe) == ("preco", "caro")
    assert MudancaEtapaIn.model_validate({"etapa": "negociacao"}).motivo_perda is None
    erros_perda = _campos_com_erro(MudancaEtapaIn, etapa="perdida")
    assert erros_perda["motivo_perda"] == "Escolha o motivo da perda"
    erros_motivo = _campos_com_erro(MudancaEtapaIn, etapa="negociacao", motivo_perda="preco")
    assert erros_motivo["motivo_perda"] == "O motivo só vale para venda perdida"
    assert "motivo_perda" in _campos_com_erro(MudancaEtapaIn, etapa="perdida", motivo_perda="caro")
    assert "etapa" in _campos_com_erro(MudancaEtapaIn, etapa="contrato")
    assert "etapa" in _campos_com_erro(MudancaEtapaIn)
    detalhe = _campos_com_erro(
        MudancaEtapaIn, etapa="perdida", motivo_perda="outro", motivo_detalhe="x" * 501
    )
    assert detalhe["motivo_detalhe"] == "Máximo de 500 caracteres"


def test_filter_defaults_and_valid_values() -> None:
    assert FiltroFunil.model_validate({}) == FiltroFunil(situacao="todas", de=None, ate=None)
    filtro = FiltroFunil.model_validate({"situacao": "ganhas", "de": "2026-10-01", "ate": ""})
    assert (filtro.situacao, filtro.de, filtro.ate) == ("ganhas", date(2026, 10, 1), None)


@pytest.mark.parametrize(
    ("dados", "campo", "mensagem"),
    [
        ({"de": "2026-10-02", "ate": "2026-10-01"}, "ate", "A data final é anterior à inicial"),
        ({"de": "2026-13-01"}, "de", "Data inválida"),
        ({"ate": "ontem"}, "ate", "Data inválida"),
        ({"de": "1999-12-31"}, "de", "Data inválida"),
        ({"ate": "2101-01-01"}, "ate", "Data inválida"),
        ({"situacao": "contratos"}, "situacao", "Valor inválido"),
    ],
)
def test_filter_errors(dados: dict[str, str], campo: str, mensagem: str) -> None:
    assert _campos_com_erro(FiltroFunil, **dados)[campo] == mensagem


@pytest.mark.parametrize("valor", [-5, 10**12 + 1, True, 1.5])
def test_programmatic_value_outside_rules_is_refused(valor: object) -> None:
    """Sem isso, o CHECK do banco viraria erro 500 em vez de erro de validação."""
    assert "valor_centavos" in _campos_com_erro(OportunidadeIn, titulo="X", valor_centavos=valor)
