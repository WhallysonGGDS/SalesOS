"""Privacidade do funil (R9, R10) com valores-sentinela fictícios."""

from pathlib import Path

import pytest
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from salesos.backup import criar_backup
from salesos.db import create_db_engine
from salesos.features.clientes import service as clientes
from salesos.features.clientes.models import Interacao
from salesos.features.clientes.schemas import ClienteIn
from salesos.features.oportunidades import service
from salesos.features.oportunidades.models import Movimentacao, Oportunidade
from salesos.features.oportunidades.schemas import MudancaEtapaIn, OportunidadeIn
from salesos.restore import RestauracaoRecusada, restaurar
from tests.backup.conftest import criar_banco

TITULO = "Qwxtitulosentinela"
OBSERVACOES = "Qwxobservacaooportunidade"
DETALHE = "Qwxdetalhesentinela"
VALOR = 987654  # "9.876,54"
SENTINELAS = [TITULO, OBSERVACOES, DETALHE]


def _percorrer(session: Session) -> Oportunidade:
    cliente = clientes.criar_cliente(session, ClienteIn(tipo="PJ", nome="Empresa", origem="site"))
    dados = OportunidadeIn(titulo=TITULO, valor_centavos=VALOR, observacoes=OBSERVACOES)
    oportunidade = service.criar_oportunidade(session, cliente.id, dados)
    service.mudar_etapa(
        session,
        oportunidade.id,
        MudancaEtapaIn(etapa="perdida", motivo_perda="outro", motivo_detalhe=DETALHE),
    )
    service.mudar_etapa(session, oportunidade.id, MudancaEtapaIn(etapa="negociacao"))
    service.mudar_etapa(
        session,
        oportunidade.id,
        MudancaEtapaIn(etapa="perdida", motivo_perda="outro", motivo_detalhe=DETALHE),
    )
    service.atualizar_oportunidade(
        session,
        oportunidade.id,
        OportunidadeIn(titulo=TITULO, valor_centavos=VALOR + 1, observacoes=OBSERVACOES),
    )
    session.refresh(oportunidade)
    assert oportunidade.observacoes == OBSERVACOES  # o texto existe até a anonimização
    return oportunidade


def _bytes_do_banco(engine: Engine) -> bytes:
    caminho = Path(str(engine.url.database))
    partes = [caminho, caminho.with_name(caminho.name + "-wal")]
    return b"".join(p.read_bytes() for p in partes if p.exists()).lower()


def test_events_never_contain_title_notes_detail_or_value(session: Session) -> None:
    oportunidade = _percorrer(session)
    eventos = session.scalars(
        select(Interacao.resumo).where(Interacao.cliente_id == oportunidade.cliente_id)
    ).all()
    texto = " ".join(eventos).lower()
    proibidos = [*SENTINELAS, str(VALOR), "9.876,54", "9876,54", "9.876,55", "outro"]
    assert [p for p in proibidos if p.lower() in texto] == []


def test_anonymization_erases_text_and_keeps_commercial_fields(session: Session) -> None:
    oportunidade = _percorrer(session)
    historico = session.execute(select(Movimentacao.id, Movimentacao.para_etapa)).all()
    clientes.anonimizar_cliente(session, oportunidade.cliente_id)
    session.refresh(oportunidade)
    assert oportunidade.titulo == f"Oportunidade #{oportunidade.id}"
    assert (oportunidade.observacoes, oportunidade.motivo_detalhe) == (None, None)
    assert (oportunidade.etapa, oportunidade.motivo_perda) == ("perdida", "outro")
    assert oportunidade.valor_centavos == VALOR + 1
    assert oportunidade.fechada_em is not None
    assert session.execute(select(Movimentacao.id, Movimentacao.para_etapa)).all() == historico


def test_database_files_do_not_keep_opportunity_text(
    session: Session, migrated_engine: Engine
) -> None:
    oportunidade = _percorrer(session)
    antes = _bytes_do_banco(migrated_engine)
    assert all(s.lower().encode() in antes for s in SENTINELAS)
    clientes.anonimizar_cliente(session, oportunidade.cliente_id)
    depois = _bytes_do_banco(migrated_engine)
    assert [s for s in SENTINELAS if s.lower().encode() in depois] == []


def test_restore_refuses_backup_that_would_bring_back_opportunity_text(tmp_path: Path) -> None:
    db = criar_banco(tmp_path / "dados" / "salesos.db")
    engine = create_db_engine(f"sqlite:///{db}")
    with Session(engine) as session:
        cliente_id = _percorrer(session).cliente_id
    engine.dispose()
    arquivo = criar_backup(db, tmp_path / "backups")
    engine = create_db_engine(f"sqlite:///{db}")
    with Session(engine) as session:
        clientes.anonimizar_cliente(session, cliente_id)
    engine.dispose()
    with pytest.raises(RestauracaoRecusada, match="anonimiza"):
        restaurar(db, arquivo, tmp_path / "backups")
