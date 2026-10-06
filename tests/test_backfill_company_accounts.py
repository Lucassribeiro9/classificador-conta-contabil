from datetime import date
import json

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from core.database import Base
from core.models import ContaContabil, ContaContabilEmpresa, Empresa, EmpresaContaContabil
from core.models import BackfillContasContabeisExecucao, BackfillContasContabeisItem
from scripts import backfill_company_accounts
from scripts.backfill_company_accounts import (
    apply_backfill,
    preflight_backfill,
    rollback_backfill,
)


def _database(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'backfill.db'}")
    Base.metadata.create_all(engine)
    return engine


def _linked_account(session: Session) -> tuple[Empresa, ContaContabil]:
    empresa = Empresa(
        nome_empresa="Empresa sintética",
        api_key="backfill-test-key",
        cnpj_cpf="12345678000199",
        cod_dominio=516001,
    )
    conta = ContaContabil(
        codigo=10046,
        classificacao="1.1.1",
        nome="Banco legado",
        tipo="A",
        grau=3,
        is_active=True,
        is_financial_origin=True,
    )
    session.add_all([empresa, conta])
    session.flush()
    session.add(
        EmpresaContaContabil(
            empresa_id=empresa.id,
            conta_codigo=conta.codigo,
            quantidade_lancamentos=2,
            ultima_utilizacao=date(2026, 1, 31),
        )
    )
    session.commit()
    return empresa, conta


def test_preflight_reports_eligible_link_without_writing(tmp_path):
    engine = _database(tmp_path)
    try:
        with Session(engine) as session:
            _linked_account(session)

            result = preflight_backfill(session)

            assert result.eligible == 1
            assert result.already_present == 0
            assert result.conflicts == 0
            assert result.ineligible == 0
            assert session.scalars(select(ContaContabilEmpresa)).all() == []
    finally:
        engine.dispose()


def test_apply_creates_company_identity_from_linked_legacy_account(tmp_path):
    engine = _database(tmp_path)
    try:
        with Session(engine) as session:
            _linked_account(session)

            result = apply_backfill(session)

            identity = session.scalar(select(ContaContabilEmpresa))
            assert result.created == 1
            assert identity is not None
            assert identity.empresa_id == 1
            assert identity.codigo == 10046
            assert identity.classificacao == "1.1.1"
            assert identity.nome == "Banco legado"
            assert identity.tipo == "A"
            assert identity.grau == 3
            assert identity.is_active is True
            assert identity.is_financial_origin is True
            assert result.run_id
    finally:
        engine.dispose()


def test_repeated_apply_does_not_duplicate_created_identity(tmp_path):
    engine = _database(tmp_path)
    try:
        with Session(engine) as session:
            _linked_account(session)

            first = apply_backfill(session)
            second = apply_backfill(session)

            assert first.created == 1
            assert second.created == 0
            assert second.already_present == 1
            assert len(session.scalars(select(ContaContabilEmpresa)).all()) == 1
    finally:
        engine.dispose()


def test_existing_company_identity_is_preserved_and_divergence_reported(tmp_path):
    engine = _database(tmp_path)
    try:
        with Session(engine) as session:
            empresa, _ = _linked_account(session)
            identity = ContaContabilEmpresa(
                empresa_id=empresa.id,
                codigo=10046,
                classificacao="2.1",
                nome="Nome específico da empresa",
                tipo="A",
                grau=2,
                is_active=True,
                is_financial_origin=False,
            )
            session.add(identity)
            session.commit()

            result = apply_backfill(session)

            persisted = session.scalar(select(ContaContabilEmpresa))
            assert result.created == 0
            assert result.conflicts == 1
            assert persisted.nome == "Nome específico da empresa"
            assert persisted.classificacao == "2.1"
    finally:
        engine.dispose()


def test_rollback_removes_only_identity_created_by_selected_run(tmp_path):
    engine = _database(tmp_path)
    try:
        with Session(engine) as session:
            _linked_account(session)
            applied = apply_backfill(session)

            rolled_back = rollback_backfill(session, applied.run_id)

            assert rolled_back.rolled_back == 1
            assert session.scalars(select(ContaContabilEmpresa)).all() == []
            repeated = rollback_backfill(session, applied.run_id)
            assert repeated.rolled_back == 1
    finally:
        engine.dispose()


def test_rollback_refuses_identity_changed_after_backfill(tmp_path):
    engine = _database(tmp_path)
    try:
        with Session(engine) as session:
            _linked_account(session)
            applied = apply_backfill(session)
            identity = session.scalar(select(ContaContabilEmpresa))
            identity.nome = "Alterada depois do backfill"
            session.commit()

            result = rollback_backfill(session, applied.run_id)

            assert result.rollback_blocked == 1
            assert identity.nome == "Alterada depois do backfill"
    finally:
        engine.dispose()


