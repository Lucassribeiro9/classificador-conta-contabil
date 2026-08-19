from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.database import Base
from core.models import (
    Empresa,
    LoteImportacaoMovimentoOperacional,
    MovimentoOperacionalImportado,
    Usuario,
)
from core.movimentos_operacionais_snapshot import (
    LoteOperacionalSnapshotNotFound,
    build_lote_operacional_snapshot,
)


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def _empresa(
    *,
    nome: str = "Empresa Snapshot LTDA",
    api_key: str = "api-key-snapshot",
    cnpj_cpf: str = "11222333000144",
    cod_dominio: int = 1122,
) -> Empresa:
    return Empresa(
        nome_empresa=nome,
        api_key=api_key,
        cnpj_cpf=cnpj_cpf,
        cod_dominio=cod_dominio,
    )


def _usuario() -> Usuario:
    return Usuario(
        nome="Operador Snapshot",
        login="operador.snapshot",
        email="operador.snapshot@example.com",
        senha_hash="$argon2id$v=19$hash-de-teste",
        papel="operador",
    )


def _lote(
    empresa: Empresa,
    usuario: Usuario,
    *,
    layout_version: str,
) -> LoteImportacaoMovimentoOperacional:
    return LoteImportacaoMovimentoOperacional(
        empresa=empresa,
        usuario=usuario,
        original_filename="movimentos.xlsx",
        file_hash=f"sha256:{layout_version}",
        status="completed_with_warnings",
        total_linhas=2,
        total_importadas=2,
        total_invalidas=0,
        warnings_metadata={"warnings": []},
        periodo_inicio=date(2026, 1, 1),
        periodo_fim=date(2026, 1, 31),
        cnpj_cpf_arquivo=empresa.cnpj_cpf,
        codigo_dominio_arquivo=str(empresa.cod_dominio),
        layout_version=layout_version,
    )


def _movimento(
    lote: LoteImportacaoMovimentoOperacional,
    empresa: Empresa,
    *,
    linha_original: int,
    status: str,
    contrapartida_informada: int | None = None,
    contrapartida_sugerida: int | None = None,
    contrapartida_final: int | None = None,
    confidence_sugerida: float | None = None,
    mensagens_validacao: list[str] | None = None,
    row_version: int = 1,
    saldo_observado_original: str | None = None,
    saldo_observado_decimal: Decimal | None = None,
    saldo_calculado_decimal: Decimal | None = None,
    warnings_saldo: list[str] | None = None,
) -> MovimentoOperacionalImportado:
    return MovimentoOperacionalImportado(
        lote=lote,
        empresa=empresa,
        data=date(2026, 1, linha_original),
        conta_financeira=10046,
        historico=f"Pagamento linha {linha_original}",
        historico_normalizado=f"pagamento linha {linha_original}",
        valor_original=Decimal("-250.75"),
        valor_absoluto=Decimal("250.75"),
        direcao="credito",
        tipo_movimento="saida",
        documento=f"DOC-{linha_original}",
        observacao="observacao original",
        contrapartida_informada=contrapartida_informada,
        contrapartida_sugerida=contrapartida_sugerida,
        contrapartida_final=contrapartida_final,
        confidence_sugerida=confidence_sugerida,
        status=status,
        elegivel_treino=status in {"aprovado", "corrigido"},
        mensagens_validacao=mensagens_validacao or [],
        conta_debito=contrapartida_final,
        conta_credito=10046 if contrapartida_final else None,
        linha_original=linha_original,
        row_version=row_version,
        saldo_observado_original=saldo_observado_original,
        saldo_observado_decimal=saldo_observado_decimal,
        saldo_calculado_decimal=saldo_calculado_decimal,
        warnings_saldo=warnings_saldo or [],
    )


