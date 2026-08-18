from datetime import date
from io import BytesIO

from openpyxl import Workbook

from core.models import AuditEvent, ContaContabil, MovimentoOperacionalImportado
from core.movimentos_operacionais_feedback_importer import (
    importar_feedback_planilha_classificada,
)
from tests.conftest import TestingSessionLocal
from tests.test_movimentos_operacionais_api import _seed_operational_lote_with_movements


HEADERS = [
    "lote_id",
    "movimento_id",
    "linha_original",
    "layout_version",
    "export_revision",
    "row_version",
    "contrapartida_sugerida",
    "confidence_sugerida",
    "status_atual",
    "mensagem_validacao",
    "decisao_revisao",
    "contrapartida_final",
    "observacao_revisao",
]


def _feedback_xlsx(rows: list[dict]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Movimentos"
    sheet.append(HEADERS)
    for row in rows:
        sheet.append([row.get(header) for header in HEADERS])

    output = BytesIO()
    workbook.save(output)
    workbook.close()
    output.seek(0)
    return output.read()


def _write_feedback_file(tmp_path, rows: list[dict]):
    path = tmp_path / "feedback.xlsx"
    path.write_bytes(_feedback_xlsx(rows))
    return path


def test_importar_feedback_processa_arquivo_misto_parcialmente(tmp_path, setup_db):
    usuario, empresa_id, lote_id = _seed_operational_lote_with_movements(
        permissao="operacao"
    )
    _, _outra_empresa_id, outro_lote_id = _seed_operational_lote_with_movements(
        empresa_overrides={
            "nome_empresa": "Outra Empresa Feedback LTDA",
            "cnpj_cpf": "99888777000166",
            "api_key": "api-key-feedback-outra",
            "cod_dominio": 9911,
        },
        usuario_overrides={
            "login": "feedback.outra",
            "email": "feedback.outra@example.com",
        },
    )

    with TestingSessionLocal() as session:
        session.add(
            ContaContabil(
                codigo=20001,
                classificacao="2.0.0",
                nome="Conta",
                tipo="A",
                grau=3,
            )
        )
        session.flush()
        movimentos = (
            session.query(MovimentoOperacionalImportado)
            .filter(MovimentoOperacionalImportado.lote_id == lote_id)
            .order_by(MovimentoOperacionalImportado.id.asc())
            .all()
        )
        movimentos[0].status = "sugerido"
        movimentos[0].contrapartida_sugerida = 20001
        movimentos[0].confidence_sugerida = 0.91
        movimentos[1].status = "revisao"
        movimentos[1].contrapartida_sugerida = None
        movimentos[1].confidence_sugerida = None
        movimento_adulterado = MovimentoOperacionalImportado(
            lote_id=lote_id,
            empresa_id=empresa_id,
            data=date(2026, 1, 4),
            conta_financeira=10046,
            historico="Linha adulterada sensivel",
            historico_normalizado="linha adulterada",
            valor_original=-30,
            valor_absoluto=30,
            direcao="credito",
            tipo_movimento="saida",
            documento="DOC-ADULTERADA",
            observacao="Observacao sensivel adulterada",
            linha_original=3,
            contrapartida_informada=None,
            contrapartida_sugerida=20001,
            confidence_sugerida=0.88,
            status="sugerido",
            mensagens_validacao=[],
            contrapartida_final=None,
            elegivel_treino=False,
            conta_debito=None,
            conta_credito=None,
        )
        session.add(movimento_adulterado)
        session.flush()
        outro_movimento = (
            session.query(MovimentoOperacionalImportado)
            .filter(MovimentoOperacionalImportado.lote_id == outro_lote_id)
            .first()
        )
        rows = [
            {
                "lote_id": lote_id,
                "movimento_id": movimentos[0].id,
                "linha_original": movimentos[0].linha_original,
                "layout_version": "operacional_valor_legado_v1",
                "export_revision": "revision-1",
                "row_version": movimentos[0].row_version,
                "contrapartida_sugerida": movimentos[0].contrapartida_sugerida,
                "confidence_sugerida": movimentos[0].confidence_sugerida,
                "status_atual": movimentos[0].status,
                "mensagem_validacao": "",
                "decisao_revisao": "aprovar",
                "contrapartida_final": 20001,
                "observacao_revisao": "ok",
            },
            {
                "lote_id": lote_id,
                "movimento_id": movimentos[1].id,
                "linha_original": movimentos[1].linha_original,
                "layout_version": "operacional_valor_legado_v1",
                "export_revision": "revision-1",
                "row_version": movimentos[1].row_version,
                "status_atual": movimentos[1].status,
                "decisao_revisao": "",
            },
            {
                "lote_id": lote_id,
                "movimento_id": movimento_adulterado.id,
                "linha_original": movimento_adulterado.linha_original,
                "layout_version": "operacional_valor_legado_v1",
                "export_revision": "revision-1",
                "row_version": movimento_adulterado.row_version,
                "contrapartida_sugerida": 99999,
                "confidence_sugerida": movimento_adulterado.confidence_sugerida,
                "status_atual": movimento_adulterado.status,
                "decisao_revisao": "corrigir",
                "contrapartida_final": 20001,
            },
            {
                "lote_id": outro_lote_id,
                "movimento_id": outro_movimento.id,
                "linha_original": outro_movimento.linha_original,
                "layout_version": "operacional_valor_legado_v1",
                "export_revision": "revision-1",
                "row_version": outro_movimento.row_version,
                "status_atual": outro_movimento.status,
                "decisao_revisao": "rejeitar",
            },
        ]
        feedback_path = _write_feedback_file(tmp_path, rows)

        resumo = importar_feedback_planilha_classificada(
            session,
            feedback_path,
            empresa_id=empresa_id,
            lote_id=lote_id,
            usuario_id=usuario.id,
        )
        session.commit()

        assert resumo.total_linhas == 4
        assert resumo.total_aplicado == 1
        assert resumo.total_ignorado == 1
        assert resumo.total_invalido == 1
        assert resumo.total_conflitante == 0
        assert resumo.total_nao_autorizado == 1
        assert [item.status for item in resumo.resultados] == [
            "aplicada",
            "ignorada",
            "invalida",
            "nao_autorizada",
        ]
        assert resumo.resultados[2].mensagem == "Campo somente leitura alterado"
        assert resumo.resultados[3].mensagem == "Linha fora do escopo da empresa/lote"

        session.refresh(movimentos[0])
        session.refresh(movimentos[1])
        session.refresh(movimento_adulterado)
        assert movimentos[0].status == "aprovado"
        assert movimentos[0].contrapartida_final == 20001
        assert movimentos[1].status == "revisao"
        assert movimentos[1].contrapartida_final is None
        assert movimento_adulterado.status == "sugerido"
        assert movimento_adulterado.contrapartida_final is None

        event_types = [event.event_type for event in session.query(AuditEvent).all()]
        assert "operational_movements.feedback_imported" in event_types
        assert "operational_movements.aprovado" in event_types
        assert "Linha aprovar sensivel" not in str(
            [event.metadata_json for event in session.query(AuditEvent).all()]
        )
        assert "DOC-APROVAR" not in str(
            [event.metadata_json for event in session.query(AuditEvent).all()]
        )


def test_importar_feedback_aplica_correcao_e_rejeicao(tmp_path, setup_db):
    usuario, empresa_id, lote_id = _seed_operational_lote_with_movements(
        permissao="operacao"
    )

    with TestingSessionLocal() as session:
        session.add(
            ContaContabil(
                codigo=30001,
                classificacao="3.0.0",
                nome="Conta Correcao",
                tipo="A",
                grau=3,
            )
        )
        session.commit()
        movimentos = (
            session.query(MovimentoOperacionalImportado)
            .filter_by(lote_id=lote_id)
            .order_by(MovimentoOperacionalImportado.id.asc())
            .all()
        )
        rows = [
            {
                "lote_id": lote_id,
                "movimento_id": movimentos[0].id,
                "linha_original": movimentos[0].linha_original,
                "layout_version": "operacional_valor_legado_v1",
                "export_revision": "revision-2",
                "row_version": movimentos[0].row_version,
                "status_atual": movimentos[0].status,
                "decisao_revisao": "corrigir",
                "contrapartida_final": 30001,
            },
            {
                "lote_id": lote_id,
                "movimento_id": movimentos[1].id,
                "linha_original": movimentos[1].linha_original,
                "layout_version": "operacional_valor_legado_v1",
                "export_revision": "revision-2",
                "row_version": movimentos[1].row_version,
                "status_atual": movimentos[1].status,
                "decisao_revisao": "rejeitar",
            },
        ]

        resumo = importar_feedback_planilha_classificada(
            session,
            _write_feedback_file(tmp_path, rows),
            empresa_id=empresa_id,
            lote_id=lote_id,
            usuario_id=usuario.id,
        )
        session.commit()

        assert resumo.total_aplicado == 2
        assert [item.status for item in resumo.resultados] == ["aplicada", "aplicada"]
        session.refresh(movimentos[0])
        session.refresh(movimentos[1])
        assert movimentos[0].status == "corrigido"
        assert movimentos[0].contrapartida_final == 30001
        assert movimentos[1].status == "rejeitado"
        assert movimentos[1].contrapartida_final is None


def test_importar_feedback_retorna_linhas_invalidas_sem_bloquear_validas(
    tmp_path,
    setup_db,
):
    usuario, empresa_id, lote_id = _seed_operational_lote_with_movements(
        permissao="operacao"
    )

    with TestingSessionLocal() as session:
        session.add(
            ContaContabil(
                codigo=20001,
                classificacao="2.0.0",
                nome="Conta",
                tipo="A",
                grau=3,
            )
        )
        session.commit()
        movimentos = (
            session.query(MovimentoOperacionalImportado)
            .filter_by(lote_id=lote_id)
            .order_by(MovimentoOperacionalImportado.id.asc())
            .all()
        )
        rows = [
            {
                "lote_id": lote_id,
                "movimento_id": movimentos[0].id,
                "linha_original": movimentos[0].linha_original,
                "layout_version": "operacional_valor_legado_v1",
                "export_revision": "revision-3",
                "row_version": movimentos[0].row_version,
                "status_atual": movimentos[0].status,
                "decisao_revisao": "decidir",
            },
            {
                "lote_id": lote_id,
                "movimento_id": movimentos[1].id,
                "linha_original": movimentos[1].linha_original,
                "layout_version": "operacional_valor_legado_v1",
                "export_revision": "revision-3",
                "row_version": movimentos[1].row_version,
                "status_atual": movimentos[1].status,
                "decisao_revisao": "corrigir",
                "contrapartida_final": 99999,
            },
        ]

        resumo = importar_feedback_planilha_classificada(
            session,
            _write_feedback_file(tmp_path, rows),
            empresa_id=empresa_id,
            lote_id=lote_id,
            usuario_id=usuario.id,
        )

        assert resumo.total_invalido == 2
        assert [item.mensagem for item in resumo.resultados] == [
            "Decisão de revisão inválida",
            "Conta final inválida ou inativa",
        ]


def test_importar_feedback_rejeita_erro_estrutural_sem_aba_movimentos(
    tmp_path,
    setup_db,
):
    from core.movimentos_operacionais_feedback_importer import (
        MovimentoOperacionalFeedbackImportError,
    )

    usuario, empresa_id, lote_id = _seed_operational_lote_with_movements(
        permissao="operacao"
    )
    workbook = Workbook()
    workbook.active.title = "OutraAba"
    path = tmp_path / "sem-movimentos.xlsx"
    workbook.save(path)
    workbook.close()

    with TestingSessionLocal() as session:
        try:
            importar_feedback_planilha_classificada(
                session,
                path,
                empresa_id=empresa_id,
                lote_id=lote_id,
                usuario_id=usuario.id,
            )
        except MovimentoOperacionalFeedbackImportError as exc:
            assert str(exc) == "Aba Movimentos não encontrada"
        else:
            raise AssertionError("esperava erro estrutural")

