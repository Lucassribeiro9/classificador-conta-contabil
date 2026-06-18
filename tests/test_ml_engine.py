from datetime import date

import joblib
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


def test_train_from_dataset_contract_trains_classifier(db_session, tmp_path):
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
    engine_ml = ClassificadorContabil(db_session, model_dir=tmp_path)

    assert engine_ml.train_from_dataset(dataset) is True
    predictions = engine_ml._predict_features(
        ["pagamento fornecedor aluguel origem_10046 direcao_credito"]
    )

    assert predictions[0]["conta_contrapartida_predita"] in {50057, 70001}
    assert predictions[0]["conta_contabil_predita"] == predictions[0][
        "conta_contrapartida_predita"
    ]


def test_train_from_dataset_persists_multinomial_model_for_company(db_session, tmp_path):
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
            "empresa_id": 42,
            "total_linhas": 10,
            "total_descartes": 0,
            "contagem_por_target": {50057: 5, 70001: 5},
            "treinavel": True,
        },
    )
    engine_ml = ClassificadorContabil(db_session, model_dir=tmp_path)

    assert engine_ml.train_from_dataset(dataset) is True

    model_path = tmp_path / "empresa_42" / "model_.joblib"
    assert model_path.exists()
    persisted_model = joblib.load(model_path)
    assert persisted_model.predict(
        ["pagamento fornecedor aluguel origem_10046 direcao_credito"]
    )[0] in {50057, 70001}


def test_train_from_dataset_recuses_insufficient_dataset_without_model_file(
    db_session, tmp_path
):
    dataset = DatasetTreinoContrapartida(
        linhas=[
            {
                "features": f"pagamento fornecedor {i} origem_10046 direcao_credito",
                "target_conta_contrapartida": 50057,
            }
            for i in range(9)
        ],
        metadata={
            "empresa_id": 43,
            "total_linhas": 9,
            "total_descartes": 0,
            "contagem_por_target": {50057: 9},
            "treinavel": False,
        },
    )
    engine_ml = ClassificadorContabil(db_session, model_dir=tmp_path)

    assert engine_ml.train_from_dataset(dataset) is False
    assert not (tmp_path / "empresa_43" / "model_.joblib").exists()


def test_train_from_dataset_keeps_model_files_isolated_by_company(db_session, tmp_path):
    def make_dataset(empresa_id: int, first_target: int, second_target: int):
        return DatasetTreinoContrapartida(
            linhas=[
                {
                    "features": f"pagamento empresa {empresa_id} {i} origem_10046 direcao_credito",
                    "target_conta_contrapartida": first_target,
                }
                for i in range(5)
            ]
            + [
                {
                    "features": f"recebimento empresa {empresa_id} {i} origem_10046 direcao_debito",
                    "target_conta_contrapartida": second_target,
                }
                for i in range(5)
            ],
            metadata={
                "empresa_id": empresa_id,
                "total_linhas": 10,
                "total_descartes": 0,
                "contagem_por_target": {first_target: 5, second_target: 5},
                "treinavel": True,
            },
        )

    engine_ml = ClassificadorContabil(db_session, model_dir=tmp_path)

    assert engine_ml.train_from_dataset(make_dataset(51, 50057, 70001)) is True
    assert engine_ml.train_from_dataset(make_dataset(52, 80001, 90001)) is True

    company_51_model = tmp_path / "empresa_51" / "model_.joblib"
    company_52_model = tmp_path / "empresa_52" / "model_.joblib"
    assert company_51_model.exists()
    assert company_52_model.exists()
    assert company_51_model != company_52_model
    assert set(joblib.load(company_51_model).classes_) == {50057, 70001}
    assert set(joblib.load(company_52_model).classes_) == {80001, 90001}


def test_train_from_dataset_preserves_previous_model_when_persistence_fails(
    db_session, tmp_path, monkeypatch
):
    def make_dataset(first_token: str, first_target: int, second_target: int):
        return DatasetTreinoContrapartida(
            linhas=[
                {
                    "features": f"{first_token} {i} origem_10046 direcao_credito",
                    "target_conta_contrapartida": first_target,
                }
                for i in range(5)
            ]
            + [
                {
                    "features": f"recebimento cliente {i} origem_10046 direcao_debito",
                    "target_conta_contrapartida": second_target,
                }
                for i in range(5)
            ],
            metadata={
                "empresa_id": 61,
                "total_linhas": 10,
                "total_descartes": 0,
                "contagem_por_target": {first_target: 5, second_target: 5},
                "treinavel": True,
            },
        )

    engine_ml = ClassificadorContabil(db_session, model_dir=tmp_path)
    assert engine_ml.train_from_dataset(
        make_dataset("pagamento fornecedor", 50057, 70001)
    )

    model_path = tmp_path / "empresa_61" / "model_.joblib"
    previous_classes = set(joblib.load(model_path).classes_)

    def fail_dump(model, filename):
        filename.write_bytes(b"modelo parcial invalido")
        raise RuntimeError("falha simulada ao salvar modelo")

    monkeypatch.setattr("core.ml_engine.joblib.dump", fail_dump)

    with pytest.raises(RuntimeError, match="falha simulada"):
        engine_ml.train_from_dataset(make_dataset("pagamento imposto", 80001, 90001))

    assert set(joblib.load(model_path).classes_) == previous_classes


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
