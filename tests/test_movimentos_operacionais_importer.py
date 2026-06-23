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
    EmpresaContaContabil,
    LoteImportacaoMovimentoOperacional,
    MovimentoOperacionalImportado,
    Usuario,
)
from core.movimentos_operacionais_importer import (
    MovimentoOperacionalImportError,
    import_movimentos_operacionais,
)


@pytest.fixture()
def session():
    """Cria banco SQLite isolado para validar persistencia da importacao."""

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


def _empresa(cnpj_cpf="11222333000144", cod_dominio=1122) -> Empresa:
    """Cria empresa minima para testes de importacao operacional."""

    return Empresa(
        nome_empresa="Empresa Operacional LTDA",
        api_key=f"api-key-{cnpj_cpf}",
        cnpj_cpf=cnpj_cpf,
        cod_dominio=cod_dominio,
    )


def _usuario() -> Usuario:
    """Cria usuario minimo para associar ao lote."""

    return Usuario(
        nome="Operador Movimentos",
        login="operador.movimentos",
        email="operador.movimentos@example.com",
        senha_hash="$argon2id$v=19$hash-de-teste",
        papel="operador",
    )


def _conta(codigo: int, *, tipo="A", is_active=True) -> ContaContabil:
    """Cria conta contabil analitica por padrao."""

    return ContaContabil(
        codigo=codigo,
        classificacao=f"1.1.{codigo}",
        nome=f"CONTA {codigo}",
        tipo=tipo,
        grau=6,
        is_active=is_active,
    )


def _vinculo(empresa_id: int, conta_codigo: int) -> EmpresaContaContabil:
    """Cria vinculo entre empresa e conta usada."""

    return EmpresaContaContabil(
        empresa_id=empresa_id,
        conta_codigo=conta_codigo,
        quantidade_lancamentos=1,
        ultima_utilizacao=date(2025, 1, 1),
    )


def _write_movimentos_workbook(
    path,
    *,
    cnpj_cpf="11.222.333/0001-44",
    codigo_dominio="1122",
    rows=None,
):
    """Grava planilha operacional simples para exercitar o importador."""

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Movimentos"
    sheet.append(["Empresa", "Empresa Operacional LTDA"])
    sheet.append(["Codigo dominio", codigo_dominio])
    sheet.append(["CNPJ/CPF", cnpj_cpf])
    sheet.append(["Periodo inicio", "01/01/2025"])
    sheet.append(["Periodo fim", "31/01/2025"])
    sheet.append([])
    sheet.append(
        [
            "data",
            "conta_financeira",
            "historico",
            "valor",
            "contrapartida",
            "tipo_movimento",
            "documento",
            "observacao",
        ]
    )
    for row in rows or []:
        sheet.append(row)
    workbook.save(path)
    workbook.close()


def test_import_movimentos_operacionais_persiste_lote_parcial_e_movimentos(session, tmp_path):
    """Deve persistir validos/recuperaveis e ignorar invalidos em lote parcial."""

    empresa = _empresa()
    usuario = _usuario()
    session.add_all([empresa, usuario, _conta(10046), _conta(10722), _conta(103382)])
    session.flush()
    session.add_all([_vinculo(empresa.id, 10046), _vinculo(empresa.id, 10722)])
    session.flush()
    xlsx_path = tmp_path / "movimentos-parcial.xlsx"
    _write_movimentos_workbook(
        xlsx_path,
        codigo_dominio="9999",
        rows=[
            [
                "02/01/2025",
                10046,
                "RECEBTO.DUPLICATAS",
                3660.15,
                10722,
                "entrada",
                "OFX-0001",
                "Classificada",
            ],
            [
                "03/01/2025",
                10046,
                "PAGTO SEM CONTRAPARTIDA",
                -1200,
                None,
                "saida",
                "OFX-0002",
                "Pendente",
            ],
            [
                "04/01/2025",
                10046,
                "PAGTO ALUGUEL",
                -800,
                103382,
                "saida",
                "BOL-123",
                "Conta ainda nao vinculada",
            ],
            [
                "05/01/2025",
                10046,
                "VALOR ZERO",
                0,
                10722,
                "entrada",
                "OFX-0003",
                "Invalida",
            ],
        ],
    )

    result = import_movimentos_operacionais(
        session,
        xlsx_path,
        empresa_id=empresa.id,
        usuario_id=usuario.id,
        original_filename="movimentos-parcial.xlsx",
    )

    lote = session.query(LoteImportacaoMovimentoOperacional).one()
    movimentos = (
        session.query(MovimentoOperacionalImportado)
        .order_by(MovimentoOperacionalImportado.data)
        .all()
    )
    assert result.lote_id == lote.id
    assert result.status == "completed_with_warnings"
    assert result.total_linhas == 4
    assert result.total_importadas == 3
    assert result.total_invalidas == 1
    assert result.warnings == [
        {
            "linha": None,
            "warnings": ["Codigo dominio do arquivo diverge da empresa selecionada."],
        },
        {
            "linha": 3,
            "warnings": ["Contrapartida 103382 nao vinculada a empresa."],
        },
        {
            "linha": 4,
            "warnings": ["Valor do movimento ausente, invalido ou zero."],
        },
    ]
    assert lote.status == "completed_with_warnings"
    assert lote.total_linhas == 4
    assert lote.total_importadas == 3
    assert lote.total_invalidas == 1
    assert lote.warnings_metadata == {"warnings": result.warnings}
    assert lote.cnpj_cpf_arquivo == empresa.cnpj_cpf
    assert lote.codigo_dominio_arquivo == "9999"
    assert lote.file_hash.startswith("sha256:")
    assert [movimento.status for movimento in movimentos] == [
        "pre_classificado",
        "pendente",
        "revisao",
    ]
    assert [movimento.empresa_id for movimento in movimentos] == [empresa.id] * 3
    assert movimentos[0].valor_original == Decimal("3660.15")
    assert movimentos[0].valor_absoluto == Decimal("3660.15")
    assert movimentos[0].direcao == "entrada"
    assert movimentos[0].contrapartida_informada == 10722
    assert movimentos[2].mensagens_validacao == [
        "Contrapartida 103382 nao vinculada a empresa."
    ]