def test_snapshot_preserva_ordem_versoes_e_separa_entrada_sugestao_e_decisao(session):
    empresa = _empresa()
    usuario = _usuario()
    lote = _lote(
        empresa,
        usuario,
        layout_version="operacional_valor_saldo_v1",
    )
    session.add(lote)
    session.flush()
    session.add_all(
        [
            _movimento(
                lote,
                empresa,
                linha_original=2,
                status="aprovado",
                contrapartida_informada=10722,
                contrapartida_sugerida=20722,
                contrapartida_final=30722,
                confidence_sugerida=0.91,
                row_version=3,
            ),
            _movimento(
                lote,
                empresa,
                linha_original=1,
                status="sugerido",
                contrapartida_informada=None,
                contrapartida_sugerida=40101,
                contrapartida_final=None,
                confidence_sugerida=0.86,
                mensagens_validacao=["aguardando aprovacao humana"],
                row_version=1,
            ),
        ]
    )
    session.commit()

    snapshot = build_lote_operacional_snapshot(
        session,
        empresa_id=empresa.id,
        lote_id=lote.id,
    )

    UUID(snapshot.export_revision)
    assert snapshot.lote_id == lote.id
    assert snapshot.empresa_id == empresa.id
    assert snapshot.layout_version == "operacional_valor_saldo_v1"
    assert [item.linha_original for item in snapshot.movimentos] == [1, 2]
    assert {item.export_revision for item in snapshot.movimentos} == {
        snapshot.export_revision
    }

    sugerido = snapshot.movimentos[0]
    assert sugerido.row_version == 1
    assert sugerido.contrapartida is None
    assert sugerido.contrapartida_sugerida == 40101
    assert sugerido.contrapartida_final is None
    assert sugerido.confidence_sugerida == 0.86
    assert sugerido.status_atual == "sugerido"
    assert sugerido.mensagem_validacao == ["aguardando aprovacao humana"]
    assert sugerido.warnings_saldo == []

    aprovado = snapshot.movimentos[1]
    assert aprovado.row_version == 3
    assert aprovado.contrapartida == 10722
    assert aprovado.contrapartida_sugerida == 20722
    assert aprovado.contrapartida_final == 30722
    assert aprovado.status_atual == "aprovado"


def test_snapshot_reflete_saldos_persistidos(session):
    empresa = _empresa(api_key="api-key-snapshot-saldo")
    usuario = _usuario()
    lote = _lote(
        empresa,
        usuario,
        layout_version="operacional_valor_saldo_v1",
    )
    session.add(lote)
    session.flush()
    session.add(
        _movimento(
            lote,
            empresa,
            linha_original=1,
            status="sugerido",
            saldo_observado_original="1000",
            saldo_observado_decimal=Decimal("1000.00"),
            saldo_calculado_decimal=Decimal("950.00"),
            warnings_saldo=[
                "Saldo observado diverge do saldo calculado para a conta financeira."
            ],
        )
    )
    session.commit()

    snapshot = build_lote_operacional_snapshot(
        session,
        empresa_id=empresa.id,
        lote_id=lote.id,
    )

    item = snapshot.movimentos[0]
    assert item.saldo_observado_original == "1000"
    assert item.saldo_observado_decimal == Decimal("1000.00")
    assert item.saldo_calculado_decimal == Decimal("950.00")
    assert item.warnings_saldo == [
        "Saldo observado diverge do saldo calculado para a conta financeira."
    ]


def test_snapshot_bloqueia_lote_inexistente_ou_de_outra_empresa(session):
    empresa = _empresa()
    outra_empresa = _empresa(
        nome="Outra Empresa Snapshot LTDA",
        api_key="api-key-snapshot-outra",
        cnpj_cpf="99888777000166",
        cod_dominio=9988,
    )
    usuario = _usuario()
    lote = _lote(
        outra_empresa,
        usuario,
        layout_version="operacional_valor_saldo_v1",
    )
    session.add_all([empresa, lote])
    session.commit()

    with pytest.raises(LoteOperacionalSnapshotNotFound):
        build_lote_operacional_snapshot(
            session,
            empresa_id=empresa.id,
            lote_id=lote.id,
        )

    with pytest.raises(LoteOperacionalSnapshotNotFound):
        build_lote_operacional_snapshot(
            session,
            empresa_id=empresa.id,
            lote_id=999999,
        )


@pytest.mark.parametrize(
    "layout_version",
    [
        "operacional_valor_saldo_v1",
        "operacional_debito_credito_saldo_v1",
        "operacional_valor_legado_v1",
    ],
)
def test_snapshot_preserva_layout_do_lote(layout_version, session):
    empresa = _empresa(api_key=f"api-{layout_version}")
    usuario = _usuario()
    lote = _lote(empresa, usuario, layout_version=layout_version)
    session.add(lote)
    session.flush()
    session.add(
        _movimento(
            lote,
            empresa,
            linha_original=1,
            status="pendente",
            row_version=1,
        )
    )
    session.commit()

    snapshot = build_lote_operacional_snapshot(
        session,
        empresa_id=empresa.id,
        lote_id=lote.id,
    )

    assert snapshot.layout_version == layout_version
    assert snapshot.movimentos[0].layout_version == layout_version
