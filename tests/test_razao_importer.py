from datetime import date
from decimal import Decimal

import pytest
from openpyxl import Workbook
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.database import Base
from core.models import (
    ContaContabil,
    Empresa,
    LancamentoRazaoNormalizado,
    LoteImportacaoRazao,
    Usuario,
)
from core.razao_importer import import_razao


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


def _write_workbook(path, rows):
    workbook = Workbook()
    sheet = workbook.active
    for row in rows:
        sheet.append(row)
    workbook.save(path)
    workbook.close()


def _empresa() -> Empresa:
    return Empresa(
        nome_empresa="Empresa Razao LTDA",
        cnpj_cpf="55666777000188",
        api_key="api-key-razao",
        cod_dominio=7701,
    )


def _usuario() -> Usuario:
    return Usuario(
        nome="Operador Razao",
        login="operador.razao",
        email="operador.razao@example.com",
        senha_hash="$argon2id$v=19$hash-de-teste",
        papel="operador",
    )


def _conta(codigo: int) -> ContaContabil:
    return ContaContabil(
        codigo=codigo,
        classificacao=f"1.1.{codigo}",
        nome=f"CONTA {codigo}",
        tipo="A",
        grau=6,
    )


def test_import_razao_persists_valid_lines_and_completes_lote(session, tmp_path):
    empresa = _empresa()
    usuario = _usuario()
    session.add_all([empresa, usuario, _conta(10046), _conta(20001)])
    session.flush()
    xlsx_path = tmp_path / "razao-valido.xlsx"
    _write_workbook(
        xlsx_path,
        [
            ["Conta:", "10046", "BCO. SANTANDER"],
            ["Data", "Numero", "Historico", "Contrapartida", "Debito", "Credito"],
            ["2026-01-02", "42", "Pagamento fornecedor", "20001", 250.75, None],
        ],
    )

    result = import_razao(
        session,
        xlsx_path,
        empresa_id=empresa.id,
        usuario_id=usuario.id,
        original_filename="razao-valido.xlsx",
    )

    lote = session.query(LoteImportacaoRazao).one()
    lancamento = session.query(LancamentoRazaoNormalizado).one()
    assert result.lote_id == lote.id
    assert result.status == "completed"
    assert lote.status == "completed"
    assert lote.total_linhas == 1
    assert lote.total_importadas == 1
    assert lote.total_invalidas == 0
    assert lote.warnings_metadata == {"warnings": []}
    assert lote.empresa_id == empresa.id
    assert lote.usuario_id == usuario.id
    assert lote.original_filename == "razao-valido.xlsx"
    assert lote.file_hash.startswith("sha256:")
    assert lancamento.lote_id == lote.id
    assert lancamento.empresa_id == empresa.id
    assert lancamento.numero_lancamento == "42"
    assert lancamento.data == date(2026, 1, 2)
    assert lancamento.conta_origem == 10046
    assert lancamento.conta_contrapartida == 20001
    assert lancamento.conta_debito == 10046
    assert lancamento.conta_credito == 20001
    assert lancamento.direcao == "debito"
    assert lancamento.historico == "Pagamento fornecedor"
    assert lancamento.historico_normalizado == "pagamento fornecedor"
    assert lancamento.valor == Decimal("250.75")


def test_import_razao_persists_valid_lines_and_records_warnings_for_invalid_ones(
    session,
    tmp_path,
):
    empresa = _empresa()
    usuario = _usuario()
    session.add_all([empresa, usuario, _conta(10046), _conta(20001)])
    session.flush()
    xlsx_path = tmp_path / "razao-parcial.xlsx"
    _write_workbook(
        xlsx_path,
        [
            ["Conta:", "10046", "BCO. SANTANDER"],
            ["Data", "Numero", "Historico", "Contrapartida", "Debito", "Credito"],
            ["2026-01-02", "42", "Pagamento fornecedor", "20001", 250.75, None],
            ["2026-01-03", "43", "Conta ausente", "99999", 10.00, None],
        ],
    )

    result = import_razao(
        session,
        xlsx_path,
        empresa_id=empresa.id,
        usuario_id=usuario.id,
        original_filename="razao-parcial.xlsx",
    )

    lote = session.query(LoteImportacaoRazao).one()
    assert result.status == "completed_with_warnings"
    assert lote.status == "completed_with_warnings"
    assert lote.total_linhas == 2
    assert lote.total_importadas == 1
    assert lote.total_invalidas == 1
    assert lote.warnings_metadata == {
        "warnings": [
            {
                "linha": 2,
                "warnings": [
                    "Conta de contrapartida 99999 nao encontrada no catalogo."
                ],
            }
        ]
    }
    assert session.query(LancamentoRazaoNormalizado).count() == 1


def test_import_razao_records_warning_for_line_without_counterpart(session, tmp_path):
    empresa = _empresa()
    usuario = _usuario()
    session.add_all([empresa, usuario, _conta(10046)])
    session.flush()
    xlsx_path = tmp_path / "razao-sem-contrapartida.xlsx"
    _write_workbook(
        xlsx_path,
        [
            ["Conta:", "10046", "BCO. SANTANDER"],
            ["Data", "Numero", "Historico", "Contrapartida", "Debito", "Credito"],
            ["2026-01-02", "42", "Sem contrapartida", None, 250.75, None],
        ],
    )

    result = import_razao(
        session,
        xlsx_path,
        empresa_id=empresa.id,
        usuario_id=usuario.id,
        original_filename="razao-sem-contrapartida.xlsx",
    )

    lote = session.query(LoteImportacaoRazao).one()
    assert result.status == "failed"
    assert lote.total_linhas == 1
    assert lote.total_importadas == 0
    assert lote.total_invalidas == 1
    assert lote.warnings_metadata == {
        "warnings": [
            {
                "linha": 1,
                "warnings": ["Linha do razao sem contrapartida valida."],
            }
        ]
    }
    assert session.query(LancamentoRazaoNormalizado).count() == 0


def test_import_razao_marks_lote_as_failed_when_no_valid_lines(session, tmp_path):
    empresa = _empresa()
    usuario = _usuario()
    session.add_all([empresa, usuario, _conta(10046)])
    session.flush()
    xlsx_path = tmp_path / "razao-sem-validas.xlsx"
    _write_workbook(
        xlsx_path,
        [
            ["Conta:", "10046", "BCO. SANTANDER"],
            ["Data", "Numero", "Historico", "Contrapartida", "Debito", "Credito"],
            ["2026-01-02", "42", "Conta ausente", "99999", 250.75, None],
            ["2026-01-03", "43", "Outra conta ausente", "88888", 10.00, None],
        ],
    )

    result = import_razao(
        session,
        xlsx_path,
        empresa_id=empresa.id,
        usuario_id=usuario.id,
        original_filename="razao-sem-validas.xlsx",
    )

    lote = session.query(LoteImportacaoRazao).one()
    assert result.status == "failed"
    assert lote.status == "failed"
    assert lote.total_linhas == 2
    assert lote.total_importadas == 0
    assert lote.total_invalidas == 2
    assert len(lote.warnings_metadata["warnings"]) == 2
    assert session.query(LancamentoRazaoNormalizado).count() == 0
