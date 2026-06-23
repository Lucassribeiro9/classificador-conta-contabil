from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping


@dataclass(frozen=True)
class MovimentoOperacionalValidationResult:
    """Resultado da validacao de uma linha operacional."""

    status: str
    is_valid: bool
    mensagens: list[str]
    movimento: dict[str, Any]


def validar_movimento_operacional(
    movimento: Mapping[str, Any],
    *,
    contas_por_codigo: Mapping[int, Any],
    contas_vinculadas: set[int],
    periodo_inicio: date | str | None = None,
    periodo_fim: date | str | None = None,
) -> MovimentoOperacionalValidationResult:
    """Valida uma linha operacional e deriva status inicial e campos canonicos."""

    data = _parse_date(movimento.get("data"))
    conta_financeira = _parse_account_code(movimento.get("conta_financeira"))
    historico = _clean_text(movimento.get("historico"))
    valor_original = _parse_decimal(movimento.get("valor"))
    contrapartida = _parse_account_code(movimento.get("contrapartida"))
    tipo_movimento = _clean_text(movimento.get("tipo_movimento"))

    invalid_messages = _validate_required_fields(
        data=data,
        conta_financeira=conta_financeira,
        historico=historico,
        valor_original=valor_original,
    )
    if conta_financeira is not None and not _is_classificavel(
        contas_por_codigo.get(conta_financeira)
    ):
        invalid_messages.append(
            f"Conta financeira {conta_financeira} inexistente, sintetica ou inativa."
        )
    if contrapartida is not None and not _is_classificavel(
        contas_por_codigo.get(contrapartida)
    ):
        invalid_messages.append(
            f"Contrapartida {contrapartida} inexistente, sintetica ou inativa."
        )

    if invalid_messages:
        return MovimentoOperacionalValidationResult(
            status="invalida",
            is_valid=False,
            mensagens=invalid_messages,
            movimento={},
        )

    assert data is not None
    assert conta_financeira is not None
    assert historico is not None
    assert valor_original is not None

    direcao = "entrada" if valor_original > 0 else "saida"
    warnings = _build_warnings(
        data=data,
        conta_financeira=conta_financeira,
        contrapartida=contrapartida,
        valor_original=valor_original,
        tipo_movimento=tipo_movimento,
        contas_vinculadas=contas_vinculadas,
        periodo_inicio=_parse_date(periodo_inicio),
        periodo_fim=_parse_date(periodo_fim),
    )
    status = _resolve_status(
        warnings=warnings,
        contrapartida=contrapartida,
    )

    return MovimentoOperacionalValidationResult(
        status=status,
        is_valid=True,
        mensagens=warnings,
        movimento={
            "data": data,
            "conta_financeira": conta_financeira,
            "historico": historico,
            "historico_normalizado": _normalize_historico(historico),
            "valor_original": valor_original,
            "valor_absoluto": abs(valor_original),
            "direcao": direcao,
            "tipo_movimento": tipo_movimento,
            "documento": _clean_text(movimento.get("documento")),
            "observacao": _clean_text(movimento.get("observacao")),
            "contrapartida_informada": contrapartida,
        },
    )


def _validate_required_fields(
    *,
    data: date | None,
    conta_financeira: int | None,
    historico: str | None,
    valor_original: Decimal | None,
) -> list[str]:
    """Valida os campos obrigatorios de uma linha operacional."""

    mensagens: list[str] = []
    if data is None:
        mensagens.append("Data do movimento ausente ou invalida.")
    if conta_financeira is None:
        mensagens.append("Conta financeira ausente.")
    if historico is None:
        mensagens.append("Historico ausente.")
    if valor_original is None or valor_original == 0:
        mensagens.append("Valor do movimento ausente, invalido ou zero.")
    return mensagens


def _build_warnings(
    *,
    data: date,
    conta_financeira: int,
    contrapartida: int | None,
    valor_original: Decimal,
    tipo_movimento: str | None,
    contas_vinculadas: set[int],
    periodo_inicio: date | None,
    periodo_fim: date | None,
) -> list[str]:
    """Monta warnings recuperaveis que levam a linha para revisao."""

    warnings: list[str] = []
    if periodo_inicio is not None and data < periodo_inicio:
        warnings.append("Data do movimento fora do periodo do lote.")
    elif periodo_fim is not None and data > periodo_fim:
        warnings.append("Data do movimento fora do periodo do lote.")

    if conta_financeira not in contas_vinculadas:
        warnings.append(f"Conta financeira {conta_financeira} nao vinculada a empresa.")
    if contrapartida is not None and contrapartida not in contas_vinculadas:
        warnings.append(f"Contrapartida {contrapartida} nao vinculada a empresa.")

    if tipo_movimento == "entrada" and valor_original < 0:
        warnings.append("Tipo de movimento incoerente com o sinal do valor.")
    if tipo_movimento == "saida" and valor_original > 0:
        warnings.append("Tipo de movimento incoerente com o sinal do valor.")
    if tipo_movimento in {"transferencia", "aplicacao", "resgate"}:
        if contrapartida is None:
            warnings.append(f"Tipo de movimento {tipo_movimento} exige contrapartida.")
    return warnings


def _resolve_status(
    *,
    warnings: list[str],
    contrapartida: int | None,
) -> str:
    """Resolve o status inicial da linha validada."""

    if warnings:
        return "revisao"
    if contrapartida is None:
        return "pendente"
    return "pre_classificado"


def _is_classificavel(conta: Any) -> bool:
    """Indica se uma conta existe, esta ativa e e analitica."""

    if conta is None:
        return False
    return bool(getattr(conta, "is_classificavel", False))


def _parse_account_code(value: Any) -> int | None:
    """Converte codigo de conta vindo de planilha para inteiro."""

    if _is_blank_value(value):
        return None
    try:
        return int(Decimal(str(value).strip()))
    except (InvalidOperation, ValueError):
        return None


def _parse_decimal(value: Any) -> Decimal | None:
    """Converte valor monetario para Decimal."""

    if _is_blank_value(value):
        return None
    try:
        return Decimal(str(value).strip())
    except InvalidOperation:
        return None


def _parse_date(value: Any) -> date | None:
    """Converte datas ISO, brasileiras ou celulas Excel para date."""

    if _is_blank_value(value):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    text = str(value).strip()
    for separator, order in (("-", "ymd"), ("/", "dmy")):
        if separator not in text:
            continue
        parts = text.split(separator)
        if len(parts) != 3:
            continue
        try:
            if order == "ymd":
                year, month, day = parts
            else:
                day, month, year = parts
            return date(int(year), int(month), int(day))
        except ValueError:
            return None
    return None


def _normalize_historico(historico: str) -> str:
    """Normaliza historico para comparacao e classificacao futura."""

    return " ".join(historico.strip().lower().split())


def _clean_text(value: Any) -> str | None:
    """Retorna texto sem espacos externos ou None para valores vazios."""

    if _is_blank_value(value):
        return None
    return str(value).strip()


def _is_blank_value(value: Any) -> bool:
    """Indica se um valor deve ser tratado como vazio."""

    return value is None or str(value).strip() == ""