def test_import_movimentos_operacionais_bloqueia_cnpj_divergente(session, tmp_path):
    """Deve bloquear antes de persistir lote quando CNPJ nao corresponde."""

    empresa = _empresa(cnpj_cpf="99888777000166")
    usuario = _usuario()
    session.add_all([empresa, usuario, _conta(10046), _conta(10722)])
    session.flush()
    xlsx_path = tmp_path / "movimentos-cnpj-divergente.xlsx"
    _write_movimentos_workbook(
        xlsx_path,
        rows=[
            ["02/01/2025", 10046, "RECEBTO.DUPLICATAS", 3660.15, 10722, "entrada"]
        ],
    )

    with pytest.raises(
        MovimentoOperacionalImportError,
        match="CNPJ da planilha operacional nao corresponde a empresa",
    ):
        import_movimentos_operacionais(
            session,
            xlsx_path,
            empresa_id=empresa.id,
            usuario_id=usuario.id,
            original_filename="movimentos-cnpj-divergente.xlsx",
        )

    assert session.query(LoteImportacaoMovimentoOperacional).count() == 0
    assert session.query(MovimentoOperacionalImportado).count() == 0


def test_import_movimentos_operacionais_bloqueia_reimportacao_por_file_hash(
    session,
    tmp_path,
):
    """Deve bloquear reimportacao de arquivo ja importado com sucesso parcial."""

    empresa = _empresa()
    usuario = _usuario()
    session.add_all([empresa, usuario, _conta(10046), _conta(10722)])
    session.flush()
    session.add_all([_vinculo(empresa.id, 10046), _vinculo(empresa.id, 10722)])
    session.flush()
    xlsx_path = tmp_path / "movimentos-duplicado.xlsx"
    _write_movimentos_workbook(
        xlsx_path,
        rows=[
            ["02/01/2025", 10046, "RECEBTO.DUPLICATAS", 3660.15, 10722, "entrada"]
        ],
    )
    first_result = import_movimentos_operacionais(
        session,
        xlsx_path,
        empresa_id=empresa.id,
        usuario_id=usuario.id,
        original_filename="movimentos-duplicado.xlsx",
    )
    assert first_result.status == "completed"

    with pytest.raises(
        MovimentoOperacionalImportError,
        match="Arquivo ja importado com sucesso para esta empresa",
    ):
        import_movimentos_operacionais(
            session,
            xlsx_path,
            empresa_id=empresa.id,
            usuario_id=usuario.id,
            original_filename="movimentos-duplicado.xlsx",
        )

    assert session.query(LoteImportacaoMovimentoOperacional).count() == 1
    assert session.query(MovimentoOperacionalImportado).count() == 1


def test_import_movimentos_operacionais_lote_failed_quando_todas_linhas_invalidas(
    session,
    tmp_path,
):
    """Deve criar lote failed sem movimentos quando nenhuma linha e importavel."""

    empresa = _empresa()
    usuario = _usuario()
    session.add_all([empresa, usuario, _conta(10046), _conta(10722)])
    session.flush()
    session.add_all([_vinculo(empresa.id, 10046), _vinculo(empresa.id, 10722)])
    session.flush()
    xlsx_path = tmp_path / "movimentos-invalidos.xlsx"
    _write_movimentos_workbook(
        xlsx_path,
        rows=[
            ["02/01/2025", 10046, "VALOR ZERO", 0, 10722, "entrada"],
            ["03/01/2025", 99999, "CONTA INVALIDA", 100, 10722, "entrada"],
        ],
    )

    result = import_movimentos_operacionais(
        session,
        xlsx_path,
        empresa_id=empresa.id,
        usuario_id=usuario.id,
        original_filename="movimentos-invalidos.xlsx",
    )

    lote = session.query(LoteImportacaoMovimentoOperacional).one()
    assert result.status == "failed"
    assert result.total_linhas == 2
    assert result.total_importadas == 0
    assert result.total_invalidas == 2
    assert result.warnings == [
        {
            "linha": 1,
            "warnings": ["Valor do movimento ausente, invalido ou zero."],
        },
        {
            "linha": 2,
            "warnings": [
                "Conta financeira 99999 inexistente, sintetica ou inativa."
            ],
        },
    ]
    assert lote.status == "failed"
    assert session.query(MovimentoOperacionalImportado).count() == 0
