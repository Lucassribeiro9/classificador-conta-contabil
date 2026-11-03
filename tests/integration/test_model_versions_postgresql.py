"""PostgreSQL lifecycle, immutable evidence, and concurrent promotions."""

from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from core.model_versions import ModelLifecycleError, change_active_version
from core.models import DatasetManifest, Empresa, ModelVersion
from tests.integration.test_postgresql_integration import ROOT, _postgres_database_url

pytestmark = pytest.mark.integration_postgres


def test_model_version_evidence_is_immutable_and_concurrent_promotions_keep_one_active(tmp_path):
    url = _postgres_database_url()
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")
    engine = create_engine(url)
    suffix = uuid4().hex[:10]
    try:
        with Session(engine) as session:
            company = Empresa(
                nome_empresa=f"Model version test {suffix}",
                api_key=f"model-version-{suffix}",
                cnpj_cpf=f"{int(suffix, 16) % 10**14:014d}",
                cod_dominio=int(suffix, 16) % 2_000_000_000,
            )
            session.add(company)
            session.flush()
            manifest = DatasetManifest(
                empresa_id=company.id, content_hash="0" * 64, content={}
            )
            session.add(manifest)
            session.flush()
            versions = []
            for _ in range(2):
                version = ModelVersion(
                    empresa_id=company.id, manifest_id=manifest.id,
                    status="candidate", threshold=0.70,
                    metrics={"macro_f1": 1.0, "per_class_f1": {"1": 1.0}},
                    evaluation={"valid": True, "method": "holdout"},
                    critical_classes=[1],
                )
                session.add(version)
                session.flush()
                data = f"artifact-{version.id}".encode()
                version.artifact_path = f"empresa_{company.id}/model_{version.id}.joblib"
                version.artifact_sha256 = sha256(data).hexdigest()
                path = tmp_path / version.artifact_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
                versions.append(version.id)
            company_id = company.id
            session.commit()

        def promote(version_id):
            with Session(engine) as session:
                try:
                    change_active_version(
                        session, company_id=company_id, version_id=version_id,
                        model_dir=tmp_path,
                    )
                    session.commit()
                    return True
                except ModelLifecycleError:
                    session.rollback()
                    return False

        with ThreadPoolExecutor(max_workers=2) as pool:
            assert sorted(pool.map(promote, versions)) == [False, True]

        with Session(engine) as session:
            active = session.scalars(select(ModelVersion).where(
                ModelVersion.empresa_id == company_id,
                ModelVersion.status == "active",
            )).all()
            assert len(active) == 1
            assert active[0].id in versions
            with pytest.raises(DBAPIError):
                with session.begin_nested():
                    session.execute(text(
                        "UPDATE model_versions SET artifact_sha256 = :hash WHERE id = :id"
                    ), {"hash": "f" * 64, "id": active[0].id})
            session.rollback()
    finally:
        engine.dispose()
