from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from openpyxl import Workbook
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.database import Base
from core.models import (
    ContaContabil,
    EmpresaContaContabil,
    Empresa,
    LancamentoRazaoNormalizado,
    LoteImportacaoRazao,
    Usuario,
)
from core.razao_importer import RazaoImportError, import_razao


FIXTURES_DIR = Path(__file__).parent / "fixtures"


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


def test_import_razao_fixture_tabular_valida_completa_lote(session):
    empresa = _empresa()
    usuario = _usuario()
    session.add_all(
        [
            empresa,
            usuario,
            _conta(10046),
            _conta(20102),
            _conta(30102),
            _conta(20104),
        ]
    )
    session.flush()

    result = import_razao(
        session,
        FIXTURES_DIR / "razao_lote_valido.xlsx",
        empresa_id=empresa.id,
        usuario_id=usuario.id,
        original_filename="razao_lote_valido.xlsx",
    )

    lote = session.query(LoteImportacaoRazao).one()
    lancamentos = (
        session.query(LancamentoRazaoNormalizado)
        .order_by(LancamentoRazaoNormalizado.numero_lancamento)
        .all()
    )
    assert result.status == "completed"
    assert result.total_linhas == 3
    assert result.total_importadas == 3
    assert result.total_invalidas == 0
    assert result.warnings == []
    assert lote.warnings_metadata == {"warnings": []}
    assert [l.numero_lancamento for l in lancamentos] == ["9001", "9002", "9003"]
    assert [l.direcao for l in lancamentos] == ["credito", "debito", "credito"]
    assert session.query(EmpresaContaContabil).count() == 4


def test_import_razao_fixture_tabular_com_warnings_importa_parcialmente(session):
    empresa = _empresa()
    usuario = _usuario()
    session.add_all([empresa, usuario, _conta(10046), _conta(20101)])
    session.flush()

    result = import_razao(
        session,
        FIXTURES_DIR / "razao_lote_com_warnings.xlsx",
        empresa_id=empresa.id,
        usuario_id=usuario.id,
        original_filename="razao_lote_com_warnings.xlsx",
    )

    lote = session.query(LoteImportacaoRazao).one()
    lancamento = session.query(LancamentoRazaoNormalizado).one()
    assert result.status == "completed_with_warnings"
    assert result.total_linhas == 3
    assert result.total_importadas == 1
    assert result.total_invalidas == 2
    assert result.warnings == [
        {
            "linha": 2,
            "warnings": ["Linha do razao sem contrapartida valida."],
        },
        {
            "linha": 3,
            "warnings": [
                "Conta de contrapartida 99999 nao encontrada no catalogo."
            ],
        },
    ]
    assert lote.status == "completed_with_warnings"
    assert lote.warnings_metadata == {"warnings": result.warnings}
    assert lancamento.numero_lancamento == "9101"
    assert lancamento.conta_origem == 10046
    assert lancamento.conta_contrapartida == 20101


def test_import_razao_records_warning_for_invalid_date_format(session, tmp_path):
    empresa = _empresa()
    usuario = _usuario()
    session.add_all([empresa, usuario, _conta(10046), _conta(20001)])
    session.flush()
    xlsx_path = tmp_path / "razao-data-invalida.xlsx"
    _write_workbook(
        xlsx_path,
        [
            ["Conta:", "10046", "BCO. SANTANDER"],
            ["Data", "Numero", "Historico", "Contrapartida", "Debito", "Credito"],
            ["2026-01-02", "42", "Pagamento fornecedor", "20001", 250.75, None],
            ["31/02/2026", "43", "Data invalida", "20001", 10.00, None],
        ],
    )

    result = import_razao(
        session,
        xlsx_path,
        empresa_id=empresa.id,
        usuario_id=usuario.id,
        original_filename="razao-data-invalida.xlsx",
    )

    assert result.status == "completed_with_warnings"
    assert result.total_linhas == 2
    assert result.total_importadas == 1
    assert result.total_invalidas == 1
    assert result.warnings == [
        {
            "linha": 2,
            "warnings": ["Data do lancamento invalida."],
        }
    ]
    assert session.query(LancamentoRazaoNormalizado).count() == 1


