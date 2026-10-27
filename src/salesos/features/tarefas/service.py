"""Regras das tarefas (Fase 04, ADR 0007).

Cada função é uma unidade de trabalho: a operação, o `TarefaEvento` e o evento do cliente vão
no mesmo commit (D6). Eventos do cliente levam só o número da tarefa e a ação, nunca título
nem descrição. Não existe função que edite ou apague eventos.
"""

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import ColumnElement, Select, case, func, select
from sqlalchemy.orm import Session

from salesos.features.clientes.service import NaoEncontrado, cliente_editavel, registrar_evento
from salesos.features.oportunidades.models import Oportunidade
from salesos.features.tarefas.models import Tarefa, TarefaEvento
from salesos.features.tarefas.schemas import FiltroTarefas, TarefaIn
from salesos.formularios import RegraViolada
from salesos.periodo import intervalo_utc

POR_PAGINA = 20
RELACIONADAS_MAX = 50
EVENTOS_MAX = 200
ACAO_NO_EVENTO = {"concluida": "concluída", "cancelada": "cancelada", "pendente": "reaberta"}


@dataclass(frozen=True)
class PaginaTarefas:
    itens: list[Tarefa]
    pagina: int
    tem_proxima: bool


def _agora() -> datetime:
    return datetime.now(UTC)


def _texto(momento: datetime) -> str:
    """Formato de `datetime()` do SQLite, em UTC, para comparar com o que está gravado."""
    return momento.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S")


def _prazo() -> ColumnElement[str]:
    # `datetime()` normaliza o texto gravado (com ou sem frações); texto inválido vira NULL.
    return func.datetime(Tarefa.prazo)


def obter_tarefa(session: Session, tarefa_id: int) -> Tarefa:
    tarefa = session.get(Tarefa, tarefa_id)
    if tarefa is None:
        raise NaoEncontrado("tarefa não encontrada")
    return tarefa


def tarefa_editavel(session: Session, tarefa_id: int) -> Tarefa:
    tarefa = obter_tarefa(session, tarefa_id)
    cliente_editavel(session, tarefa.cliente_id)  # anonimizado → Bloqueado
    return tarefa


def _oportunidade_do_cliente(session: Session, cliente_id: int, oportunidade: int | None) -> None:
    if oportunidade is None:
        return
    encontrada = session.get(Oportunidade, oportunidade)
    if encontrada is None or encontrada.cliente_id != cliente_id:
        raise RegraViolada("oportunidade_id", "Escolha uma oportunidade deste cliente")


def _registrar(session: Session, tarefa: Tarefa, acao: str) -> None:
    session.add(TarefaEvento(tarefa_id=tarefa.id, acao=acao, ocorrida_em=_agora()))


def criar_tarefa(session: Session, cliente_id: int, dados: TarefaIn) -> Tarefa:
    cliente = cliente_editavel(session, cliente_id)
    _oportunidade_do_cliente(session, cliente.id, dados.oportunidade_id)
    tarefa = Tarefa(cliente_id=cliente.id, estado="pendente", **dados.model_dump())
    session.add(tarefa)
    session.flush()
    _registrar(session, tarefa, "criada")
    registrar_evento(session, cliente.id, f"Tarefa #{tarefa.id} criada")
    session.commit()
    return tarefa


def atualizar_tarefa(session: Session, tarefa_id: int, dados: TarefaIn) -> Tarefa:
    tarefa = tarefa_editavel(session, tarefa_id)
    if tarefa.estado != "pendente":
        raise RegraViolada("geral", "Só tarefas pendentes podem ser editadas; reabra antes")
    _oportunidade_do_cliente(session, tarefa.cliente_id, dados.oportunidade_id)
    mudou = []
    for campo, valor in dados.model_dump().items():
        atual = getattr(tarefa, campo)
        if campo == "prazo" and atual is not None:
            atual = atual.replace(tzinfo=UTC)  # o SQLite devolve sem fuso; o valor está em UTC
        if atual != valor:
            setattr(tarefa, campo, valor)
            mudou.append(campo)
    if mudou:
        resumo = f"Tarefa #{tarefa.id} atualizada: {', '.join(sorted(mudou))}"
        registrar_evento(session, tarefa.cliente_id, resumo)
        session.commit()
    return tarefa


