"""Contratos do processamento em blocos da importação do Razão."""

from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.database import Base
from core.models import (
    ContaContabil,
    Empresa,
    LancamentoRazaoNormalizado,
    LoteImportacaoRazao,
    Usuario,
    WarningImportacaoRazao,
)
from core.razao_importer import import_razao


def _session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine)()


def _seed(session):
    empresa = Empresa(
        nome_empresa="Empresa sintética",
        cnpj_cpf="55666777000188",
        api_key="synthetic",
        cod_dominio=7701,
    )
    usuario = Usuario(
        nome="Operador sintético",
        login="operador-blocos",
        email="operador-blocos@example.com",
        senha_hash="synthetic",
        papel="operador",
    )
    contas = [
        ContaContabil(
            codigo=codigo,
            classificacao=f"1.1.{codigo}",
            nome=f"CONTA {codigo}",
            tipo="A",
            grau=6,
        )
        for codigo in (10046, 20001)
    ]
    session.add_all([empresa, usuario, *contas])
    session.flush()
    return empresa, usuario


def _parsed_line(numero, *, contraparte="20001"):
    return {
        "bloco_id": "bloco:1",
        "data": "2026-01-02",
        "numero": str(numero),
        "historico": f"Lançamento {numero}",
        "conta_origem": "10046",
        "contrapartida": contraparte,
        "debito": "10.00",
        "credito": None,
    }


def test_import_razao_preloads_catalog_and_persists_blocks_and_normalized_warnings(
    tmp_path, monkeypatch
):
    """Consultas não crescem por linha e warnings novos não duplicam o metadata."""
    from core import razao_importer

    engine, session = _session()
    empresa, usuario = _seed(session)
    path = tmp_path / "synthetic.xlsx"
    path.write_bytes(b"synthetic")
    parsed = [_parsed_line(1), _parsed_line(2), _parsed_line(3, contraparte="99999")]
    monkeypatch.setattr(razao_importer, "_parse_lancamentos_and_validate_company", lambda *_: parsed)
    statements = []
    event.listen(engine, "before_cursor_execute", lambda *args: statements.append(args[2]))

    result = import_razao(
        session,
        path,
        empresa_id=empresa.id,
        usuario_id=usuario.id,
        original_filename="synthetic.xlsx",
        block_size=2,
    )

    assert result.total_importadas == 2
    assert result.total_invalidas == 1
    lote = session.query(LoteImportacaoRazao).one()
    assert lote.linhas_processadas == 3
    assert lote.warnings_total == 2
    assert lote.warnings_metadata == {
        "totals_by_code": {"saldo_ausente": 1, "conta_nao_encontrada": 1}
    }
    persisted_warnings = session.query(WarningImportacaoRazao).order_by(
        WarningImportacaoRazao.linha
    ).all()
    assert [(warning.linha, warning.codigo) for warning in persisted_warnings] == [
        (1, "saldo_ausente"),
        (3, "conta_nao_encontrada"),
    ]
    assert session.query(LancamentoRazaoNormalizado).count() == 2
    catalog_queries = [sql for sql in statements if "FROM contas_contabeis" in sql]
    account_link_queries = [sql for sql in statements if "FROM empresa_contas_contabeis" in sql]
    assert len(catalog_queries) == 1
    assert len(account_link_queries) == 1

    session.close()
    engine.dispose()


