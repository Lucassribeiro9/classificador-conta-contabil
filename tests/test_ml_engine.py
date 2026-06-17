from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.database import Base
from core.dataset_builder import DatasetTreinoContrapartida
from core.ml_engine import ClassificadorContabil
from core.models import Empresa, Transacao


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def empresa(db_session):
    item = Empresa(
        nome_empresa="Teste Contabil LTDA",
        cnpj_cpf="12345678000199",
        api_key="sk_test",
        cod_dominio=1,
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return item


def _seed_treino(db_session, empresa_id: int):
    dados = [
        ("PAGAMENTO SALARIO", 101, 1),
        ("SALARIO FUNCIONARIOS", 101, 1),
        ("FOLHA DE PAGAMENTO", 101, 1),
        ("VENDA MERCADORIA", 301, 33),
        ("RECEBIMENTO CLIENTE", 301, 33),
        ("VENDA PRODUTOS", 301, 33),
        ("GUIA IMPOSTO", 202, 237),
        ("IMPOSTO SOBRE FATURAMENTO", 202, 237),
        ("PAGTO SIMPLES NACIONAL", 202, 237),
        ("PAGAMENTO BONUS SALARIAL", 101, 1),
        ("VENDA NF 123", 301, 33),
        ("IMPOSTO RETIDO", 202, 237),
    ]
    for historico, conta, banco in dados:
        db_session.add(
            Transacao(
                empresa_id=empresa_id,
                data=date.today(),
                cod_banco=banco,
                historico=historico,
                valor=100.0,
                conta_contabil=conta,
            )
        )
    db_session.commit()


def test_train_for_company_sem_dados_lanca_erro(db_session, empresa):
    engine_ml = ClassificadorContabil(db_session)
    with pytest.raises(ValueError):
        engine_ml.train_for_company(empresa.id)


def test_train_for_company_com_poucos_dados_retorna_false(db_session, empresa):
    for i in range(5):
        db_session.add(
            Transacao(
                empresa_id=empresa.id,
                data=date.today(),
                cod_banco=1,
                historico=f"PAGAMENTO TESTE {i}",
                valor=100.0,
                conta_contabil=101,
            )
        )
    db_session.commit()

    engine_ml = ClassificadorContabil(db_session)
    assert engine_ml.train_for_company(empresa.id) is False


def test_train_from_dataset_contract_trains_classifier(db_session):
    dataset = DatasetTreinoContrapartida(
        linhas=[
            {
                "features": f"pagamento fornecedor {i} origem_10046 direcao_credito",
                "target_conta_contrapartida": 50057,
            }
            for i in range(5)
        ]
        + [
            {
                "features": f"recebimento cliente {i} origem_10046 direcao_debito",
                "target_conta_contrapartida": 70001,
            }
            for i in range(5)
        ],
        metadata={
            "empresa_id": 1,
            "total_linhas": 10,
            "total_descartes": 0,
            "contagem_por_target": {50057: 5, 70001: 5},
            "treinavel": True,
        },
    )
    engine_ml = ClassificadorContabil(db_session)

    assert engine_ml.train_from_dataset(dataset) is True
    predictions = engine_ml._predict_features(
        ["pagamento fornecedor aluguel origem_10046 direcao_credito"]
    )

    assert predictions[0]["conta_contrapartida_predita"] in {50057, 70001}
    assert predictions[0]["conta_contabil_predita"] == predictions[0][
        "conta_contrapartida_predita"
    ]


def test_predict_inputs_retorna_estrutura_esperada(db_session, empresa):
    _seed_treino(db_session, empresa.id)
    engine_ml = ClassificadorContabil(db_session)
    assert engine_ml.train_for_company(empresa.id) is True

    result = engine_ml.predict_inputs(
        [
            {"historico": "PAGAMENTO SALARIO JOAO", "cod_banco": 1},
            {"historico": "VENDA ECOMMERCE", "cod_banco": 33},
        ]
    )

    assert len(result) == 2
    assert "conta_contabil_predita" in result[0]
    assert "confidence" in result[0]
    assert "needs_review" in result[0]
    assert result[0]["historico"] == "PAGAMENTO SALARIO JOAO"
    assert result[1]["cod_banco"] == 33


def test_classify_transactions_atualiza_transacoes(db_session, empresa):
    _seed_treino(db_session, empresa.id)
    pendente_1 = Transacao(
        empresa_id=empresa.id,
        data=date.today(),
        cod_banco=1,
        historico="PAGTO SALARIO FEVEREIRO",
        valor=1500.0,
    )
    pendente_2 = Transacao(
        empresa_id=empresa.id,
        data=date.today(),
        cod_banco=33,
        historico="VENDA LOJA VIRTUAL",
        valor=900.0,
    )
    db_session.add_all([pendente_1, pendente_2])
    db_session.commit()
    db_session.refresh(pendente_1)
    db_session.refresh(pendente_2)

    engine_ml = ClassificadorContabil(db_session)
    assert engine_ml.train_for_company(empresa.id) is True

    classificados = engine_ml.classify_transactions(
        empresa.id, [pendente_1.id, pendente_2.id]
    )

    assert len(classificados) == 2
    for item in classificados:
        assert item.conta_contabil is not None
        assert item.confidence is not None
        assert isinstance(item.needs_review, bool)
