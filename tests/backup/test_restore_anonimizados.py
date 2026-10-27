"""Backup com cliente marcado como anonimizado que ainda tem dados pessoais é recusado.

O marcador `anonimizado_em` não basta: um backup editado à mão pode mantê-lo e devolver
e-mail, contatos, títulos ou textos. Bancos temporários com dados fictícios.
"""

import sqlite3
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from salesos.backup import criar_backup, sha256_arquivo
from salesos.db import create_db_engine
from salesos.features.clientes import service as clientes
from salesos.features.clientes.normalize import search_key
from salesos.features.clientes.schemas import ClienteIn, ContatoIn, InteracaoIn
from salesos.features.oportunidades import service as oportunidades
from salesos.features.oportunidades.schemas import MudancaEtapaIn, OportunidadeIn
from salesos.features.tarefas import service as tarefas
from salesos.migracao_backup import PREFIXO_TEMPORARIO, migrar_backup
from salesos.restore import RestauracaoRecusada, controle_pendente, restaurar
from tests.backup.conftest import criar_banco
from tests.conftest import migrar
from tests.tarefas.conftest import PRAZO, nova_tarefa

SENTINELA = "Qwxanonsentinela"


def _anonimizado_com_historico(db: Path) -> int:
    """Cliente que passou por todo tipo de evento antes de ser anonimizado, e um ativo."""
    engine = create_db_engine(f"sqlite:///{db}")
    try:
        with Session(engine) as s:
            novo = ClienteIn(tipo="PJ", nome="Fulano Ficticio", origem="site", email="f@x.invalid")
            cliente = clientes.criar_cliente(s, novo)
            clientes.atualizar_cliente(
                s, cliente.id, novo.model_copy(update={"nome": "Fulano F", "observacoes": "x"})
            )
            contato = clientes.adicionar_contato(s, cliente.id, ContatoIn(nome="Contato"))
            clientes.atualizar_contato(s, contato.id, ContatoIn(nome="Contato 2", cargo="c"))
            clientes.remover_contato(s, contato.id)
            interacao = InteracaoIn(tipo="nota", ocorrida_em=PRAZO, resumo="Conversa ficticia")
            clientes.registrar_interacao(s, cliente.id, interacao)
            clientes.arquivar_cliente(s, cliente.id)
            clientes.desarquivar_cliente(s, cliente.id)
            dados = OportunidadeIn(titulo="Projeto", valor_centavos=100, observacoes="obs")
            op = oportunidades.criar_oportunidade(s, cliente.id, dados)
            alterada = dados.model_copy(update={"titulo": "P2"})
            oportunidades.atualizar_oportunidade(s, op.id, alterada)
            oportunidades.mudar_etapa(s, op.id, MudancaEtapaIn(etapa="ganha"))
            oportunidades.mudar_etapa(s, op.id, MudancaEtapaIn(etapa="negociacao"))
            tarefa = nova_tarefa(s, cliente.id, descricao="Detalhe ficticio")
            tarefas.concluir_tarefa(s, tarefa.id)
            tarefas.reabrir_tarefa(s, tarefa.id)
            tarefas.cancelar_tarefa(s, tarefa.id)
            clientes.anonimizar_cliente(s, cliente.id)
            # Um cliente ativo continua com os dados: a regra vale só para anonimizados.
            ativo = ClienteIn(tipo="PF", nome="Ativo Ficticio", origem="site", email="a@x.invalid")
            clientes.criar_cliente(s, ativo)
            return cliente.id
    finally:
        engine.dispose()


def _restaurar_no_banco_atual(tmp_path: Path, backup: Path) -> tuple[Path, str]:
    db = criar_banco(tmp_path / "dados" / "salesos.db", "Atual")
    return db, sha256_arquivo(db)


def _sem_sobras(db: Path, pasta: Path) -> None:
    assert not list(db.parent.glob(f"{db.name}.staging-*"))
    assert not list(pasta.glob(f"{PREFIXO_TEMPORARIO}*"))
    assert not controle_pendente(db)


def test_legitimate_anonymized_client_with_full_history_is_restored(tmp_path: Path) -> None:
    origem = tmp_path / "origem.db"
    migrar(origem)
    _anonimizado_com_historico(origem)
    pasta = tmp_path / "backups"
    backup = criar_backup(origem, pasta)
    db, _ = _restaurar_no_banco_atual(tmp_path, backup)
    restaurar(db, backup, pasta)
    _sem_sobras(db, pasta)


