from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs/specs/16-planilha-classificada-feedback-roundtrip.md"


def read_spec() -> str:
    return SPEC.read_text(encoding="utf-8")


def normalized_spec() -> str:
    return " ".join(read_spec().split())


def test_spec16_define_row_version_como_versao_canonica():
    spec = read_spec()

    assert "`row_version` inteiro monotonico" in spec
    assert "`row_version` ou `updated_at`" not in spec
    assert "usar `updated_at` como alternativa canonica" in spec
    assert "estado revisavel ou exportavel" in spec


def test_spec16_define_export_revision_uuid_sem_snapshot_obrigatorio():
    spec = read_spec()

    assert "`export_revision` e um UUID gerado a cada download" in spec
    assert "Todas as linhas do arquivo compartilham o mesmo `export_revision`" in spec
    assert "nao exige snapshot persistido" in spec
    assert "presenca e consistencia de `export_revision`" in spec


def test_spec16_define_rotas_definitivas_do_roundtrip():
    spec = read_spec()

    assert (
        "GET `/api/v1/companies/{company_id}/movimentos-operacionais/lotes/"
        "{lote_id}/planilha-classificada`"
    ) in spec
    assert (
        "POST `/api/v1/companies/{company_id}/movimentos-operacionais/lotes/"
        "{lote_id}/planilha-classificada/feedback`"
    ) in spec


def test_spec16_define_snapshot_minimo_e_campos_editaveis():
    spec = read_spec()
    normalized = normalized_spec()

    for campo in [
        "`lote_id`",
        "`movimento_id`",
        "`linha_original`",
        "`layout_version`",
        "`export_revision`",
        "`row_version`",
        "`contrapartida`",
        "`contrapartida_sugerida`",
        "`confidence_sugerida`",
        "`contrapartida_final`",
        "`decisao_revisao`",
        "`observacao_revisao`",
    ]:
        assert campo in spec

    assert "A importacao aceita somente os campos editaveis" in spec
    assert "Alteracoes em campos somente leitura devem ser ignoradas" in normalized


def test_spec16_define_concorrencia_idempotencia_e_processamento_parcial():
    spec = read_spec()
    normalized = normalized_spec()

    assert (
        "comparar `row_version` da planilha com o `row_version` persistido"
        in normalized
    )
    assert "HTTP 200 com resumo e resultados por linha" in spec
    assert "HTTP 400" in spec
    assert "reenvio idempotente" in spec
    assert "Linhas de outro lote" in spec
    assert "`export_revision` divergente" in spec
