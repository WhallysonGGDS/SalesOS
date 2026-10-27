"""Expurgo manual de clientes anonimizados há 12 meses (P1, E5). Dados fictícios.

Cobre: prazo, abrangência, ordem das chaves estrangeiras, transação única, repetição segura,
registros de outros clientes preservados e ausência de execução automática.
"""

import ast
import logging
import sqlite3
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, func, select, text
from sqlalchemy.orm import Session

from salesos import expurgo
from salesos.features.clientes import service as clientes
from salesos.features.clientes.models import Cliente, Contato, Interacao
from salesos.features.oportunidades.models import Movimentacao, Oportunidade
from salesos.features.tarefas import service as tarefas
from salesos.features.tarefas.models import Tarefa, TarefaEvento
from tests.backup.conftest import escutar
from tests.tarefas.conftest import nova_oportunidade, nova_tarefa, novo_cliente

AGORA = datetime(2027, 3, 1, 12, 0, tzinfo=UTC)
TABELAS = (Cliente, Contato, Interacao, Oportunidade, Movimentacao, Tarefa, TarefaEvento)


@pytest.fixture
def session(migrated_engine: Engine) -> Iterator[Session]:
    with Session(migrated_engine) as s:
        yield s


def _cliente_completo(session: Session, nome: str) -> int:
    """Cliente com oportunidade, histórico de etapa, tarefa com histórico e eventos."""
    cliente_id = novo_cliente(session, nome)
    oportunidade_id = nova_oportunidade(session, cliente_id)
    tarefa = nova_tarefa(session, cliente_id, oportunidade_id=oportunidade_id)
    tarefas.concluir_tarefa(session, tarefa.id)
    return cliente_id


