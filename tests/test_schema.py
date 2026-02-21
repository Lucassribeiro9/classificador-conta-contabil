from datetime import date

import pytest
from pydantic import ValidationError

from api.schemas import EmpresaCreate, TransacaoCreate


def test_empresa_create_valida():
    empresa = EmpresaCreate(
        nome_empresa="Empresa Teste",
        cnpj_cpf="12.345.678/0001-90",
        cod_dominio=200,
    )
    assert empresa.nome_empresa == "Empresa Teste"
    assert empresa.cnpj_cpf == "12.345.678/0001-90"
    assert empresa.cod_dominio == 200
    assert empresa.is_active is True


def test_empresa_create_sem_cod_dominio_gera_erro():
    with pytest.raises(ValidationError):
        EmpresaCreate(
            nome_empresa="Empresa Inválida",
            cnpj_cpf="12.345.678/0001-90",
        )


def test_transacao_create_valida_com_opcionais():
    transacao = TransacaoCreate(
        data=date(2026, 1, 28),
        cod_banco=341,
        historico="Compra de material",
        valor=150.50,
        conta_contabil=1234,
        empresa_id=1,
    )
    assert transacao.historico == "Compra de material"
    assert transacao.cod_banco == 341
    assert transacao.conta_contabil == 1234


def test_transacao_create_valida_sem_opcionais():
    transacao = TransacaoCreate(
        data=date(2026, 1, 28),
        historico="Compra de material",
        valor=150.50,
        empresa_id=1,
    )
    assert transacao.cod_banco is None
    assert transacao.conta_contabil is None


def test_transacao_create_campos_com_tipos_invalidos():
    with pytest.raises(ValidationError):
        TransacaoCreate(
            data="hoje",
            historico="Erro de tipo",
            valor="caro",
            empresa_id=1,
        )