def _mudar_estado(session: Session, tarefa_id: int, para: str) -> Tarefa:
    tarefa = tarefa_editavel(session, tarefa_id)
    if tarefa.estado == para:
        return tarefa  # envio repetido não gera evento
    if tarefa.estado != "pendente" and para != "pendente":
        raise RegraViolada("geral", "Reabra a tarefa antes de mudar o estado")
    tarefa.estado = para
    tarefa.concluida_em = _agora() if para == "concluida" else None
    tarefa.cancelada_em = _agora() if para == "cancelada" else None
    _registrar(session, tarefa, "reaberta" if para == "pendente" else para)
    resumo = f"Tarefa #{tarefa.id} {ACAO_NO_EVENTO[para]}"
    registrar_evento(session, tarefa.cliente_id, resumo)
    session.commit()
    return tarefa


def concluir_tarefa(session: Session, tarefa_id: int) -> Tarefa:
    return _mudar_estado(session, tarefa_id, "concluida")


def cancelar_tarefa(session: Session, tarefa_id: int) -> Tarefa:
    return _mudar_estado(session, tarefa_id, "cancelada")


def reabrir_tarefa(session: Session, tarefa_id: int) -> Tarefa:
    return _mudar_estado(session, tarefa_id, "pendente")


def esta_vencida(tarefa: Tarefa, agora: datetime | None = None) -> bool:
    """D7: pendente com prazo anterior ao momento atual (o prazo está gravado em UTC)."""
    agora = (agora or _agora()).replace(microsecond=0)  # mesma precisão do contador em SQL
    return tarefa.estado == "pendente" and tarefa.prazo.replace(tzinfo=UTC) < agora


def _vencidas(agora: datetime | None) -> Select[Tarefa]:
    limite = _texto(agora or _agora())
    return select(Tarefa).where(Tarefa.estado == "pendente", _prazo() < limite)


def contar_vencidas(session: Session, agora: datetime | None = None) -> int:
    query = select(func.count()).select_from(_vencidas(agora).subquery())
    return session.scalar(query) or 0


def tarefas_vencidas(session: Session, agora: datetime | None = None) -> list[Tarefa]:
    query = _vencidas(agora).order_by(_prazo(), Tarefa.id).limit(POR_PAGINA)
    return list(session.scalars(query))


def listar_tarefas(session: Session, filtro: FiltroTarefas, pagina: int = 1) -> PaginaTarefas:
    query = select(Tarefa)
    if filtro.estado != "todas":
        query = query.where(Tarefa.estado == filtro.estado)
    if filtro.prioridade:
        query = query.where(Tarefa.prioridade == filtro.prioridade)
    if filtro.tipo:
        query = query.where(Tarefa.tipo == filtro.tipo)
    inicio, fim = intervalo_utc(filtro.de, filtro.ate)
    if inicio is not None:
        query = query.where(_prazo() >= _texto(inicio))
    if fim is not None:
        query = query.where(_prazo() < _texto(fim))
    pagina = max(1, pagina)
    query = query.order_by(_prazo(), Tarefa.id)
    itens = list(session.scalars(query.offset((pagina - 1) * POR_PAGINA).limit(POR_PAGINA + 1)))
    return PaginaTarefas(itens[:POR_PAGINA], pagina, len(itens) > POR_PAGINA)


def _relacionadas(condicao: ColumnElement[bool]) -> Select[Tarefa]:
    pendentes_primeiro = case((Tarefa.estado == "pendente", 0), else_=1)
    query = select(Tarefa).where(condicao).order_by(pendentes_primeiro, _prazo(), Tarefa.id)
    return query.limit(RELACIONADAS_MAX)


def tarefas_do_cliente(session: Session, cliente_id: int) -> list[Tarefa]:
    return list(session.scalars(_relacionadas(Tarefa.cliente_id == cliente_id)))


def tarefas_da_oportunidade(session: Session, oportunidade_id: int) -> list[Tarefa]:
    return list(session.scalars(_relacionadas(Tarefa.oportunidade_id == oportunidade_id)))


def eventos(session: Session, tarefa_id: int) -> list[TarefaEvento]:
    query = (
        select(TarefaEvento)
        .where(TarefaEvento.tarefa_id == tarefa_id)
        .order_by(TarefaEvento.ocorrida_em, TarefaEvento.id)
        .limit(EVENTOS_MAX)
    )
    return list(session.scalars(query))
