import hashlib
import os
from pathlib import Path

from pwdlib import PasswordHash
from sqlalchemy import create_engine, or_, select
from sqlalchemy.orm import Session, sessionmaker

from core.models import (
    Empresa,
    LoteImportacaoMovimentoOperacional,
    LoteImportacaoRazao,
    Usuario,
    UsuarioEmpresaPermissao,
)
from core.movimentos_operacionais_importer import import_movimentos_operacionais
from core.plano_contas_importer import import_plano_contas
from core.plano_contas_parser import parse_plano_contas_xlsx
from core.razao_importer import import_razao


password_hash = PasswordHash.recommended()
COMPANY_CNPJ = "22333444000155"
COMPANY_NAME = "EMPRESA MODELO HOMOLOGACAO LTDA"
COMPANY_DOMAIN_CODE = 7701


class UnsafeHomologacaoEnvironmentError(RuntimeError):
    pass


class SeedHomologacaoConflictError(RuntimeError):
    pass


class SeedHomologacaoConfigurationError(RuntimeError):
    pass


def ensure_hml_environment(app_env: str | None) -> None:
    if app_env != "hml":
        raise UnsafeHomologacaoEnvironmentError(
            "Seed recusado: APP_ENV deve ser hml."
        )


def seed_homologacao(
    *,
    app_env: str | None,
    database_url: str,
    admin_password: str,
    operator_password: str,
    company_api_key: str,
    fixtures_dir: str | Path,
    engine=None,
) -> None:
    ensure_hml_environment(app_env)
    connectable = engine if engine is not None else create_engine(database_url)
    SessionFactory = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=connectable,
    )
    fixtures_path = Path(fixtures_dir)

    with SessionFactory.begin() as session:
        empresa = _get_or_create_company(session, company_api_key)
        admin = _get_or_create_user(
            session,
            nome="ADMIN MODELO HOMOLOGACAO",
            login="admin.hml",
            email="admin.hml@example.invalid",
            papel="admin",
            password=admin_password,
        )
        operator = _get_or_create_user(
            session,
            nome="OPERADOR MODELO HOMOLOGACAO",
            login="operador.hml",
            email="operador.hml@example.invalid",
            papel="operador",
            password=operator_password,
        )
        _ensure_company_permission(session, operator, empresa)

        contas = parse_plano_contas_xlsx(fixtures_path / "plano_contas_hml.xlsx")
        import_plano_contas(session, contas)

        razao_path = fixtures_path / "razao_hml.xlsx"
        if not _has_completed_import(
            session,
            LoteImportacaoRazao,
            empresa.id,
            razao_path,
        ):
            import_razao(
                session,
                razao_path,
                empresa_id=empresa.id,
                usuario_id=admin.id,
                original_filename=razao_path.name,
            )

        movimentos_path = fixtures_path / "movimentos_operacionais_hml.xlsx"
        if not _has_completed_import(
            session,
            LoteImportacaoMovimentoOperacional,
            empresa.id,
            movimentos_path,
        ):
            import_movimentos_operacionais(
                session,
                movimentos_path,
                empresa_id=empresa.id,
                usuario_id=admin.id,
                original_filename=movimentos_path.name,
            )


def _get_or_create_company(session: Session, company_api_key: str) -> Empresa:
    empresa = session.execute(
        select(Empresa).where(Empresa.cnpj_cpf == COMPANY_CNPJ)
    ).scalar_one_or_none()
    if empresa is not None:
        if (
            empresa.nome_empresa != COMPANY_NAME
            or empresa.cod_dominio != COMPANY_DOMAIN_CODE
        ):
            raise SeedHomologacaoConflictError(
                "Empresa HML existente diverge da identidade sanitizada."
            )
        return empresa

    empresa = Empresa(
        nome_empresa=COMPANY_NAME,
        cnpj_cpf=COMPANY_CNPJ,
        api_key=company_api_key,
        cod_dominio=COMPANY_DOMAIN_CODE,
        is_active=True,
    )
    session.add(empresa)
    session.flush()
    return empresa


def _get_or_create_user(
    session: Session,
    *,
    nome: str,
    login: str,
    email: str,
    papel: str,
    password: str,
) -> Usuario:
    usuario = session.execute(
        select(Usuario).where(
            or_(Usuario.login == login, Usuario.email == email)
        )
    ).scalar_one_or_none()
    if usuario is not None:
        if usuario.login != login or usuario.email != email or usuario.papel != papel:
            raise SeedHomologacaoConflictError(
                f"Usuario HML existente diverge da identidade esperada: {login}."
            )
        return usuario

    usuario = Usuario(
        nome=nome,
        login=login,
        email=email,
        senha_hash=password_hash.hash(password),
        papel=papel,
        is_active=True,
    )
    session.add(usuario)
    session.flush()
    return usuario


def _ensure_company_permission(
    session: Session,
    operator: Usuario,
    empresa: Empresa,
) -> None:
    permissao = session.execute(
        select(UsuarioEmpresaPermissao).where(
            UsuarioEmpresaPermissao.usuario_id == operator.id,
            UsuarioEmpresaPermissao.empresa_id == empresa.id,
        )
    ).scalar_one_or_none()
    if permissao is None:
        session.add(
            UsuarioEmpresaPermissao(
                usuario_id=operator.id,
                empresa_id=empresa.id,
                permissao="operacao",
            )
        )
        session.flush()
        return

    permissao.permissao = "operacao"


def _has_completed_import(
    session: Session,
    lote_model,
    empresa_id: int,
    fixture_path: Path,
) -> bool:
    digest = hashlib.sha256(fixture_path.read_bytes()).hexdigest()
    file_hash = f"sha256:{digest}"
    lote = session.execute(
        select(lote_model).where(
            lote_model.empresa_id == empresa_id,
            lote_model.file_hash == file_hash,
            lote_model.status.in_(["completed", "completed_with_warnings"]),
        )
    ).scalar_one_or_none()
    return lote is not None


def _required_environment() -> dict[str, str]:
    names = (
        "DATABASE_URL",
        "HML_ADMIN_PASSWORD",
        "HML_OPERATOR_PASSWORD",
        "HML_COMPANY_API_KEY",
    )
    values = {name: os.getenv(name, "").strip() for name in names}
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise SeedHomologacaoConfigurationError(
            "Variaveis obrigatorias ausentes: " + ", ".join(missing) + "."
        )
    return values


def main() -> None:
    try:
        app_env = os.getenv("APP_ENV")
        ensure_hml_environment(app_env)
        environment = _required_environment()
        seed_homologacao(
            app_env=app_env,
            database_url=environment["DATABASE_URL"],
            admin_password=environment["HML_ADMIN_PASSWORD"],
            operator_password=environment["HML_OPERATOR_PASSWORD"],
            company_api_key=environment["HML_COMPANY_API_KEY"],
            fixtures_dir=(
                Path(__file__).resolve().parents[1]
                / "tests"
                / "fixtures"
                / "homologacao"
            ),
        )
    except (
        SeedHomologacaoConfigurationError,
        UnsafeHomologacaoEnvironmentError,
    ) as exc:
        raise SystemExit(str(exc)) from exc

    print("Seed de homologacao concluido com sucesso.")


if __name__ == "__main__":
    main()
