from datetime import date
from decimal import Decimal

from core.models import ContaContabil
from core.movimentos_operacionais_validator import validar_movimento_operacional


def _conta(codigo: int, *, tipo: str = "A", is_active: bool = True):
    """Cria uma conta contabil minima para validar movimentos."""

    return ContaContabil(
        codigo=codigo,
        classificacao=f"1.1.{codigo}",
        nome=f"CONTA {codigo}",
        tipo=tipo,
        grau=6,
        is_active=is_active,
    )


def _movimento(**overrides):
    """Retorna um movimento bruto valido por padrao."""

    movimento = {
        "data": "2025-01-10",
        "conta_financeira": 10046,
        "historico": "RECEBTO.DUPLICATAS",
        "valor": 3660.15,
        "contrapartida": 10722,
        "tipo_movimento": "entrada",
        "documento": "OFX-0001",
        "observacao": "Contrapartida conhecida pelo contador",
    }
    movimento.update(overrides)
    return movimento


def test_validar_movimento_com_contrapartida_valida_pre_classifica():
    """Deve pre-classificar movimento com contas validas e vinculadas."""

    result = validar_movimento_operacional(
        _movimento(),
        contas_por_codigo={10046: _conta(10046), 10722: _conta(10722)},
        contas_vinculadas={10046, 10722},
        periodo_inicio=date(2025, 1, 1),
        periodo_fim=date(2025, 1, 31),
    )

    assert result.status == "pre_classificado"
    assert result.is_valid is True
    assert result.mensagens == []
    assert result.movimento["data"] == date(2025, 1, 10)
    assert result.movimento["valor_original"] == Decimal("3660.15")
    assert result.movimento["valor_absoluto"] == Decimal("3660.15")
    assert result.movimento["direcao"] == "debito"
    assert result.movimento["historico_normalizado"] == "recebto.duplicatas"
    assert result.movimento["contrapartida_informada"] == 10722


def test_validar_movimento_sem_contrapartida_fica_pendente():
    """Deve deixar pendente movimento valido sem contrapartida."""

    result = validar_movimento_operacional(
        _movimento(contrapartida=None, valor=-1200, tipo_movimento="saida"),
        contas_por_codigo={10046: _conta(10046)},
        contas_vinculadas={10046},
        periodo_inicio=date(2025, 1, 1),
        periodo_fim=date(2025, 1, 31),
    )

    assert result.status == "pendente"
    assert result.is_valid is True
    assert result.mensagens == []
    assert result.movimento["valor_original"] == Decimal("-1200")
    assert result.movimento["valor_absoluto"] == Decimal("1200")
    assert result.movimento["direcao"] == "credito"
    assert result.movimento["contrapartida_informada"] is None


def test_validar_movimento_invalida_valor_zero_ou_vazio():
    """Deve invalidar movimento sem valor contabil util."""

    result = validar_movimento_operacional(
        _movimento(valor=0),
        contas_por_codigo={10046: _conta(10046), 10722: _conta(10722)},
        contas_vinculadas={10046, 10722},
    )

    assert result.status == "invalida"
    assert result.is_valid is False
    assert result.mensagens == ["Valor do movimento ausente, invalido ou zero."]
    assert result.movimento == {}


def test_validar_movimento_invalida_campos_obrigatorios_ausentes():
    """Deve invalidar movimento sem data, conta financeira ou historico."""

    result = validar_movimento_operacional(
        _movimento(data="31/02/2025", conta_financeira=None, historico=""),
        contas_por_codigo={10722: _conta(10722)},
        contas_vinculadas={10722},
    )

    assert result.status == "invalida"
    assert result.is_valid is False
    assert result.mensagens == [
        "Data do movimento ausente ou invalida.",
        "Conta financeira ausente.",
        "Historico ausente.",
    ]
    assert result.movimento == {}


def test_validar_movimento_invalida_conta_inexistente_sintetica_ou_inativa():
    """Deve invalidar conta financeira que nao pode receber lancamento."""

    for conta in (None, _conta(10046, tipo="S"), _conta(10046, is_active=False)):
        contas = {10046: conta, 10722: _conta(10722)} if conta else {10722: _conta(10722)}

        result = validar_movimento_operacional(
            _movimento(),
            contas_por_codigo=contas,
            contas_vinculadas={10046, 10722},
        )

        assert result.status == "invalida"
        assert result.is_valid is False
        assert result.mensagens == [
            "Conta financeira 10046 inexistente, sintetica ou inativa."
        ]


def test_validar_movimento_invalida_contrapartida_inexistente_sintetica_ou_inativa():
    """Deve invalidar contrapartida preenchida que nao pode receber lancamento."""

    for conta in (None, _conta(10722, tipo="S"), _conta(10722, is_active=False)):
        contas = {10046: _conta(10046)}
        if conta:
            contas[10722] = conta

        result = validar_movimento_operacional(
            _movimento(),
            contas_por_codigo=contas,
            contas_vinculadas={10046, 10722},
        )

        assert result.status == "invalida"
        assert result.is_valid is False
        assert result.mensagens == [
            "Contrapartida 10722 inexistente, sintetica ou inativa."
        ]


def test_validar_movimento_conta_valida_nao_vinculada_fica_em_revisao():
    """Deve revisar movimento quando conta valida nao esta vinculada a empresa."""

    result = validar_movimento_operacional(
        _movimento(),
        contas_por_codigo={10046: _conta(10046), 10722: _conta(10722)},
        contas_vinculadas={10046},
    )

    assert result.status == "revisao"
    assert result.is_valid is True
    assert result.mensagens == ["Contrapartida 10722 nao vinculada a empresa."]


def test_validar_transferencia_aplicacao_ou_resgate_sem_contrapartida_revisao():
    """Deve revisar movimentos especiais sem contrapartida informada."""

    for tipo_movimento in ("transferencia", "aplicacao", "resgate"):
        result = validar_movimento_operacional(
            _movimento(contrapartida=None, tipo_movimento=tipo_movimento),
            contas_por_codigo={10046: _conta(10046)},
            contas_vinculadas={10046},
        )

        assert result.status == "revisao"
        assert result.is_valid is True
        assert result.mensagens == [
            f"Tipo de movimento {tipo_movimento} exige contrapartida."
        ]
