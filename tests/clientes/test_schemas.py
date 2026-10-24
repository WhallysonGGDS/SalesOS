"""Validação de entrada da Fase 02 (dados fictícios)."""

from datetime import UTC, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from salesos.features.clientes.schemas import ClienteIn, ContatoIn, InteracaoIn

CLIENTE = {"tipo": "PJ", "nome": "Empresa Ficticia", "origem": "site"}


def test_cliente_normalizes_email_and_blank_optionals() -> None:
    dados = ClienteIn(**CLIENTE, email="  Vendas@Exemplo.COM ", nome_fantasia="  ", observacoes="")
    assert dados.email == "vendas@exemplo.com"
    assert dados.nome_fantasia is None
    assert dados.observacoes is None
    assert ClienteIn(**CLIENTE, email="").email is None


@pytest.mark.parametrize(
    "campo",
    [
        {"email": "sem-arroba"},
        {"origem": "tiktok"},
        {"tipo": "pf"},
        {"nome": "   "},
        {"nome": "x" * 201},
        {"observacoes": "x" * 5001},
    ],
)
def test_cliente_rejects_invalid_input(campo: dict[str, str]) -> None:
    with pytest.raises(ValidationError):
        ClienteIn(**{**CLIENTE, **campo})


@pytest.mark.parametrize("campo", ["documento", "telefone", "busca", "anonimizado_em"])
def test_blocked_and_internal_fields_are_refused(campo: str) -> None:
    """CPF, CNPJ e telefone seguem bloqueados (D6, D11, D12); campos internos não entram."""
    with pytest.raises(ValidationError):
        ClienteIn(**CLIENTE, **{campo: "1"})
    with pytest.raises(ValidationError):
        ContatoIn(nome="Pessoa Ficticia", **{campo: "1"})


def test_contato_normalizes_email_and_limits_cargo() -> None:
    assert ContatoIn(nome="Pessoa", email=" P@Exemplo.com").email == "p@exemplo.com"
    with pytest.raises(ValidationError):
        ContatoIn(nome="Pessoa", cargo="x" * 101)


def test_interacao_converts_to_utc_and_requires_timezone() -> None:
    brasilia = timezone(timedelta(hours=-3))
    dados = InteracaoIn(
        tipo="ligacao", ocorrida_em=datetime(2026, 10, 24, 10, 0, tzinfo=brasilia), resumo="ok"
    )
    assert dados.ocorrida_em == datetime(2026, 10, 24, 13, 0, tzinfo=UTC)
    assert dados.ocorrida_em.utcoffset() == timedelta(0)
    with pytest.raises(ValidationError):
        InteracaoIn(tipo="ligacao", ocorrida_em=datetime(2026, 10, 24, 10, 0), resumo="ok")


@pytest.mark.parametrize("tipo", ["sistema", "visita"])
def test_interacao_rejects_system_and_unknown_types(tipo: str) -> None:
    with pytest.raises(ValidationError):
        InteracaoIn(tipo=tipo, ocorrida_em=datetime.now(UTC), resumo="ok")