def _anonimizado_em(session: Session, cliente_id: int, quando: datetime) -> None:
    clientes.anonimizar_cliente(session, cliente_id)
    session.execute(
        text("UPDATE clientes SET anonimizado_em = :q WHERE id = :i"),
        {"q": quando.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S.%f"), "i": cliente_id},
    )
    session.commit()


def _contagens(session: Session) -> dict[str, int]:
    return {
        t.__tablename__: session.scalar(select(func.count()).select_from(t)) or 0 for t in TABELAS
    }


def test_only_clients_anonymized_twelve_months_ago_are_in_scope(session: Session) -> None:
    no_limite = _cliente_completo(session, "No Limite Ficticio")
    _anonimizado_em(session, no_limite, datetime(2026, 3, 1, 12, 0, tzinfo=UTC))
    um_dia_antes = _cliente_completo(session, "Recente Ficticio")
    _anonimizado_em(session, um_dia_antes, datetime(2026, 3, 2, 12, 0, tzinfo=UTC))
    _cliente_completo(session, "Ativo Ficticio")  # nunca anonimizado
    escopo = expurgo.abrangencia(session, agora=AGORA)
    assert [a.cliente_id for a in escopo] == [no_limite]
    assert escopo[0].linhas == {
        "tarefa_eventos": 2,
        "tarefas": 1,
        "movimentacoes": 1,
        "oportunidades": 1,
        "interacoes": escopo[0].linhas["interacoes"],
        "contatos": 0,
        "clientes": 1,
    }
    assert escopo[0].linhas["interacoes"] >= 3  # eventos da linha do tempo do cliente


def test_twelve_months_counts_calendar_months_even_on_leap_day() -> None:
    assert expurgo.limite(datetime(2028, 2, 29, 9, 0, tzinfo=UTC)) == datetime(2027, 2, 28, 9, 0)
    assert expurgo.limite(AGORA) == datetime(2026, 3, 1, 12, 0)


def test_purge_removes_the_client_and_everything_linked_and_nothing_else(session: Session) -> None:
    alvo = _cliente_completo(session, "Alvo Ficticio")
    _anonimizado_em(session, alvo, datetime(2025, 1, 1, tzinfo=UTC))
    outro = _cliente_completo(session, "Outro Ficticio")
    recente = _cliente_completo(session, "Recente Ficticio")
    _anonimizado_em(session, recente, datetime(2026, 12, 1, tzinfo=UTC))
    session.execute(
        text("INSERT INTO contatos (cliente_id, nome) VALUES (:c, 'Contato')"), {"c": alvo}
    )
    session.commit()
    antes = _contagens(session)
    relatorio = expurgo.expurgar(session, [alvo], agora=AGORA)
    depois = _contagens(session)
    assert relatorio == {t: antes[t] - depois[t] for t in antes}
    assert relatorio["clientes"] == 1 and relatorio["contatos"] == 1
    assert session.get(Cliente, alvo) is None
    for tabela in (Interacao, Oportunidade, Tarefa, Contato):
        assert not session.scalars(select(tabela).where(tabela.cliente_id == alvo)).all()
    assert session.get(Cliente, outro) is not None and session.get(Cliente, recente) is not None
    assert len(tarefas.tarefas_do_cliente(session, outro)) == 1


def test_purging_again_is_a_safe_no_op(session: Session) -> None:
    alvo = _cliente_completo(session, "Alvo Ficticio")
    _anonimizado_em(session, alvo, datetime(2025, 1, 1, tzinfo=UTC))
    expurgo.expurgar(session, [alvo], agora=AGORA)
    antes = _contagens(session)
    assert expurgo.abrangencia(session, agora=AGORA) == []
    with pytest.raises(expurgo.ExpurgoRecusado, match="fora do escopo"):
        expurgo.expurgar(session, [alvo], agora=AGORA)
    assert _contagens(session) == antes


@pytest.mark.parametrize("motivo", ["nao-anonimizado", "recente"])
def test_clients_out_of_scope_are_refused_and_nothing_is_deleted(
    session: Session, motivo: str
) -> None:
    alvo = _cliente_completo(session, "Alvo Ficticio")
    _anonimizado_em(session, alvo, datetime(2025, 1, 1, tzinfo=UTC))
    fora = _cliente_completo(session, "Fora Ficticio")
    if motivo == "recente":
        _anonimizado_em(session, fora, datetime(2026, 12, 1, tzinfo=UTC))
    antes = _contagens(session)
    with pytest.raises(expurgo.ExpurgoRecusado, match="fora do escopo"):
        expurgo.expurgar(session, [alvo, fora], agora=AGORA)
    assert _contagens(session) == antes


def test_record_of_another_client_pointing_to_the_target_refuses_everything(
    session: Session,
) -> None:
    # D1 proíbe, mas o banco não impede: apagar exigiria mexer no registro de outro cliente.
    alvo = _cliente_completo(session, "Alvo Ficticio")
    outro = novo_cliente(session, "Outro Ficticio")
    oportunidade_do_alvo = session.scalars(
        select(Oportunidade.id).where(Oportunidade.cliente_id == alvo)
    ).one()
    session.execute(
        text("UPDATE tarefas SET oportunidade_id = :o WHERE id = :t"),
        {"o": oportunidade_do_alvo, "t": nova_tarefa(session, outro).id},
    )
    session.commit()
    _anonimizado_em(session, alvo, datetime(2025, 1, 1, tzinfo=UTC))
    antes = _contagens(session)
    with pytest.raises(expurgo.ExpurgoRecusado, match="outro cliente"):
        expurgo.expurgar(session, [alvo], agora=AGORA)
    assert _contagens(session) == antes


def test_failure_in_the_middle_rolls_back_everything(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    alvo = _cliente_completo(session, "Alvo Ficticio")
    _anonimizado_em(session, alvo, datetime(2025, 1, 1, tzinfo=UTC))
    antes = _contagens(session)
    original = session.execute
    chamadas: list[int] = []

    def falhar_na_quarta(*args: Any, **kwargs: Any) -> Any:
        chamadas.append(1)
        if len(chamadas) == 4:
            raise sqlite3.OperationalError("falha injetada")
        return original(*args, **kwargs)

    monkeypatch.setattr(session, "execute", falhar_na_quarta)
    with pytest.raises(sqlite3.OperationalError):
        expurgo.expurgar(session, [alvo], agora=AGORA)
    monkeypatch.undo()
    session.rollback()
    assert _contagens(session) == antes


def test_nothing_runs_the_purge_automatically() -> None:
    # Só o comando `salesos expurgar` chama `expurgar`; nenhuma rota, serviço ou inicialização.
    chamadores = []
    for arquivo in Path(expurgo.__file__).parent.rglob("*.py"):
        for no in ast.walk(ast.parse(arquivo.read_text(encoding="utf-8"))):
            if (
                isinstance(no, ast.Call)
                and getattr(no.func, "attr", getattr(no.func, "id", "")) == "expurgar"
            ):
                chamadores.append(arquivo.name)
    assert chamadores == ["main.py"]


def test_purge_warns_when_the_wal_could_not_be_emptied(
    session: Session, migrated_engine: Engine, caplog: pytest.LogCaptureFixture
) -> None:
    # Outro programa lendo o banco impede o checkpoint: os dados expurgados podem ficar no
    # `-wal` até o próximo checkpoint completo; o comando precisa avisar, não dizer só "ok".
    alvo = _cliente_completo(session, "Alvo Ficticio")
    _anonimizado_em(session, alvo, datetime(2025, 1, 1, tzinfo=UTC))
    escutar(caplog)
    leitor = sqlite3.connect(str(migrated_engine.url.database))
    try:
        leitor.execute("BEGIN")
        leitor.execute("SELECT count(*) FROM clientes").fetchone()  # segura uma leitura
        expurgo.expurgar(session, [alvo], agora=AGORA)
    finally:
        leitor.close()
    avisos = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert any("-wal" in a for a in avisos)
    assert not any("Alvo" in a for a in avisos)
