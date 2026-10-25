"""Regras de clientes, contatos e interações (Fase 02, E3).

Cada função é uma unidade de trabalho e faz o próprio commit. Eventos (`tipo="sistema"`)
registram a ação e os nomes dos campos, nunca os valores (D4). Interações só aceitam
acréscimo (D5): não há função de edição nem de exclusão.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import String, cast, delete, select, text, update
from sqlalchemy.orm import Session

from salesos.features.clientes.models import Cliente, Contato, Interacao
from salesos.features.clientes.normalize import like_contains, search_key
from salesos.features.clientes.schemas import ClienteIn, ContatoIn, InteracaoIn
from salesos.features.oportunidades.models import Oportunidade

logger = logging.getLogger(__name__)

POR_PAGINA_MAX = 100
CONTATOS_MAX = 200
CONTEUDO_REMOVIDO = "[conteúdo removido]"


class NaoEncontrado(LookupError):
    pass


class Duplicado(ValueError):
    pass


class Bloqueado(Exception):
    """Cliente anonimizado: não aceita mudanças (D9)."""


@dataclass(frozen=True)
class Pagina:
    itens: list[Cliente]
    pagina: int
    tem_proxima: bool


def _agora() -> datetime:
    return datetime.now(UTC)


def registrar_evento(session: Session, cliente_id: int, resumo: str) -> None:
    session.add(
        Interacao(cliente_id=cliente_id, tipo="sistema", ocorrida_em=_agora(), resumo=resumo)
    )


def _aplicar(alvo: Cliente | Contato, dados: ClienteIn | ContatoIn) -> list[str]:
    """Copia os campos e devolve os nomes dos que mudaram (nunca os valores)."""
    mudou = []
    for campo, valor in dados.model_dump().items():
        if getattr(alvo, campo) != valor:
            setattr(alvo, campo, valor)
            mudou.append(campo)
    return sorted(mudou)


def _busca(cliente: Cliente) -> str:
    return search_key(cliente.nome, cliente.nome_fantasia, cliente.email)


def cliente_editavel(session: Session, cliente_id: int) -> Cliente:
    cliente = obter_cliente(session, cliente_id)
    if cliente.anonimizado_em is not None:
        raise Bloqueado("cliente anonimizado")
    return cliente


def _email_livre(session: Session, email: str | None, exceto_id: int | None = None) -> None:
    if email is None:
        return
    query = select(Cliente.id).where(Cliente.email == email, Cliente.id != exceto_id)
    if session.scalar(query) is not None:
        raise Duplicado("e-mail já usado por outro cliente")


def _email_de_contato_livre(
    session: Session, cliente_id: int, email: str | None, exceto_id: int | None = None
) -> None:
    if email is None:
        return
    query = select(Contato.id).where(
        Contato.cliente_id == cliente_id, Contato.email == email, Contato.id != exceto_id
    )
    if session.scalar(query) is not None:
        raise Duplicado("e-mail já usado por outro contato deste cliente")


def obter_cliente(session: Session, cliente_id: int) -> Cliente:
    cliente = session.get(Cliente, cliente_id)
    if cliente is None:
        raise NaoEncontrado("cliente não encontrado")
    return cliente


def criar_cliente(session: Session, dados: ClienteIn) -> Cliente:
    _email_livre(session, dados.email)
    cliente = Cliente(**dados.model_dump())
    cliente.busca = _busca(cliente)
    session.add(cliente)
    session.flush()
    registrar_evento(session, cliente.id, "Cliente criado")
    session.commit()
    return cliente


def atualizar_cliente(session: Session, cliente_id: int, dados: ClienteIn) -> Cliente:
    cliente = cliente_editavel(session, cliente_id)
    _email_livre(session, dados.email, exceto_id=cliente.id)
    if mudou := _aplicar(cliente, dados):
        cliente.busca = _busca(cliente)
        registrar_evento(session, cliente.id, f"Cliente atualizado: {', '.join(mudou)}")
        session.commit()
    return cliente


def listar_clientes(
    session: Session,
    termo: str = "",
    arquivados: bool = False,
    pagina: int = 1,
    por_pagina: int = 20,
) -> Pagina:
    pagina = max(1, pagina)
    por_pagina = min(max(1, por_pagina), POR_PAGINA_MAX)
    query = select(Cliente).where(
        Cliente.archived_at.is_not(None) if arquivados else Cliente.archived_at.is_(None)
    )
    if chave := search_key(termo):
        query = query.where(Cliente.busca.like(like_contains(chave), escape="\\"))
    # `busca` começa pelo nome sem acento e em casefold: ordem alfabética de verdade.
    query = query.order_by(Cliente.busca, Cliente.id)
    query = query.offset((pagina - 1) * por_pagina).limit(por_pagina + 1)
    itens = list(session.scalars(query))
    return Pagina(itens[:por_pagina], pagina, len(itens) > por_pagina)


def arquivar_cliente(session: Session, cliente_id: int) -> None:
    cliente = obter_cliente(session, cliente_id)
    if cliente.archived_at is None:
        cliente.archived_at = _agora()
        registrar_evento(session, cliente.id, "Cliente arquivado")
        session.commit()


def desarquivar_cliente(session: Session, cliente_id: int) -> None:
    cliente = cliente_editavel(session, cliente_id)
    if cliente.archived_at is not None:
        cliente.archived_at = None
        registrar_evento(session, cliente.id, "Cliente desarquivado")
        session.commit()


def listar_contatos(session: Session, cliente_id: int) -> list[Contato]:
    query = (
        select(Contato)
        .where(Contato.cliente_id == cliente_id)
        .order_by(Contato.nome, Contato.id)
        .limit(CONTATOS_MAX)
    )
    return list(session.scalars(query))


def obter_contato(session: Session, contato_id: int) -> Contato:
    contato = session.get(Contato, contato_id)
    if contato is None:
        raise NaoEncontrado("contato não encontrado")
    return contato


def adicionar_contato(session: Session, cliente_id: int, dados: ContatoIn) -> Contato:
    cliente = cliente_editavel(session, cliente_id)
    _email_de_contato_livre(session, cliente.id, dados.email)
    contato = Contato(cliente_id=cliente.id, **dados.model_dump())
    session.add(contato)
    registrar_evento(session, cliente.id, "Contato adicionado")
    session.commit()
    return contato


def atualizar_contato(session: Session, contato_id: int, dados: ContatoIn) -> Contato:
    contato = obter_contato(session, contato_id)
    cliente_editavel(session, contato.cliente_id)
    _email_de_contato_livre(session, contato.cliente_id, dados.email, exceto_id=contato.id)
    if mudou := _aplicar(contato, dados):
        registrar_evento(session, contato.cliente_id, f"Contato atualizado: {', '.join(mudou)}")
        session.commit()
    return contato


def remover_contato(session: Session, contato_id: int) -> None:
    """D3: o contato sai; as interações ligadas ficam com `contato_id` nulo (FK SET NULL)."""
    contato = obter_contato(session, contato_id)
    cliente_id = contato.cliente_id
    cliente_editavel(session, cliente_id)
    session.delete(contato)
    registrar_evento(session, cliente_id, "Contato removido")
    session.commit()


def registrar_interacao(session: Session, cliente_id: int, dados: InteracaoIn) -> Interacao:
    cliente = cliente_editavel(session, cliente_id)
    if dados.contato_id is not None:
        contato = session.get(Contato, dados.contato_id)
        if contato is None or contato.cliente_id != cliente.id:
            raise NaoEncontrado("contato não encontrado neste cliente")
    interacao = Interacao(cliente_id=cliente.id, **dados.model_dump())
    session.add(interacao)
    session.commit()
    return interacao


def listar_interacoes(session: Session, cliente_id: int, limite: int = 50) -> list[Interacao]:
    query = (
        select(Interacao)
        .where(Interacao.cliente_id == cliente_id)
        .order_by(Interacao.ocorrida_em.desc(), Interacao.id.desc())
        .limit(min(max(1, limite), POR_PAGINA_MAX))
    )
    return list(session.scalars(query))


def anonimizar_cliente(session: Session, cliente_id: int) -> None:
    """D9: irreversível na aplicação. Mantém o ID, as interações e os eventos.

    `secure_delete` zera o conteúdo antigo no arquivo e o checkpoint esvazia o `-wal`;
    isso não alcança backups nem outras cópias (não é garantia forense).
    """
    cliente = obter_cliente(session, cliente_id)
    if cliente.anonimizado_em is not None:
        return
    agora = _agora()
    cliente.nome = f"Cliente anonimizado #{cliente.id}"
    cliente.nome_fantasia = cliente.email = cliente.observacoes = cliente.documento = None
    cliente.busca = _busca(cliente)
    cliente.archived_at = cliente.archived_at or agora
    cliente.anonimizado_em = agora
    session.execute(delete(Contato).where(Contato.cliente_id == cliente.id))
    # R10 (ADR 0006): some o texto livre; valor, etapa e datas ficam (retenção: pendência P1).
    session.execute(
        update(Oportunidade)
        .where(Oportunidade.cliente_id == cliente.id)
        .values(
            titulo="Oportunidade #" + cast(Oportunidade.id, String),
            observacoes=None,
            motivo_detalhe=None,
        )
    )
    session.execute(
        update(Interacao)
        .where(Interacao.cliente_id == cliente.id, Interacao.tipo != "sistema")
        .values(resumo=CONTEUDO_REMOVIDO)
    )
    registrar_evento(session, cliente.id, "Cliente anonimizado")
    session.commit()
    ocupado = session.execute(text("PRAGMA wal_checkpoint(TRUNCATE)")).scalar()
    session.commit()
    if ocupado:
        # O `-wal` pode manter o conteúdo antigo até o próximo checkpoint completo.
        logger.warning("Checkpoint do WAL incompleto após anonimizar o cliente %s", cliente.id)