# (descrição, SQL que devolve um dado pessoal mantendo `anonimizado_em`)
ADULTERACOES = {
    "email": "UPDATE clientes SET email = 'Qwxanonsentinela@x.invalid' WHERE id = :c",
    "nome_fantasia": "UPDATE clientes SET nome_fantasia = 'Qwxanonsentinela' WHERE id = :c",
    "documento": "UPDATE clientes SET documento = 'Qwxanonsentinela' WHERE id = :c",
    "observacoes": "UPDATE clientes SET observacoes = 'Qwxanonsentinela' WHERE id = :c",
    "nome": "UPDATE clientes SET nome = 'Qwxanonsentinela' WHERE id = :c",
    "busca": "UPDATE clientes SET busca = 'Qwxanonsentinela' WHERE id = :c",
    "contato": "INSERT INTO contatos (cliente_id, nome) VALUES (:c, 'Qwxanonsentinela')",
    "oportunidade_titulo": (
        "UPDATE oportunidades SET titulo = 'Qwxanonsentinela' WHERE cliente_id = :c"
    ),
    "oportunidade_observacoes": (
        "UPDATE oportunidades SET observacoes = 'Qwxanonsentinela' WHERE cliente_id = :c"
    ),
    "oportunidade_motivo_detalhe": (
        "UPDATE oportunidades SET motivo_detalhe = 'Qwxanonsentinela' WHERE cliente_id = :c"
    ),
    "tarefa_titulo": "UPDATE tarefas SET titulo = 'Qwxanonsentinela' WHERE cliente_id = :c",
    "tarefa_descricao": "UPDATE tarefas SET descricao = 'Qwxanonsentinela' WHERE cliente_id = :c",
    "interacao_resumo": (
        "UPDATE interacoes SET resumo = 'Qwxanonsentinela' WHERE cliente_id = :c AND tipo = 'nota'"
    ),
    "evento_texto_livre": (
        "INSERT INTO interacoes (cliente_id, tipo, ocorrida_em, resumo) "
        "VALUES (:c, 'sistema', '2026-01-01 00:00:00.000000', 'Qwxanonsentinela')"
    ),
    "evento_com_sufixo": (
        "INSERT INTO interacoes (cliente_id, tipo, ocorrida_em, resumo) "
        "VALUES (:c, 'sistema', '2026-01-01 00:00:00.000000', "
        "'Contato removido: Qwxanonsentinela')"
    ),
    # Um número de documento escondido no número do evento ou em dígitos de outro alfabeto.
    "evento_numero_alheio": (
        "INSERT INTO interacoes (cliente_id, tipo, ocorrida_em, resumo) "
        "VALUES (:c, 'sistema', '2026-01-01 00:00:00.000000', 'Oportunidade #12345678909 criada')"
    ),
    "evento_digitos_nao_ascii": (
        "INSERT INTO interacoes (cliente_id, tipo, ocorrida_em, resumo) "
        "VALUES (:c, 'sistema', '2026-01-01 00:00:00.000000', 'Tarefa #١٢٣ criada')"
    ),
    "evento_resumo_blob": (
        "INSERT INTO interacoes (cliente_id, tipo, ocorrida_em, resumo) "
        "VALUES (:c, 'sistema', '2026-01-01 00:00:00.000000', CAST('Cliente criado' AS BLOB))"
    ),
    # Colunas de data aceitam qualquer texto no SQLite.
    "cliente_data_numero": "UPDATE clientes SET updated_at = 12345678909 WHERE id = :c",
    "cliente_data_com_sufixo": (
        "UPDATE clientes SET updated_at = '2026-01-01 00:00:00 Qwxanonsentinela' WHERE id = :c"
    ),
    "cliente_data": "UPDATE clientes SET created_at = 'Qwxanonsentinela' WHERE id = :c",
    "interacao_data": (
        "UPDATE interacoes SET ocorrida_em = 'Qwxanonsentinela' WHERE cliente_id = :c"
    ),
    "oportunidade_previsao": (
        "UPDATE oportunidades SET previsao_fechamento = 'Qwxanonsentinela' WHERE cliente_id = :c"
    ),
    "movimentacao_data": (
        "UPDATE movimentacoes SET ocorrida_em = 'Qwxanonsentinela' WHERE oportunidade_id IN "
        "(SELECT id FROM oportunidades WHERE cliente_id = :c)"
    ),
    "tarefa_prazo": "UPDATE tarefas SET prazo = 'Qwxanonsentinela' WHERE cliente_id = :c",
    "tarefa_evento_data": (
        "UPDATE tarefa_eventos SET ocorrida_em = 'Qwxanonsentinela' WHERE tarefa_id IN "
        "(SELECT id FROM tarefas WHERE cliente_id = :c)"
    ),
    "evento_campo_inventado": (
        "INSERT INTO interacoes (cliente_id, tipo, ocorrida_em, resumo) "
        "VALUES (:c, 'sistema', '2026-01-01 00:00:00.000000', "
        "'Cliente atualizado: Qwxanonsentinela')"
    ),
}