def test_block_boundaries_preserve_sequences_results_and_single_transaction(
    tmp_path, monkeypatch
):
    """Estado contábil atravessa blocos e o importador não confirma a transação."""
    from core import razao_importer

    engine, session = _session()
    empresa, usuario = _seed(session)
    path = tmp_path / "synthetic-boundary.xlsx"
    path.write_bytes(b"synthetic-boundary")
    parsed = [
        {
            **_parsed_line(1),
            "saldo_anterior": {
                "valor_original": "100,00D",
                "valor_decimal": 100,
                "natureza": "D",
            },
            "saldo": {
                "valor_original": "10,00D",
                "valor_decimal": 10,
                "natureza": "D",
            },
            "saldo_exercicio": {
                "valor_original": "110,00D",
                "valor_decimal": 110,
                "natureza": "D",
            },
        },
        {
            **_parsed_line(2),
            "saldo": {
                "valor_original": "20,00D",
                "valor_decimal": 20,
                "natureza": "D",
            },
            "saldo_exercicio": {
                "valor_original": "120,00D",
                "valor_decimal": 120,
                "natureza": "D",
            },
        },
    ]
    monkeypatch.setattr(razao_importer, "_parse_lancamentos_and_validate_company", lambda *_: parsed)
    commits = []
    event.listen(session, "after_commit", lambda *_: commits.append(True))

    result = import_razao(
        session,
        path,
        empresa_id=empresa.id,
        usuario_id=usuario.id,
        original_filename="synthetic-boundary.xlsx",
        block_size=1,
    )

    assert commits == []
    assert result.status == "completed"
    assert result.total_importadas == 2
    assert result.warnings == []
    closing = session.query(razao_importer.FechamentoRazaoMensal).one()
    assert str(closing.saldo_calculado_decimal) == "120.00"
    assert str(closing.saldo_observado_decimal) == "120.00"
    session.rollback()
    assert session.query(LoteImportacaoRazao).count() == 0

    session.close()
    engine.dispose()


def test_warning_preview_is_bounded_while_all_warnings_are_persisted(
    tmp_path, monkeypatch
):
    """Arquivos inválidos grandes não mantêm todos os warnings em memória."""
    from core import razao_importer

    engine, session = _session()
    empresa, usuario = _seed(session)
    path = tmp_path / "synthetic-invalid.xlsx"
    path.write_bytes(b"synthetic-invalid")
    parsed = [_parsed_line(index, contraparte="") for index in range(1, 106)]
    monkeypatch.setattr(
        razao_importer,
        "_parse_lancamentos_and_validate_company",
        lambda *_: parsed,
    )

    result = import_razao(
        session,
        path,
        empresa_id=empresa.id,
        usuario_id=usuario.id,
        original_filename="synthetic-invalid.xlsx",
        block_size=10,
    )

    lote = session.query(LoteImportacaoRazao).one()
    assert result.status == "failed"
    assert len(result.warnings) == 100
    assert lote.warnings_total == 105
    assert lote.warnings_metadata == {
        "totals_by_code": {"contrapartida_ausente": 105}
    }
    assert session.query(WarningImportacaoRazao).count() == 105

    session.close()
    engine.dispose()


def test_each_validation_message_is_persisted_as_a_normalized_warning(
    tmp_path, monkeypatch
):
    """Uma linha pode produzir avisos distintos para origem e contrapartida."""
    from core import razao_importer

    engine, session = _session()
    empresa, usuario = _seed(session)
    path = tmp_path / "synthetic-two-missing-accounts.xlsx"
    path.write_bytes(b"synthetic-two-missing-accounts")
    parsed = [
        {
            **_parsed_line(1, contraparte="99998"),
            "conta_origem": "99997",
        }
    ]
    monkeypatch.setattr(
        razao_importer,
        "_parse_lancamentos_and_validate_company",
        lambda *_: parsed,
    )

    result = import_razao(
        session,
        path,
        empresa_id=empresa.id,
        usuario_id=usuario.id,
        original_filename="synthetic-two-missing-accounts.xlsx",
        block_size=1,
    )

    lote = session.query(LoteImportacaoRazao).one()
    assert len(result.warnings) == 1
    assert len(result.warnings[0]["warnings"]) == 2
    assert lote.warnings_total == 2
    assert lote.warnings_metadata == {
        "totals_by_code": {"conta_nao_encontrada": 2}
    }
    assert session.query(WarningImportacaoRazao).count() == 2

    session.close()
    engine.dispose()
