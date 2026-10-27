"""Confere, num backup, que todo cliente marcado como anonimizado está de fato limpo.

O marcador `anonimizado_em` não basta: um backup editado à mão pode mantê-lo e devolver
e-mail, contatos, títulos ou textos. O estado esperado é o que `anonimizar_cliente` deixa
(ADR 0005 e `docs/privacy.md`). Só clientes anonimizados são conferidos: os ativos têm dados
pessoais por definição. Roda na cópia privada da restauração, só leitura.
"""

import re
import sqlite3
from pathlib import Path

from sqlalchemy import Date, DateTime

from salesos.backup import BackupInvalido, abrir_leitura
from salesos.db import Base
from salesos.features.clientes.normalize import search_key
from salesos.features.clientes.service import CONTEUDO_REMOVIDO
from salesos.features.oportunidades.service import ROTULOS_ETAPAS
from salesos.features.tarefas.service import ACAO_NO_EVENTO

# Como cada tabela chega ao cliente. Tabelas e colunas vêm só deste módulo, nunca do backup.
_DONO = {
    "clientes": "x.id",
    "contatos": "x.cliente_id",
    "oportunidades": "x.cliente_id",
    "interacoes": "x.cliente_id",
    "tarefas": "x.cliente_id",
    "movimentacoes": "(SELECT cliente_id FROM oportunidades WHERE id = x.oportunidade_id)",
    "tarefa_eventos": "(SELECT cliente_id FROM tarefas WHERE id = x.tarefa_id)",
}
# Datas como o SQLAlchemy grava no SQLite; o SQLite aceitaria qualquer texto nessas colunas.
_DATA = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}(?: [0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?)?"
    r"(?:[+-][0-9]{2}:[0-9]{2})?",
    re.ASCII,
)
# Número no começo de um evento de oportunidade ou tarefa: precisa ser um registro do cliente.
_REFERENCIA = re.compile(r"(Oportunidade|Tarefa) #([0-9]+) ", re.ASCII)


def _linhas(conn: sqlite3.Connection, tabela: str, colunas: str) -> sqlite3.Cursor:
    """Linhas da tabela que pertencem a clientes anonimizados, com o id do cliente primeiro."""
    dono = _DONO[tabela]
    return conn.execute(
        f"SELECT {dono}, {colunas} FROM {tabela} AS x WHERE {dono} IN "  # noqa: S608 (texto fixo)
        "(SELECT id FROM clientes WHERE anonimizado_em IS NOT NULL)"
    )


def _data_valida(valor: object) -> bool:
    return valor is None or (isinstance(valor, str) and _DATA.fullmatch(valor) is not None)


def _lista(tabela: str) -> str:
    """Nomes de campos de um evento "atualizado": só nomes de colunas, nunca valores."""
    campos = "|".join(sorted(Base.metadata.tables[tabela].columns.keys()))
    return f"(?:{campos})(?:, (?:{campos}))*"


def _eventos() -> re.Pattern[str]:
    """Todo texto que o SalesOS grava como evento (sem dados pessoais), e só ele."""
    etapas = "|".join(re.escape(r) for r in ROTULOS_ETAPAS.values())
    acoes_tarefa = "|".join(re.escape(a) for a in ACAO_NO_EVENTO.values())
    formas = [
        "Cliente (?:criado|arquivado|desarquivado|anonimizado)",
        "Contato (?:adicionado|removido)",
        f"Cliente atualizado: {_lista('clientes')}",
        f"Contato atualizado: {_lista('contatos')}",
        r"Oportunidade #\d+ criada",
        rf"Oportunidade #\d+ atualizada: {_lista('oportunidades')}",
        rf"Oportunidade #\d+ (?:movida para|reaberta em) (?:{etapas})",
        r"Tarefa #\d+ criada",
        rf"Tarefa #\d+ atualizada: {_lista('tarefas')}",
        rf"Tarefa #\d+ (?:{acoes_tarefa})",
    ]
    return re.compile("|".join(f"(?:{f})" for f in formas), re.ASCII)


def _sujos(conn: sqlite3.Connection) -> dict[str, set[int]]:
    """Por tabela, os clientes anonimizados que ainda têm algo que a anonimização apaga."""
    sujos: dict[str, set[int]] = {}

    def marcar(tabela: str, cliente_id: int) -> None:
        sujos.setdefault(tabela, set()).add(cliente_id)

    for cid, nome, fantasia, documento, email, observacoes, busca in _linhas(
        conn, "clientes", "nome, nome_fantasia, documento, email, observacoes, busca"
    ):
        esperado = f"Cliente anonimizado #{cid}"
        livres = (fantasia, documento, email, observacoes)
        if nome != esperado or any(livres) or busca != search_key(esperado, None, None):
            marcar("clientes", cid)
    for cid, _ in _linhas(conn, "contatos", "x.id"):
        marcar("contatos", cid)
    seus: dict[tuple[int, str], set[str]] = {}
    colunas = "x.id, x.titulo, x.observacoes, x.motivo_detalhe"
    for cid, oid, titulo, observacoes, detalhe in _linhas(conn, "oportunidades", colunas):
        seus.setdefault((cid, "Oportunidade"), set()).add(str(oid))
        if titulo != f"Oportunidade #{oid}" or observacoes is not None or detalhe is not None:
            marcar("oportunidades", cid)
    for cid, tid, titulo, descricao in _linhas(conn, "tarefas", "x.id, x.titulo, x.descricao"):
        seus.setdefault((cid, "Tarefa"), set()).add(str(tid))
        if titulo != f"Tarefa #{tid}" or descricao is not None:
            marcar("tarefas", cid)
    eventos = _eventos()
    for cid, tipo, resumo in _linhas(conn, "interacoes", "x.tipo, x.resumo"):
        if not isinstance(resumo, str):
            limpo = False
        elif tipo != "sistema":
            limpo = resumo == CONTEUDO_REMOVIDO
        else:
            ref = _REFERENCIA.match(resumo)
            dono_ok = ref is None or ref[2] in seus.get((cid, ref[1]), set())
            limpo = dono_ok and eventos.fullmatch(resumo) is not None
        if not limpo:
            marcar("interacoes", cid)
    for tabela in _DONO:
        datas = [
            f"x.{c.name}"
            for c in Base.metadata.tables[tabela].columns
            if isinstance(c.type, (DateTime, Date))
        ]
        for cid, *valores in _linhas(conn, tabela, ", ".join(datas)):
            if not all(_data_valida(v) for v in valores):
                marcar(tabela, cid)
    return sujos


def verificar_anonimizacao(caminho: Path) -> None:
    """Recusa o backup se algum cliente anonimizado ainda tiver dados pessoais.

    A mensagem diz quantos clientes e em quais tabelas, nunca o conteúdo.
    """
    try:
        conn = abrir_leitura(caminho)
        try:
            sujos = _sujos(conn)
        finally:
            conn.close()
    except sqlite3.DatabaseError as erro:
        raise BackupInvalido(f"falha ao conferir a anonimização ({type(erro).__name__})") from erro
    if sujos:
        clientes = set().union(*sujos.values())
        raise BackupInvalido(
            f"{len(clientes)} cliente(s) marcado(s) como anonimizado(s) ainda com dados "
            f"pessoais ({', '.join(sorted(sujos))})"
        )