def test_partial_failure_is_recorded_and_a_later_run_completes_remaining_link(
    tmp_path,
):
    engine = _database(tmp_path)
    try:
        with Session(engine) as session:
            empresa, _ = _linked_account(session)
            second = ContaContabil(
                codigo=20002,
                classificacao="2.2",
                nome="Conta com falha transitória",
                tipo="A",
                grau=2,
            )
            session.add(second)
            session.flush()
            session.add(
                EmpresaContaContabil(
                    empresa_id=empresa.id,
                    conta_codigo=second.codigo,
                    quantidade_lancamentos=1,
                    ultima_utilizacao=date(2026, 2, 1),
                )
            )
            session.commit()
            session.execute(
                text(
                    """CREATE TRIGGER fail_one_backfill BEFORE INSERT
                    ON contas_contabeis_empresas WHEN NEW.codigo = 20002
                    BEGIN SELECT RAISE(ABORT, 'synthetic failure'); END"""
                )
            )
            session.commit()

            first = apply_backfill(session)

            assert first.eligible == 2
            assert first.created == 1
            assert first.failed == 1
            execution = session.get(BackfillContasContabeisExecucao, first.run_id)
            assert execution.status == "partial"
            failed_item = session.scalar(
                select(BackfillContasContabeisItem).where(
                    BackfillContasContabeisItem.execucao_id == first.run_id,
                    BackfillContasContabeisItem.resultado == "failed",
                )
            )
            assert failed_item.error_code == "IntegrityError"

            session.execute(text("DROP TRIGGER fail_one_backfill"))
            session.commit()
            resumed = apply_backfill(session)

            assert resumed.created == 1
            assert resumed.already_present == 1
            assert resumed.failed == 0
            assert len(session.scalars(select(ContaContabilEmpresa)).all()) == 2
    finally:
        engine.dispose()


def test_missing_legacy_catalog_account_is_reported_ineligible(tmp_path):
    engine = _database(tmp_path)
    try:
        with Session(engine) as session:
            empresa, _ = _linked_account(session)
            session.add(
                EmpresaContaContabil(
                    empresa_id=empresa.id,
                    conta_codigo=99999,
                    quantidade_lancamentos=0,
                    ultima_utilizacao=date(2026, 2, 1),
                )
            )
            session.commit()

            result = apply_backfill(session)

            assert result.created == 1
            assert result.ineligible == 1
    finally:
        engine.dispose()


def test_rollback_refuses_identity_with_relational_dependents(tmp_path):
    engine = _database(tmp_path)
    try:
        with Session(engine) as session:
            _linked_account(session)
            applied = apply_backfill(session)
            identity = session.scalar(select(ContaContabilEmpresa))
            session.execute(
                text(
                    """CREATE TABLE dependent_accounts (
                        id INTEGER PRIMARY KEY,
                        identity_id INTEGER REFERENCES contas_contabeis_empresas(id)
                    )"""
                )
            )
            session.execute(
                text(
                    "INSERT INTO dependent_accounts (identity_id) VALUES (:identity_id)"
                ),
                {"identity_id": identity.id},
            )
            session.commit()

            result = rollback_backfill(session, applied.run_id)

            assert result.rollback_blocked == 1
            assert session.get(ContaContabilEmpresa, identity.id) is not None
    finally:
        engine.dispose()


def test_cli_preflight_emits_sanitized_json_summary(tmp_path, monkeypatch, capsys):
    engine = _database(tmp_path)
    try:
        with Session(engine) as session:
            _linked_account(session)
        monkeypatch.setattr(backfill_company_accounts.settings, "DATABASE_URL", str(engine.url))

        assert backfill_company_accounts.main(["preflight"]) == 0

        output = capsys.readouterr().out
        assert '"eligible": 1' in output
        assert "Banco legado" not in output
        assert "10046" not in output
    finally:
        engine.dispose()


def test_cli_refuses_mutation_when_app_environment_is_production(
    tmp_path, monkeypatch
):
    engine = _database(tmp_path)
    try:
        monkeypatch.setattr(backfill_company_accounts.settings, "DATABASE_URL", str(engine.url))
        monkeypatch.setenv("APP_ENV", "prod")

        try:
            backfill_company_accounts.main(["apply"])
        except SystemExit as exc:
            assert exc.code == 2
        else:
            raise AssertionError("production mutation should be rejected")

        with Session(engine) as session:
            assert session.scalars(select(BackfillContasContabeisExecucao)).all() == []
    finally:
        engine.dispose()


def test_cli_apply_and_rollback_use_execution_id_without_exposing_account_data(
    tmp_path, monkeypatch, capsys
):
    engine = _database(tmp_path)
    try:
        with Session(engine) as session:
            _linked_account(session)
        monkeypatch.setattr(backfill_company_accounts.settings, "DATABASE_URL", str(engine.url))
        monkeypatch.setenv("APP_ENV", "hml")

        assert backfill_company_accounts.main(["apply"]) == 0
        applied_output = capsys.readouterr().out
        assert '"created": 1' in applied_output
        assert "Banco legado" not in applied_output
        execution_id = json.loads(applied_output)["run_id"]

        assert backfill_company_accounts.main(
            ["rollback", "--run-id", execution_id]
        ) == 0
        rollback_output = capsys.readouterr().out
        assert '"rolled_back": 1' in rollback_output
        assert "10046" not in rollback_output
        with Session(engine) as session:
            assert session.scalars(select(ContaContabilEmpresa)).all() == []
    finally:
        engine.dispose()