def test_import_razao_records_warning_for_invalid_amount_format(session, tmp_path):
    empresa = _empresa()
    usuario = _usuario()
    session.add_all([empresa, usuario, _conta(10046), _conta(20001)])
    session.flush()
    xlsx_path = tmp_path / "razao-valor-invalido.xlsx"
    _write_workbook(
        xlsx_path,
        [
            ["Conta:", "10046", "BCO. SANTANDER"],
            ["Data", "Numero", "Historico", "Contrapartida", "Debito", "Credito"],
            ["2026-01-02", "42", "Pagamento fornecedor", "20001", 250.75, None],
            ["2026-01-03", "43", "Valor invalido", "20001", "abc", None],
        ],
    )

    result = import_razao(
        session,
        xlsx_path,
        empresa_id=empresa.id,
        usuario_id=usuario.id,
        original_filename="razao-valor-invalido.xlsx",
    )

    assert result.status == "completed_with_warnings"
    assert result.total_linhas == 2
    assert result.total_importadas == 1
    assert result.total_invalidas == 1
    assert result.warnings == [
        {
            "linha": 2,
            "warnings": ["Valor do lancamento invalido."],
        }
    ]
    assert session.query(LancamentoRazaoNormalizado).count() == 1


def test_import_razao_accepts_integer_like_account_codes_with_decimal_suffix(
    session,
    tmp_path,
):
    empresa = _empresa()
    usuario = _usuario()
    session.add_all([empresa, usuario, _conta(10046), _conta(20001)])
    session.flush()
    xlsx_path = tmp_path / "razao-contas-decimais.xlsx"
    _write_workbook(
        xlsx_path,
        [
            ["Conta:", "10046.0", "BCO. SANTANDER"],
            ["Data", "Numero", "Historico", "Contrapartida", "Debito", "Credito"],
            ["2026-01-02", "42.0", "Pagamento fornecedor", "20001.0", 250.75, None],
        ],
    )

    result = import_razao(
        session,
        xlsx_path,
        empresa_id=empresa.id,
        usuario_id=usuario.id,
        original_filename="razao-contas-decimais.xlsx",
    )

    lancamento = session.query(LancamentoRazaoNormalizado).one()
    assert result.status == "completed"
    assert result.total_importadas == 1
    assert result.warnings == []
    assert lancamento.numero_lancamento == "42"
    assert lancamento.conta_origem == 10046
    assert lancamento.conta_contrapartida == 20001


def test_import_razao_blocks_inactive_company_from_file_cnpj(session, tmp_path):
    empresa = _empresa()
    empresa.is_active = False
    usuario = _usuario()
    session.add_all([empresa, usuario, _conta(10046), _conta(20001)])
    session.flush()
    xlsx_path = tmp_path / "razao-empresa-inativa.xlsx"
    _write_workbook(
        xlsx_path,
        [
            ["Empresa:", None, empresa.nome_empresa],
            ["C.N.P.J.:", None, "55.666.777/0001-88"],
            ["Período:", None, "01/01/2026 - 31/12/2026"],
            [],
            ["Conta:", "10046", "BCO. SANTANDER"],
            ["Data", "Numero", "Historico", "Contrapartida", "Debito", "Credito"],
            ["2026-01-02", "42", "Pagamento fornecedor", "20001", 250.75, None],
        ],
    )

    with pytest.raises(RazaoImportError, match="empresa.*inativa"):
        import_razao(
            session,
            xlsx_path,
            empresa_id=empresa.id,
            usuario_id=usuario.id,
            original_filename="razao-empresa-inativa.xlsx",
        )

    session.refresh(empresa)
    assert empresa.is_active is False
    assert session.query(Empresa).count() == 1
    assert session.query(LoteImportacaoRazao).count() == 0
    assert session.query(LancamentoRazaoNormalizado).count() == 0


