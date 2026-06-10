from __future__ import annotations

import argparse
import getpass
from dataclasses import dataclass

from pwdlib import PasswordHash
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from core.config import settings
from core.models import Usuario


@dataclass(frozen=True)
class BootstrapAdminResult:
    created: bool
    usuario_id: int | None = None


password_hash = PasswordHash.recommended()


def _find_existing_admin(session, login: str, email: str) -> Usuario | None:
    return session.execute(
        select(Usuario).where((Usuario.login == login) | (Usuario.email == email))
    ).scalar_one_or_none()


def bootstrap_admin(
    *,
    database_url: str,
    nome: str,
    login: str,
    email: str,
    password: str,
    engine=None,
) -> BootstrapAdminResult:
    connectable = engine if engine is not None else create_engine(database_url)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=connectable)

    with Session() as session:
        existing_user = _find_existing_admin(session, login, email)
        if existing_user is not None:
            return BootstrapAdminResult(created=False, usuario_id=existing_user.id)

        admin = Usuario(
            nome=nome,
            login=login,
            email=email,
            senha_hash=password_hash.hash(password),
            papel="admin",
            is_active=True,
        )
        session.add(admin)
        session.commit()
        session.refresh(admin)

    return BootstrapAdminResult(created=True, usuario_id=admin.id)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create the first internal admin user."
    )
    parser.add_argument("--nome", required=True, help="Nome do usuario admin.")
    parser.add_argument("--login", required=True, help="Login unico do admin.")
    parser.add_argument("--email", required=True, help="Email unico do admin.")
    parser.add_argument(
        "--database-url",
        default=settings.DATABASE_URL,
        help="Database URL alvo. Por padrao usa DATABASE_URL.",
    )
    args = parser.parse_args()

    password = getpass.getpass("Senha do admin: ")
    confirmation = getpass.getpass("Confirme a senha do admin: ")
    if password != confirmation:
        parser.error("As senhas informadas nao conferem.")

    result = bootstrap_admin(
        database_url=args.database_url,
        nome=args.nome,
        login=args.login,
        email=args.email,
        password=password,
    )

    if result.created:
        print(f"Admin created: id={result.usuario_id}, login={args.login}")
    else:
        print(f"Admin already exists: id={result.usuario_id}, login/email already used")


if __name__ == "__main__":
    main()
