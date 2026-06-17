from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.database import Base
from core.dataset_builder import build_dataset_treino_contrapartida
from core.models import (
    Empresa,
    LancamentoRazaoNormalizado,
    LoteImportacaoRazao,
    Usuario,
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


def _empresa(**overrides) -> Empresa:
    data = {
        "nome_empresa": "Empresa Dataset LTDA",
        "cnpj_cpf": "11222333000144",
        "api_key": "api-key-dataset",
        "cod_dominio": 9901,
    }
    data.update(overrides)
    return Empresa(**data)


def _usuario() -> Usuario:
    return Usuario(
        nome="Operador Dataset",
        login="operador.dataset",
        email="operador.dataset@example.com",
        senha_hash="$argon2id$v=19$hash-de-teste",
        papel="operador",
    )


def _lancamento(
    lote: LoteImportacaoRazao,
    empresa: Empresa,
    **overrides,
) -> LancamentoRazaoNormalizado:
    data = {
        "lote": lote,
        "empresa": empresa,
        "numero_lancamento": "42",
        "data": date(2026, 1, 15),
        "conta_origem": 10046,
        "conta_contrapartida": 50057,
        "conta_debito": 50057,
        "conta_credito": 10046,
        "direcao": "credito",
        "historico": "Recebimento cliente",
        "historico_normalizado": "recebimento cliente",
        "valor": Decimal("2500.00"),
    }
    data.update(overrides)
    return LancamentoRazaoNormalizado(**data)


def test_dataset_builder_can_be_called_for_known_company(session):
    empresa = _empresa()
    lote = LoteImportacaoRazao(
        empresa=empresa,
        usuario=_usuario(),
        original_filename="razao-janeiro.xlsx",
        file_hash="sha256:abc123",
        status="completed",
    )
    session.add(_lancamento(lote=lote, empresa=empresa))
    session.commit()

    dataset = build_dataset_treino_contrapartida(session, empresa_id=empresa.id)

    assert dataset.metadata["empresa_id"] == empresa.id
    assert dataset.linhas == [
        {
            "features": "recebimento cliente origem_10046 direcao_credito",
            "target_conta_contrapartida": 50057,
        }
    ]


def test_dataset_builder_returns_explicit_lines_and_metadata(session):
    empresa = _empresa()
    lote = LoteImportacaoRazao(
        empresa=empresa,
        usuario=_usuario(),
        original_filename="razao-janeiro.xlsx",
        file_hash="sha256:abc123",
        status="completed",
    )
    session.add(_lancamento(lote=lote, empresa=empresa))
    session.commit()

    dataset = build_dataset_treino_contrapartida(session, empresa_id=empresa.id)

    assert isinstance(dataset.linhas, list)
    assert dataset.metadata == {
        "empresa_id": empresa.id,
        "total_linhas": 1,
        "total_descartes": 0,
        "contagem_por_target": {50057: 1},
        "treinavel": True,
    }


def test_dataset_builder_returns_empty_dataset_when_company_has_no_lines(session):
    empresa = _empresa()
    session.add(empresa)
    session.commit()

    dataset = build_dataset_treino_contrapartida(session, empresa_id=empresa.id)

    assert dataset.linhas == []
    assert dataset.metadata == {
        "empresa_id": empresa.id,
        "total_linhas": 0,
        "total_descartes": 0,
        "contagem_por_target": {},
        "treinavel": False,
    }


def test_dataset_builder_keeps_examples_isolated_by_company(session):
    empresa_a = _empresa()
    empresa_b = _empresa(
        nome_empresa="Empresa Vizinha LTDA",
        cnpj_cpf="99888777000166",
        api_key="api-key-vizinha",
        cod_dominio=9902,
    )
    operador = _usuario()
    lote_a = LoteImportacaoRazao(
        empresa=empresa_a,
        usuario=operador,
        original_filename="razao-empresa-a.xlsx",
        file_hash="sha256:empresa-a",
        status="completed",
    )
    lote_b = LoteImportacaoRazao(
        empresa=empresa_b,
        usuario=operador,
        original_filename="razao-empresa-b.xlsx",
        file_hash="sha256:empresa-b",
        status="completed",
    )
    session.add_all(
        [
            _lancamento(lote=lote_a, empresa=empresa_a),
            _lancamento(
                lote=lote_b,
                empresa=empresa_b,
                conta_origem=10046,
                conta_contrapartida=70001,
                conta_debito=70001,
                conta_credito=10046,
                historico="Recebimento cliente",
                historico_normalizado="recebimento cliente",
            ),
        ]
    )
    session.commit()

    dataset = build_dataset_treino_contrapartida(session, empresa_id=empresa_a.id)

    assert dataset.linhas == [
        {
            "features": "recebimento cliente origem_10046 direcao_credito",
            "target_conta_contrapartida": 50057,
        }
    ]
    assert dataset.metadata["empresa_id"] == empresa_a.id
    assert dataset.metadata["total_linhas"] == 1
    assert dataset.metadata["contagem_por_target"] == {50057: 1}


def test_dataset_builder_rejects_missing_company_scope(session):
    with pytest.raises(ValueError, match="empresa_id"):
        build_dataset_treino_contrapartida(session, empresa_id=None)