def _adulterar(db: Path, sql: str, cliente_id: int) -> None:
    conn = sqlite3.connect(db)
    conn.execute(sql.replace(":c", str(cliente_id)))
    conn.commit()
    conn.close()


@pytest.mark.parametrize("sql", ADULTERACOES.values(), ids=ADULTERACOES.keys())
def test_anonymized_client_with_personal_data_is_refused(tmp_path: Path, sql: str) -> None:
    origem = tmp_path / "origem.db"
    migrar(origem)
    cliente_id = _anonimizado_com_historico(origem)
    _adulterar(origem, sql, cliente_id)
    pasta = tmp_path / "backups"
    backup = criar_backup(origem, pasta)  # manifesto e SHA-256 batem
    antes_backup = sha256_arquivo(backup)
    db, antes_db = _restaurar_no_banco_atual(tmp_path, backup)
    # Nem a opção de aceitar reintrodução libera: não é reintrodução, é inconsistência.
    with pytest.raises(RestauracaoRecusada, match="anonimizado") as erro:
        restaurar(db, backup, pasta, aceitar_reintroducao=True)
    assert SENTINELA not in str(erro.value)
    assert (sha256_arquivo(db), sha256_arquivo(backup)) == (antes_db, antes_backup)
    _sem_sobras(db, pasta)


def _antigo_anonimizado(db: Path, email: str | None) -> int:
    """Cliente anonimizado num banco da revisão 0002, como o código daquela época deixava."""
    migrar(db, "0002")
    nome = "Cliente anonimizado #1"
    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO clientes (id, tipo, nome, origem, busca, email, archived_at, anonimizado_em)"
        " VALUES (1, 'PJ', ?, 'site', ?, ?, '2025-01-01 00:00:00', '2025-01-01 00:00:00')",
        (nome, search_key(nome, None, None), email),
    )
    conn.execute(
        "INSERT INTO interacoes (cliente_id, tipo, ocorrida_em, resumo) VALUES "
        "(1, 'nota', '2024-12-01 00:00:00', '[conteúdo removido]'), "
        "(1, 'sistema', '2024-12-01 00:00:00', 'Cliente criado'), "
        "(1, 'sistema', '2025-01-01 00:00:00', 'Cliente anonimizado')"
    )
    conn.commit()
    conn.close()
    return 1


@pytest.mark.parametrize("email", [None, f"{SENTINELA}@x.invalid"], ids=["legitimo", "adulterado"])
def test_migrate_flow_checks_anonymized_clients_of_old_backups(
    tmp_path: Path, email: str | None
) -> None:
    antigo = tmp_path / "antigo.db"
    _antigo_anonimizado(antigo, email)
    pasta = tmp_path / "backups"
    backup = criar_backup(antigo, pasta)
    antes_backup = sha256_arquivo(backup)
    db, antes_db = _restaurar_no_banco_atual(tmp_path, backup)
    if email is None:
        restaurar(db, migrar_backup(backup, pasta), pasta)
    else:
        with pytest.raises(RestauracaoRecusada, match="anonimizado") as erro:
            restaurar(db, migrar_backup(backup, pasta), pasta)
        assert SENTINELA not in str(erro.value)
        assert sha256_arquivo(db) == antes_db
    assert sha256_arquivo(backup) == antes_backup
    _sem_sobras(db, pasta)
