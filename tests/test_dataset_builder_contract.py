from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.database import Base
from core.dataset_builder import build_dataset_treino_contrapartida
from core.models import (
    ContaContabil,
    Empresa,
    LancamentoRazaoNormalizado,
    LoteImportacaoRazao,
    Transacao,
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


def _conta(
    codigo: int,
    *,
    is_financial_origin: bool,
    nome: str | None = None,
    tipo: str = "A",
    is_active: bool = True,
) -> ContaContabil:
    return ContaContabil(
        codigo=codigo,
        classificacao=f"1.1.1.{codigo}",
        nome=nome or f"Conta {codigo}",
        tipo=tipo,
        grau=4,
        is_active=is_active,
        is_financial_origin=is_financial_origin,
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


def _seed_valid_dataset(
    session,
    *,
    empresa: Empresa,
    total_linhas: int,
    targets: list[int],
):
    lote = LoteImportacaoRazao(
        empresa=empresa,
        usuario=_usuario(),
        original_filename="razao-treinabilidade.xlsx",
        file_hash=f"sha256:treinabilidade-{total_linhas}-{len(set(targets))}",
        status="completed",
    )
    contas = [_conta(10046, is_financial_origin=True)]
    contas.extend(_conta(target, is_financial_origin=False) for target in set(targets))
    lancamentos = [
        _lancamento(
            lote=lote,
            empresa=empresa,
            numero_lancamento=str(index + 1),
            conta_contrapartida=targets[index],
            conta_debito=targets[index],
            conta_credito=10046,
            historico=f"Lancamento {index + 1}",
            historico_normalizado=f"lancamento {index + 1}",
        )
        for index in range(total_linhas)
    ]
    session.add_all([*contas, *lancamentos])


def test_dataset_builder_can_be_called_for_known_company(session):
    empresa = _empresa()
    lote = LoteImportacaoRazao(
        empresa=empresa,
        usuario=_usuario(),
        original_filename="razao-janeiro.xlsx",
        file_hash="sha256:abc123",
        status="completed",
    )
    session.add_all(
        [
            _conta(10046, is_financial_origin=True),
            _conta(50057, is_financial_origin=False),
            _lancamento(lote=lote, empresa=empresa),
        ]
    )
    session.commit()

    dataset = build_dataset_treino_contrapartida(session, empresa_id=empresa.id)

    assert dataset.metadata["empresa_id"] == empresa.id
    assert dataset.linhas == [
        {
            "features": "recebimento cliente origem_10046 direcao_credito",
            "target_conta_contrapartida": 50057,
        }
    ]


def test_dataset_builder_uses_imported_razao_instead_of_legacy_transactions(session):
    empresa = _empresa()
    lote = LoteImportacaoRazao(
        empresa=empresa,
        usuario=_usuario(),
        original_filename="razao-importado.xlsx",
        file_hash="sha256:razao-importado",
        status="completed",
    )
    session.add_all(
        [
            _conta(10046, is_financial_origin=True),
            _conta(50057, is_financial_origin=False),
            _lancamento(
                lote=lote,
                empresa=empresa,
                historico="Recebimento por razao importado",
                historico_normalizado="recebimento por razao importado",
            ),
            Transacao(
                empresa=empresa,
                data=date(2026, 1, 16),
                cod_banco=1,
                historico="Transacao legada ignorada",
                valor=Decimal("999.99"),
                conta_contabil=101,
            ),
        ]
    )
    session.commit()

    dataset = build_dataset_treino_contrapartida(session, empresa_id=empresa.id)

    assert dataset.linhas == [
        {
            "features": (
                "recebimento por razao importado origem_10046 direcao_credito"
            ),
            "target_conta_contrapartida": 50057,
        }
    ]
    assert dataset.metadata["total_linhas"] == 1
    assert dataset.metadata["contagem_por_target"] == {50057: 1}


def test_dataset_builder_returns_explicit_lines_and_metadata(session):
    empresa = _empresa()
    lote = LoteImportacaoRazao(
        empresa=empresa,
        usuario=_usuario(),
        original_filename="razao-janeiro.xlsx",
        file_hash="sha256:abc123",
        status="completed",
    )
    session.add_all(
        [
            _conta(10046, is_financial_origin=True),
            _conta(50057, is_financial_origin=False),
            _lancamento(lote=lote, empresa=empresa),
        ]
    )
    session.commit()

    dataset = build_dataset_treino_contrapartida(session, empresa_id=empresa.id)

    assert isinstance(dataset.linhas, list)
    assert dataset.metadata == {
        "empresa_id": empresa.id,
        "total_linhas": 1,
        "total_descartes": 0,
        "contagem_por_target": {50057: 1},
        "treinavel": False,
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
            _conta(10046, is_financial_origin=True),
            _conta(50057, is_financial_origin=False),
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


def test_dataset_builder_uses_persisted_flag_instead_of_textual_heuristic(session):
    empresa = _empresa()
    lote = LoteImportacaoRazao(
        empresa=empresa,
        usuario=_usuario(),
        original_filename="razao-fevereiro.xlsx",
        file_hash="sha256:sem-heuristica-textual",
        status="completed",
    )
    session.add_all(
        [
            _conta(
                10046,
                is_financial_origin=False,
                nome="Banco Marcado Como Nao Financeiro",
            ),
            _conta(
                90001,
                is_financial_origin=True,
                nome="Conta Generica Marcada Financeira",
            ),
            _conta(70001, is_financial_origin=False),
            _lancamento(lote=lote, empresa=empresa),
            _lancamento(
                lote=lote,
                empresa=empresa,
                numero_lancamento="43",
                conta_origem=90001,
                conta_contrapartida=70001,
                conta_debito=70001,
                conta_credito=90001,
                historico="Pagamento fornecedor",
                historico_normalizado="pagamento fornecedor",
            ),
        ]
    )
    session.commit()

    dataset = build_dataset_treino_contrapartida(session, empresa_id=empresa.id)

    assert dataset.linhas == [
        {
            "features": "pagamento fornecedor origem_90001 direcao_credito",
            "target_conta_contrapartida": 70001,
        }
    ]
    assert dataset.metadata["contagem_por_target"] == {70001: 1}


def test_dataset_builder_rejects_missing_company_scope(session):
    with pytest.raises(ValueError, match="empresa_id"):
        build_dataset_treino_contrapartida(session, empresa_id=None)


def test_dataset_builder_filters_origin_by_persisted_financial_flag(session):
    empresa = _empresa()
    lote = LoteImportacaoRazao(
        empresa=empresa,
        usuario=_usuario(),
        original_filename="razao-janeiro.xlsx",
        file_hash="sha256:origem-financeira",
        status="completed",
    )
    session.add_all(
        [
            _conta(10046, is_financial_origin=True),
            _conta(90001, is_financial_origin=False),
            _conta(50057, is_financial_origin=False),
            _lancamento(lote=lote, empresa=empresa),
            _lancamento(
                lote=lote,
                empresa=empresa,
                numero_lancamento="43",
                conta_origem=90001,
                conta_contrapartida=70001,
                conta_debito=70001,
                conta_credito=90001,
                historico="Pagamento fornecedor",
                historico_normalizado="pagamento fornecedor",
            ),
        ]
    )
    session.commit()

    dataset = build_dataset_treino_contrapartida(session, empresa_id=empresa.id)

    assert dataset.linhas == [
        {
            "features": "recebimento cliente origem_10046 direcao_credito",
            "target_conta_contrapartida": 50057,
        }
    ]
    assert dataset.metadata["total_linhas"] == 1
    assert dataset.metadata["contagem_por_target"] == {50057: 1}


def test_dataset_builder_features_have_deterministic_initial_format(session):
    empresa = _empresa()
    lote = LoteImportacaoRazao(
        empresa=empresa,
        usuario=_usuario(),
        original_filename="razao-features.xlsx",
        file_hash="sha256:features-iniciais",
        status="completed",
    )
    session.add_all(
        [
            _conta(10046, is_financial_origin=True),
            _conta(50057, is_financial_origin=False),
            _lancamento(
                lote=lote,
                empresa=empresa,
                historico_normalizado="  pagamento pix fornecedor  ",
                valor=Decimal("9876.54"),
            ),
        ]
    )
    session.commit()

    dataset = build_dataset_treino_contrapartida(session, empresa_id=empresa.id)

    features = dataset.linhas[0]["features"]
    assert features == "pagamento pix fornecedor origem_10046 direcao_credito"
    assert "9876.54" not in features


def test_dataset_builder_features_support_minimal_history(session):
    empresa = _empresa()
    lote = LoteImportacaoRazao(
        empresa=empresa,
        usuario=_usuario(),
        original_filename="razao-features-minimas.xlsx",
        file_hash="sha256:features-minimas",
        status="completed",
    )
    session.add_all(
        [
            _conta(10046, is_financial_origin=True),
            _conta(50057, is_financial_origin=False),
            _lancamento(
                lote=lote,
                empresa=empresa,
                historico_normalizado="",
            ),
        ]
    )
    session.commit()

    dataset = build_dataset_treino_contrapartida(session, empresa_id=empresa.id)

    assert dataset.linhas[0]["features"] == "origem_10046 direcao_credito"


def test_dataset_builder_discards_synthetic_and_missing_targets(session):
    empresa = _empresa()
    lote = LoteImportacaoRazao(
        empresa=empresa,
        usuario=_usuario(),
        original_filename="razao-targets.xlsx",
        file_hash="sha256:targets-invalidos",
        status="completed",
    )
    session.add_all(
        [
            _conta(10046, is_financial_origin=True),
            _conta(50057, is_financial_origin=False),
            _conta(70001, is_financial_origin=False, tipo="S"),
            _lancamento(lote=lote, empresa=empresa),
            _lancamento(
                lote=lote,
                empresa=empresa,
                numero_lancamento="43",
                conta_contrapartida=70001,
                conta_debito=70001,
                conta_credito=10046,
                historico="Lancamento com alvo sintetico",
                historico_normalizado="lancamento com alvo sintetico",
            ),
            _lancamento(
                lote=lote,
                empresa=empresa,
                numero_lancamento="44",
                conta_contrapartida=88888,
                conta_debito=88888,
                conta_credito=10046,
                historico="Lancamento com alvo inexistente",
                historico_normalizado="lancamento com alvo inexistente",
            ),
        ]
    )
    session.commit()

    dataset = build_dataset_treino_contrapartida(session, empresa_id=empresa.id)

    assert dataset.linhas == [
        {
            "features": "recebimento cliente origem_10046 direcao_credito",
            "target_conta_contrapartida": 50057,
        }
    ]
    assert dataset.metadata["total_linhas"] == 1
    assert dataset.metadata["total_descartes"] == 2
    assert dataset.metadata["contagem_por_target"] == {50057: 1}


def test_dataset_builder_discards_inactive_target(session):
    empresa = _empresa()
    lote = LoteImportacaoRazao(
        empresa=empresa,
        usuario=_usuario(),
        original_filename="razao-target-inativo.xlsx",
        file_hash="sha256:target-inativo",
        status="completed",
    )
    session.add_all(
        [
            _conta(10046, is_financial_origin=True),
            _conta(50057, is_financial_origin=False),
            _conta(70001, is_financial_origin=False, is_active=False),
            _lancamento(lote=lote, empresa=empresa),
            _lancamento(
                lote=lote,
                empresa=empresa,
                numero_lancamento="43",
                conta_contrapartida=70001,
                conta_debito=70001,
                conta_credito=10046,
                historico="Target inativo",
                historico_normalizado="target inativo",
            ),
        ]
    )
    session.commit()

    dataset = build_dataset_treino_contrapartida(session, empresa_id=empresa.id)

    assert dataset.linhas == [
        {
            "features": "recebimento cliente origem_10046 direcao_credito",
            "target_conta_contrapartida": 50057,
        }
    ]
    assert dataset.metadata["total_linhas"] == 1
    assert dataset.metadata["total_descartes"] == 1
    assert dataset.metadata["contagem_por_target"] == {50057: 1}


def test_dataset_builder_metadata_counts_discards_from_filters_and_validations(
    session,
):
    empresa = _empresa()
    lote = LoteImportacaoRazao(
        empresa=empresa,
        usuario=_usuario(),
        original_filename="razao-metadados.xlsx",
        file_hash="sha256:metadados-descartes",
        status="completed",
    )
    session.add_all(
        [
            _conta(10046, is_financial_origin=True),
            _conta(90001, is_financial_origin=False),
            _conta(50057, is_financial_origin=False),
            _conta(70001, is_financial_origin=False, tipo="S"),
            _lancamento(lote=lote, empresa=empresa),
            _lancamento(
                lote=lote,
                empresa=empresa,
                numero_lancamento="43",
                conta_origem=90001,
                conta_contrapartida=50057,
                conta_debito=50057,
                conta_credito=90001,
                historico="Origem nao financeira",
                historico_normalizado="origem nao financeira",
            ),
            _lancamento(
                lote=lote,
                empresa=empresa,
                numero_lancamento="44",
                conta_contrapartida=70001,
                conta_debito=70001,
                conta_credito=10046,
                historico="Target sintetico",
                historico_normalizado="target sintetico",
            ),
        ]
    )
    session.commit()

    dataset = build_dataset_treino_contrapartida(session, empresa_id=empresa.id)

    assert dataset.metadata == {
        "empresa_id": empresa.id,
        "total_linhas": 1,
        "total_descartes": 2,
        "contagem_por_target": {50057: 1},
        "treinavel": False,
    }


def test_dataset_builder_marks_one_valid_line_as_not_trainable(session):
    empresa = _empresa()
    _seed_valid_dataset(
        session,
        empresa=empresa,
        total_linhas=1,
        targets=[50057],
    )
    session.commit()

    dataset = build_dataset_treino_contrapartida(session, empresa_id=empresa.id)

    assert dataset.metadata["total_linhas"] == 1
    assert dataset.metadata["contagem_por_target"] == {50057: 1}
    assert dataset.metadata["treinavel"] is False


def test_dataset_builder_marks_nine_valid_lines_as_not_trainable(session):
    empresa = _empresa()
    _seed_valid_dataset(
        session,
        empresa=empresa,
        total_linhas=9,
        targets=[50057, 70001, 50057, 70001, 50057, 70001, 50057, 70001, 50057],
    )
    session.commit()

    dataset = build_dataset_treino_contrapartida(session, empresa_id=empresa.id)

    assert dataset.metadata["total_linhas"] == 9
    assert dataset.metadata["contagem_por_target"] == {50057: 5, 70001: 4}
    assert dataset.metadata["treinavel"] is False


def test_dataset_builder_marks_ten_lines_with_one_target_as_not_trainable(session):
    empresa = _empresa()
    _seed_valid_dataset(
        session,
        empresa=empresa,
        total_linhas=10,
        targets=[50057] * 10,
    )
    session.commit()

    dataset = build_dataset_treino_contrapartida(session, empresa_id=empresa.id)

    assert dataset.metadata["total_linhas"] == 10
    assert dataset.metadata["contagem_por_target"] == {50057: 10}
    assert dataset.metadata["treinavel"] is False


def test_dataset_builder_marks_ten_lines_with_two_targets_as_trainable(session):
    empresa = _empresa()
    _seed_valid_dataset(
        session,
        empresa=empresa,
        total_linhas=10,
        targets=[50057, 70001, 50057, 70001, 50057, 70001, 50057, 70001, 50057, 70001],
    )
    session.commit()

    dataset = build_dataset_treino_contrapartida(session, empresa_id=empresa.id)

    assert dataset.metadata["total_linhas"] == 10
    assert dataset.metadata["contagem_por_target"] == {50057: 5, 70001: 5}
    assert dataset.metadata["treinavel"] is True
