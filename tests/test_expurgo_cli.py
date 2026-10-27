"""Comando `salesos expurgar`: abrangência, confirmação explícita e trava (E5).

Banco temporário com dados fictícios; o servidor nunca sobe.
"""

import sqlite3
import sys
from pathlib import Path

import pytest

from salesos import main
from salesos.lock import caminho_trava
from tests.backup.test_lock import segurar_em_outro_processo
from tests.conftest import migrar

NOME = "Qwxexpurgosentinela"


@pytest.fixture
def db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    caminho = tmp_path / "dados" / "salesos.db"
    caminho.parent.mkdir()
    migrar(caminho)
    monkeypatch.setenv("SALESOS_DATABASE_URL", f"sqlite:///{caminho}")
    monkeypatch.setenv("SALESOS_BACKUP_DIR", str(tmp_path / "backups"))
    return caminho


def _cliente(db: Path, anonimizado_em: str | None) -> None:
    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO clientes (tipo, nome, origem, busca, anonimizado_em, archived_at) "
        "VALUES ('PJ', ?, 'site', 'x', ?, ?)",
        (NOME, anonimizado_em, anonimizado_em),
    )
    conn.commit()
    conn.close()


def _dump(db: Path) -> list[str]:
    conn = sqlite3.connect(db)
    try:
        return list(conn.iterdump())
    finally:
        conn.close()


def _rodar(monkeypatch: pytest.MonkeyPatch, resposta: str | None) -> None:
    def entrada(_texto: str) -> str:
        if resposta is None:
            raise EOFError
        return resposta

    monkeypatch.setattr("builtins.input", entrada)
    monkeypatch.setattr(sys, "argv", ["salesos", "expurgar"])
    main.run()


def test_nothing_in_scope_says_so_and_asks_nothing(
    db: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _cliente(db, None)
    _cliente(db, "2099-01-01 00:00:00.000000")  # anonimizado "no futuro": fora do prazo
    _rodar(monkeypatch, "não deveria ser pedido")
    assert "Nenhum cliente" in capsys.readouterr().out


@pytest.mark.parametrize("resposta", ["", "sim", "EXPURGAR 2", "expurgar 1", None])
def test_purge_needs_the_exact_confirmation(
    db: Path, monkeypatch: pytest.MonkeyPatch, resposta: str | None
) -> None:
    _cliente(db, "2000-01-01 00:00:00.000000")
    antes = _dump(db)
    with pytest.raises(SystemExit, match="Nada foi apagado"):
        _rodar(monkeypatch, resposta)
    assert _dump(db) == antes


def test_confirmed_purge_reports_numbers_without_names(
    db: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _cliente(db, "2000-01-01 00:00:00.000000")
    _cliente(db, None)
    _rodar(monkeypatch, "EXPURGAR 1")
    saida = capsys.readouterr().out
    assert "Cliente #1" in saida and "1 cliente(s)" in saida and "indicadores" in saida
    assert "tarefa_eventos" not in saida  # o relatório fala português, não nomes de tabela
    assert NOME not in saida
    conn = sqlite3.connect(db)
    try:
        assert conn.execute("SELECT id FROM clientes").fetchall() == [(2,)]
    finally:
        conn.close()


def test_purge_is_refused_while_another_process_uses_the_database(
    db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _cliente(db, "2000-01-01 00:00:00.000000")
    antes = _dump(db)
    proc = segurar_em_outro_processo(caminho_trava(db))
    try:
        with pytest.raises(SystemExit, match="Outro processo do SalesOS"):
            _rodar(monkeypatch, "EXPURGAR 1")
    finally:
        proc.kill()
        proc.wait()
    assert _dump(db) == antes


def test_missing_database_is_reported_without_creating_a_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ausente = tmp_path / "nao-existe" / "salesos.db"
    monkeypatch.setenv("SALESOS_DATABASE_URL", f"sqlite:///{ausente}")
    with pytest.raises(SystemExit, match="Banco não encontrado"):
        _rodar(monkeypatch, "EXPURGAR 1")
    assert not ausente.exists()


def test_unmigrated_database_gives_a_message_not_a_traceback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    vazio = tmp_path / "vazio.db"
    sqlite3.connect(vazio).close()
    monkeypatch.setenv("SALESOS_DATABASE_URL", f"sqlite:///{vazio}")
    with pytest.raises(SystemExit) as erro:
        _rodar(monkeypatch, "EXPURGAR 1")
    assert "OperationalError" in str(erro.value)


def test_purge_refuses_to_start_while_another_program_reads_the_database(
    db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Outro programa (DB Browser, por exemplo) impediria esvaziar o -wal depois do expurgo.
    _cliente(db, "2000-01-01 00:00:00.000000")
    antes = _dump(db)
    leitor = sqlite3.connect(db)
    try:
        leitor.execute("PRAGMA journal_mode=WAL")
        leitor.execute("BEGIN")
        leitor.execute("SELECT count(*) FROM clientes").fetchone()
        with pytest.raises(SystemExit, match="Nada foi apagado"):
            _rodar(monkeypatch, "EXPURGAR 1")
    finally:
        leitor.close()
    assert _dump(db) == antes


def test_purge_does_not_claim_physical_completion_when_the_wal_stays(
    db: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Um programa abre o banco depois da checagem inicial: os registros saem, mas o
    # conteúdo apagado pode continuar no -wal. O comando não diz "concluído".
    _cliente(db, "2000-01-01 00:00:00.000000")
    monkeypatch.setattr("salesos.expurgo.esvaziar_wal", lambda _s: False)  # depois do expurgo
    with pytest.raises(SystemExit, match="NÃO terminou") as erro:
        _rodar(monkeypatch, "EXPURGAR 1")
    saida = capsys.readouterr().out
    assert "Expurgo concluído" not in saida and NOME not in saida + str(erro.value)
    assert "rode `uv run salesos expurgar` de novo" in str(erro.value)


def test_running_again_confirms_the_wal_is_empty(
    db: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _rodar(monkeypatch, "não deveria ser pedido")
    assert "-wal está vazio" in capsys.readouterr().out


def test_other_sqlite_errors_keep_their_real_diagnosis(
    db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Só bloqueio vira "outro programa"; arquivo só de leitura ou erro de disco dizem o que é.
    from salesos.restore import RestauracaoRecusada

    def somente_leitura(_db: Path) -> None:
        raise RestauracaoRecusada(
            "Não foi possível usar o banco atual (SQLITE_READONLY: x). Nada foi alterado."
        )

    _cliente(db, "2000-01-01 00:00:00.000000")
    antes = _dump(db)
    monkeypatch.setattr("salesos.main.aquietar", somente_leitura)
    with pytest.raises(SystemExit) as erro:
        _rodar(monkeypatch, "EXPURGAR 1")
    assert "SQLITE_READONLY" in str(erro.value) and "Outro programa" not in str(erro.value)
    assert "Nada foi apagado" in str(erro.value)
    assert _dump(db) == antes
