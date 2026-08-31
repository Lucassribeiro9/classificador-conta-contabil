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
from core.movimentos_operacionais_parser import MovimentoOperacionalParseError


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
    periodo_inicio="01/01/2025",
    periodo_fim="31/01/2025",
    headers=None,
    rows=None,
):
    """Grava planilha operacional simples para exercitar o importador."""

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Movimentos"
    sheet.append(["Empresa", "Empresa Operacional LTDA"])
    sheet.append(["Codigo dominio", codigo_dominio])
    sheet.append(["CNPJ/CPF", cnpj_cpf])
    sheet.append(["Periodo inicio", periodo_inicio])
    sheet.append(["Periodo fim", periodo_fim])
    sheet.append([])
    sheet.append(
        headers
        or [
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


def test_import_movimentos_operacionais_aceita_periodos_como_data_nativa_excel(
    session,
    tmp_path,
):
    """Deve importar lote quando os periodos forem datas nativas do Excel."""

    empresa = _empresa()
    usuario = _usuario()
    session.add_all([empresa, usuario, _conta(10046), _conta(10722)])
    session.flush()
    session.add_all([_vinculo(empresa.id, 10046), _vinculo(empresa.id, 10722)])
    session.flush()
    xlsx_path = tmp_path / "movimentos-periodos-data-nativa.xlsx"
    _write_movimentos_workbook(
        xlsx_path,
        periodo_inicio=date(2025, 1, 1),
        periodo_fim=date(2025, 1, 31),
        rows=[
            [
                "02/01/2025",
                10046,
                "RECEBTO.DUPLICATAS",
                3660.15,
                10722,
                "entrada",
                "OFX-0001",
                "Periodo em data nativa",
            ],
        ],
    )

    result = import_movimentos_operacionais(
        session,
        xlsx_path,
        empresa_id=empresa.id,
        usuario_id=usuario.id,
        original_filename="movimentos-periodos-data-nativa.xlsx",
    )

    lote = session.query(LoteImportacaoMovimentoOperacional).one()
    assert result.status == "completed_with_warnings"
    assert lote.periodo_inicio == date(2025, 1, 1)
    assert lote.periodo_fim == date(2025, 1, 31)


def test_import_movimentos_operacionais_persiste_layout_valor_saldo(session, tmp_path):
    """Deve persistir a versao oficial do layout A detectada pelo parser."""

    empresa = _empresa()
    usuario = _usuario()
    session.add_all([empresa, usuario, _conta(10046), _conta(10722)])
    session.flush()
    session.add_all([_vinculo(empresa.id, 10046), _vinculo(empresa.id, 10722)])
    session.flush()
    xlsx_path = tmp_path / "movimentos-valor-saldo.xlsx"
    _write_movimentos_workbook(
        xlsx_path,
        headers=[
            "data",
            "conta_financeira",
            "historico",
            "valor",
            "saldo",
            "contrapartida",
            "tipo_movimento",
            "documento",
            "observacao",
        ],
        rows=[
            [
                "02/01/2025",
                10046,
                "RECEBTO.DUPLICATAS",
                3660.15,
                5000.15,
                10722,
                "entrada",
                "OFX-0001",
                "Layout com saldo",
            ],
        ],
    )

    result = import_movimentos_operacionais(
        session,
        xlsx_path,
        empresa_id=empresa.id,
        usuario_id=usuario.id,
        original_filename="movimentos-valor-saldo.xlsx",
    )

    lote = session.query(LoteImportacaoMovimentoOperacional).one()
    assert result.status == "completed"
    assert lote.layout_version == "operacional_valor_saldo_v1"


def test_import_movimentos_operacionais_persiste_layout_debito_credito_saldo_sem_linhas(
    session,
    tmp_path,
):
    """Deve persistir layout B sem antecipar normalizacao de debito/credito."""

    empresa = _empresa()
    usuario = _usuario()
    session.add_all([empresa, usuario])
    session.flush()
    xlsx_path = tmp_path / "movimentos-debito-credito-saldo.xlsx"
    _write_movimentos_workbook(
        xlsx_path,
        headers=[
            "data",
            "conta_financeira",
            "historico",
            "debito",
            "credito",
            "saldo",
            "contrapartida",
            "tipo_movimento",
            "documento",
            "observacao",
        ],
    )

    result = import_movimentos_operacionais(
        session,
        xlsx_path,
        empresa_id=empresa.id,
        usuario_id=usuario.id,
        original_filename="movimentos-debito-credito-saldo.xlsx",
    )

    lote = session.query(LoteImportacaoMovimentoOperacional).one()
    assert result.total_linhas == 0
    assert lote.layout_version == "operacional_debito_credito_saldo_v1"


def test_import_movimentos_operacionais_nao_persiste_layout_ambiguo(session, tmp_path):
    """Deve bloquear layout ambiguo antes de criar lote."""

    empresa = _empresa()
    usuario = _usuario()
    session.add_all([empresa, usuario])
    session.flush()
    xlsx_path = tmp_path / "movimentos-ambiguo.xlsx"
    _write_movimentos_workbook(
        xlsx_path,
        headers=[
            "data",
            "conta_financeira",
            "historico",
            "valor",
            "debito",
            "credito",
        ],
    )

    with pytest.raises(MovimentoOperacionalParseError):
        import_movimentos_operacionais(
            session,
            xlsx_path,
            empresa_id=empresa.id,
            usuario_id=usuario.id,
            original_filename="movimentos-ambiguo.xlsx",
        )

    assert session.query(LoteImportacaoMovimentoOperacional).count() == 0


def test_import_movimentos_operacionais_normaliza_layout_b_e_mantem_invalidos_recuperaveis(
    session,
    tmp_path,
):
    """Deve importar validos do layout B e contabilizar invalidos por linha."""

    empresa = _empresa()
    usuario = _usuario()
    session.add_all([empresa, usuario, _conta(10046), _conta(10722)])
    session.flush()
    session.add_all([_vinculo(empresa.id, 10046), _vinculo(empresa.id, 10722)])
    session.flush()
    xlsx_path = tmp_path / "movimentos-layout-b-parcial.xlsx"
    _write_movimentos_workbook(
        xlsx_path,
        headers=[
            "data",
            "conta_financeira",
            "historico",
            "debito",
            "credito",
            "saldo",
            "contrapartida",
            "tipo_movimento",
            "documento",
            "observacao",
        ],
        rows=[
            [
                "02/01/2025",
                10046,
                "RECEBIMENTO CLIENTE",
                None,
                1500,
                2500,
                10722,
                "entrada",
                "OFX-0001",
                "Credito valido",
            ],
            [
                "03/01/2025",
                10046,
                "PAGAMENTO FORNECEDOR",
                300,
                None,
                2200,
                10722,
                "saida",
                "OFX-0002",
                "Debito valido",
            ],
            [
                "04/01/2025",
                10046,
                "AMBOS PREENCHIDOS",
                100,
                200,
                2300,
                10722,
                "entrada",
                "OFX-0003",
                "Invalido",
            ],
            [
                "05/01/2025",
                10046,
                "AMBOS VAZIOS",
                None,
                None,
                2300,
                10722,
                "entrada",
                "OFX-0004",
                "Invalido",
            ],
            [
                "06/01/2025",
                10046,
                "VALOR ZERO",
                0,
                None,
                2300,
                10722,
                "saida",
                "OFX-0005",
                "Invalido",
            ],
            [
                "07/01/2025",
                10046,
                "VALOR NEGATIVO",
                None,
                -10,
                2290,
                10722,
                "entrada",
                "OFX-0006",
                "Invalido",
            ],
        ],
    )

    result = import_movimentos_operacionais(
        session,
        xlsx_path,
        empresa_id=empresa.id,
        usuario_id=usuario.id,
        original_filename="movimentos-layout-b-parcial.xlsx",
    )

    lote = session.query(LoteImportacaoMovimentoOperacional).one()
    movimentos = (
        session.query(MovimentoOperacionalImportado)
        .order_by(MovimentoOperacionalImportado.data)
        .all()
    )
    assert lote.layout_version == "operacional_debito_credito_saldo_v1"
    assert result.status == "completed_with_warnings"
    assert result.total_linhas == 6
    assert result.total_importadas == 2
    assert result.total_invalidas == 4
    assert [warning["linha"] for warning in result.warnings] == [3, 4, 5, 6]
    assert {
        tuple(warning["warnings"]) for warning in result.warnings
    } == {("Valor do movimento ausente, invalido ou zero.",)}
    assert [movimento.valor_original for movimento in movimentos] == [
        Decimal("1500.00"),
        Decimal("-300.00"),
    ]
    assert [movimento.valor_absoluto for movimento in movimentos] == [
        Decimal("1500.00"),
        Decimal("300.00"),
    ]
    assert [movimento.direcao for movimento in movimentos] == ["debito", "credito"]


def test_import_movimentos_operacionais_persiste_e_calcula_saldos_por_conta(
    session,
    tmp_path,
):
    """Deve preservar saldo observado e calcular sequencias independentes."""

    empresa = _empresa()
    usuario = _usuario()
    session.add_all([empresa, usuario, _conta(10046), _conta(20000), _conta(10722)])
    session.flush()
    session.add_all(
        [
            _vinculo(empresa.id, 10046),
            _vinculo(empresa.id, 20000),
            _vinculo(empresa.id, 10722),
        ]
    )
    session.flush()
    xlsx_path = tmp_path / "movimentos-saldos.xlsx"
    _write_movimentos_workbook(
        xlsx_path,
        headers=[
            "data",
            "conta_financeira",
            "historico",
            "valor",
            "saldo",
            "contrapartida",
            "tipo_movimento",
            "documento",
            "observacao",
        ],
        rows=[
            ["02/01/2025", 10046, "SALDO INICIAL OBSERVADO", 100, 1000, 10722, "entrada"],
            ["03/01/2025", 20000, "OUTRA CONTA INICIAL", 50, 500, 10722, "entrada"],
            ["04/01/2025", 10046, "SAIDA CONFERIDA", -100, 900, 10722, "saida"],
            ["05/01/2025", 20000, "SALDO DIVERGENTE", 25, 999, 10722, "entrada"],
            ["06/01/2025", 10046, "SALDO AUSENTE", -50, None, 10722, "saida"],
            ["07/01/2025", 10046, "SALDO INVALIDO", -50, "saldo invalido", 10722, "saida"],
        ],
    )

    result = import_movimentos_operacionais(
        session,
        xlsx_path,
        empresa_id=empresa.id,
        usuario_id=usuario.id,
        original_filename="movimentos-saldos.xlsx",
    )

    lote = session.query(LoteImportacaoMovimentoOperacional).one()
    movimentos = (
        session.query(MovimentoOperacionalImportado)
        .order_by(MovimentoOperacionalImportado.linha_original)
        .all()
    )
    assert result.status == "completed_with_warnings"
    assert lote.status == "completed_with_warnings"
    assert result.total_importadas == 6
    assert [mov.saldo_observado_original for mov in movimentos] == [
        "1000",
        "500",
        "900",
        "999",
        None,
        "saldo invalido",
    ]
    assert [mov.saldo_observado_decimal for mov in movimentos] == [
        Decimal("1000.00"),
        Decimal("500.00"),
        Decimal("900.00"),
        Decimal("999.00"),
        None,
        None,
    ]
    assert [mov.saldo_calculado_decimal for mov in movimentos] == [
        Decimal("1000.00"),
        Decimal("500.00"),
        Decimal("900.00"),
        Decimal("525.00"),
        Decimal("850.00"),
        Decimal("800.00"),
    ]
    assert movimentos[3].warnings_saldo == [
        "Saldo observado diverge do saldo calculado para a conta financeira."
    ]
    assert movimentos[4].warnings_saldo == [
        "Saldo ausente; conferencia por saldo limitada para esta linha."
    ]
    assert movimentos[5].warnings_saldo == [
        "Saldo informado invalido; conferencia por saldo limitada para esta linha."
    ]
    assert movimentos[3].status == "pre_classificado"
    assert movimentos[4].status == "pre_classificado"
    assert movimentos[5].status == "pre_classificado"


def test_import_movimentos_operacionais_legado_registra_warning_de_saldo_ausente(
    session,
    tmp_path,
):
    """Deve manter legado compativel e avisar ausencia de saldo por movimento."""

    empresa = _empresa()
    usuario = _usuario()
    session.add_all([empresa, usuario, _conta(10046), _conta(10722)])
    session.flush()
    session.add_all([_vinculo(empresa.id, 10046), _vinculo(empresa.id, 10722)])
    session.flush()
    xlsx_path = tmp_path / "movimentos-legado-saldo-ausente.xlsx"
    _write_movimentos_workbook(
        xlsx_path,
        rows=[["02/01/2025", 10046, "RECEBTO.DUPLICATAS", 100, 10722, "entrada"]],
    )

    result = import_movimentos_operacionais(
        session,
        xlsx_path,
        empresa_id=empresa.id,
        usuario_id=usuario.id,
        original_filename="movimentos-legado-saldo-ausente.xlsx",
    )

    movimento = session.query(MovimentoOperacionalImportado).one()
    assert result.status == "completed_with_warnings"
    assert movimento.saldo_observado_original is None
    assert movimento.saldo_observado_decimal is None
    assert movimento.saldo_calculado_decimal == Decimal("100.00")
    assert movimento.warnings_saldo == [
        "Saldo ausente; conferencia por saldo limitada para esta linha.",
        "Saldo inicial ausente; saldo calculado partiu de zero.",
    ]
    assert movimento.status == "pre_classificado"


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
            "linha": 1,
            "warnings": [
                "Saldo ausente; conferencia por saldo limitada para esta linha.",
                "Saldo inicial ausente; saldo calculado partiu de zero.",
            ],
        },
        {
            "linha": 2,
            "warnings": ["Saldo ausente; conferencia por saldo limitada para esta linha."],
        },
        {
            "linha": 3,
            "warnings": ["Contrapartida 103382 nao vinculada a empresa."],
        },
        {
            "linha": 3,
            "warnings": ["Saldo ausente; conferencia por saldo limitada para esta linha."],
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
    assert lote.layout_version == "operacional_valor_legado_v1"
    assert lote.file_hash.startswith("sha256:")
    assert [movimento.linha_original for movimento in movimentos] == [1, 2, 3]
    assert [movimento.row_version for movimento in movimentos] == [1, 1, 1]
    assert [movimento.status for movimento in movimentos] == [
        "pre_classificado",
        "pendente",
        "revisao",
    ]
    assert [movimento.empresa_id for movimento in movimentos] == [empresa.id] * 3
    assert movimentos[0].valor_original == Decimal("3660.15")
    assert movimentos[0].valor_absoluto == Decimal("3660.15")
    assert movimentos[0].direcao == "debito"
    assert movimentos[1].direcao == "credito"
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
    assert first_result.status == "completed_with_warnings"

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