def test_import_razao_allows_active_company_from_file_cnpj(session, tmp_path):
    empresa = _empresa()
    usuario = _usuario()
    session.add_all([empresa, usuario, _conta(10046), _conta(20001)])
    session.flush()
    xlsx_path = tmp_path / "razao-empresa-ativa.xlsx"
    _write_workbook(
        xlsx_path,
        [
            ["Empresa:", None, empresa.nome_empresa],
            ["C.N.P.J.:", None, "55.666.777/0001-88"],
            ["Período:", None, "01/01/2026 - 31/12/2026"],
            [],
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
        original_filename="razao-empresa-ativa.xlsx",
    )

    assert result.status == "completed"
    assert session.query(LoteImportacaoRazao).count() == 1
    assert session.query(LancamentoRazaoNormalizado).count() == 1


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


def test_import_razao_blocks_same_successfully_imported_file_for_same_company(
    session,
    tmp_path,
):
    empresa = _empresa()
    usuario = _usuario()
    session.add_all([empresa, usuario, _conta(10046), _conta(20001)])
    session.flush()
    xlsx_path = tmp_path / "razao-reupload.xlsx"
    _write_workbook(
        xlsx_path,
        [
            ["Conta:", "10046", "BCO. SANTANDER"],
            ["Data", "Numero", "Historico", "Contrapartida", "Debito", "Credito"],
            ["2026-01-02", "42", "Pagamento fornecedor", "20001", 250.75, None],
        ],
    )
    import_razao(
        session,
        xlsx_path,
        empresa_id=empresa.id,
        usuario_id=usuario.id,
        original_filename="razao-reupload.xlsx",
    )

    with pytest.raises(RazaoImportError, match="Arquivo ja importado"):
        import_razao(
            session,
            xlsx_path,
            empresa_id=empresa.id,
            usuario_id=usuario.id,
            original_filename="razao-reupload.xlsx",
        )

    assert session.query(LoteImportacaoRazao).count() == 1
    assert session.query(LancamentoRazaoNormalizado).count() == 1


def test_import_razao_allows_same_file_hash_for_another_company(session, tmp_path):
    empresa_a = _empresa()
    empresa_b = Empresa(
        nome_empresa="Outra Empresa Razao LTDA",
        cnpj_cpf="11222333000144",
        api_key="api-key-outra-razao",
        cod_dominio=8802,
    )
    usuario = _usuario()
    session.add_all(
        [
            empresa_a,
            empresa_b,
            usuario,
            _conta(10046),
            _conta(20001),
        ]
    )
    session.flush()
    xlsx_path = tmp_path / "razao-mesmo-hash-outra-empresa.xlsx"
    _write_workbook(
        xlsx_path,
        [
            ["Conta:", "10046", "BCO. SANTANDER"],
            ["Data", "Numero", "Historico", "Contrapartida", "Debito", "Credito"],
            ["2026-01-02", "42", "Pagamento fornecedor", "20001", 250.75, None],
        ],
    )

    import_razao(
        session,
        xlsx_path,
        empresa_id=empresa_a.id,
        usuario_id=usuario.id,
        original_filename="razao.xlsx",
    )
    result = import_razao(
        session,
        xlsx_path,
        empresa_id=empresa_b.id,
        usuario_id=usuario.id,
        original_filename="razao.xlsx",
    )

    assert result.status == "completed"
    assert session.query(LoteImportacaoRazao).count() == 2
    assert session.query(LancamentoRazaoNormalizado).count() == 2


def test_import_razao_allows_different_file_for_same_company(session, tmp_path):
    empresa = _empresa()
    usuario = _usuario()
    session.add_all([empresa, usuario, _conta(10046), _conta(20001)])
    session.flush()
    first_path = tmp_path / "razao-1.xlsx"
    second_path = tmp_path / "razao-2.xlsx"
    _write_workbook(
        first_path,
        [
            ["Conta:", "10046", "BCO. SANTANDER"],
            ["Data", "Numero", "Historico", "Contrapartida", "Debito", "Credito"],
            ["2026-01-02", "42", "Pagamento fornecedor", "20001", 250.75, None],
        ],
    )
    _write_workbook(
        second_path,
        [
            ["Conta:", "10046", "BCO. SANTANDER"],
            ["Data", "Numero", "Historico", "Contrapartida", "Debito", "Credito"],
            ["2026-01-03", "43", "Outro pagamento", "20001", 99.99, None],
        ],
    )

    import_razao(
        session,
        first_path,
        empresa_id=empresa.id,
        usuario_id=usuario.id,
        original_filename="razao-1.xlsx",
    )
    result = import_razao(
        session,
        second_path,
        empresa_id=empresa.id,
        usuario_id=usuario.id,
        original_filename="razao-2.xlsx",
    )

    assert result.status == "completed"
    assert session.query(LoteImportacaoRazao).count() == 2
    assert session.query(LancamentoRazaoNormalizado).count() == 2


def test_import_razao_links_origin_and_counterpart_accounts_to_company(
    session,
    tmp_path,
):
    empresa = _empresa()
    usuario = _usuario()
    session.add_all([empresa, usuario, _conta(10046), _conta(20001)])
    session.flush()
    xlsx_path = tmp_path / "razao-vinculos.xlsx"
    _write_workbook(
        xlsx_path,
        [
            ["Conta:", "10046", "BCO. SANTANDER"],
            ["Data", "Numero", "Historico", "Contrapartida", "Debito", "Credito"],
            ["2026-01-02", "42", "Pagamento fornecedor", "20001", 250.75, None],
        ],
    )

    import_razao(
        session,
        xlsx_path,
        empresa_id=empresa.id,
        usuario_id=usuario.id,
        original_filename="razao-vinculos.xlsx",
    )

    vinculos = (
        session.query(EmpresaContaContabil)
        .filter(EmpresaContaContabil.empresa_id == empresa.id)
        .order_by(EmpresaContaContabil.conta_codigo)
        .all()
    )
    assert [vinculo.conta_codigo for vinculo in vinculos] == [10046, 20001]
    assert [vinculo.quantidade_lancamentos for vinculo in vinculos] == [1, 1]
    assert all(vinculo.ultima_utilizacao == date(2026, 1, 2) for vinculo in vinculos)


def test_import_razao_updates_existing_account_links_without_duplicates(
    session,
    tmp_path,
):
    empresa = _empresa()
    usuario = _usuario()
    session.add_all([empresa, usuario, _conta(10046), _conta(20001)])
    session.flush()
    first_path = tmp_path / "razao-vinculos-1.xlsx"
    second_path = tmp_path / "razao-vinculos-2.xlsx"
    rows = [
        ["Conta:", "10046", "BCO. SANTANDER"],
        ["Data", "Numero", "Historico", "Contrapartida", "Debito", "Credito"],
    ]
    _write_workbook(
        first_path,
        rows + [["2026-01-02", "42", "Pagamento fornecedor", "20001", 250.75, None]],
    )
    _write_workbook(
        second_path,
        rows + [["2026-01-05", "43", "Pagamento fornecedor", "20001", 99.99, None]],
    )

    import_razao(
        session,
        first_path,
        empresa_id=empresa.id,
        usuario_id=usuario.id,
        original_filename="razao-vinculos-1.xlsx",
    )
    import_razao(
        session,
        second_path,
        empresa_id=empresa.id,
        usuario_id=usuario.id,
        original_filename="razao-vinculos-2.xlsx",
    )

    vinculos = (
        session.query(EmpresaContaContabil)
        .filter(EmpresaContaContabil.empresa_id == empresa.id)
        .order_by(EmpresaContaContabil.conta_codigo)
        .all()
    )
    assert [vinculo.conta_codigo for vinculo in vinculos] == [10046, 20001]
    assert [vinculo.quantidade_lancamentos for vinculo in vinculos] == [2, 2]
    assert all(vinculo.ultima_utilizacao == date(2026, 1, 5) for vinculo in vinculos)


def test_import_razao_account_links_are_isolated_by_company(session, tmp_path):
    empresa_a = _empresa()
    empresa_b = Empresa(
        nome_empresa="Outra Empresa Razao LTDA",
        cnpj_cpf="11222333000144",
        api_key="api-key-outra-razao",
        cod_dominio=8802,
    )
    usuario = _usuario()
    session.add_all([empresa_a, empresa_b, usuario, _conta(10046), _conta(20001)])
    session.flush()
    xlsx_path = tmp_path / "razao-vinculos-empresas.xlsx"
    _write_workbook(
        xlsx_path,
        [
            ["Conta:", "10046", "BCO. SANTANDER"],
            ["Data", "Numero", "Historico", "Contrapartida", "Debito", "Credito"],
            ["2026-01-02", "42", "Pagamento fornecedor", "20001", 250.75, None],
        ],
    )

    import_razao(
        session,
        xlsx_path,
        empresa_id=empresa_a.id,
        usuario_id=usuario.id,
        original_filename="razao-a.xlsx",
    )
    import_razao(
        session,
        xlsx_path,
        empresa_id=empresa_b.id,
        usuario_id=usuario.id,
        original_filename="razao-b.xlsx",
    )

    vinculos_empresa_a = (
        session.query(EmpresaContaContabil)
        .filter(EmpresaContaContabil.empresa_id == empresa_a.id)
        .count()
    )
    vinculos_empresa_b = (
        session.query(EmpresaContaContabil)
        .filter(EmpresaContaContabil.empresa_id == empresa_b.id)
        .count()
    )
    assert vinculos_empresa_a == 2
    assert vinculos_empresa_b == 2
