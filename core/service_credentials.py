from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from core.audit import record_audit_event
from core.config import settings
from core.models import IdentidadeServico


@dataclass(frozen=True)
class CredencialServicoEmitida:
    identidade_id: int
    identifier: str
    secret: str
    fingerprint: str


def emitir_credencial_servico(
    session: Session,
    *,
    identidade_id: int,
    actor_user_id: int | None = None,
) -> CredencialServicoEmitida:
    """Emite uma nova credencial para uma identidade de servico.

    O segredo puro e retornado somente nesta chamada. No banco ficam apenas
    hash HMAC e fingerprint; a auditoria registra metadados seguros sem o
    segredo.
    """
    identidade = _get_identidade(session, identidade_id)
    secret = _generate_secret(identidade.identifier)
    credential_hash = _credential_hash(secret)
    fingerprint = _credential_fingerprint(secret)

    identidade.credential_hash = credential_hash
    identidade.credential_fingerprint = fingerprint
    identidade.status = "ativa"
    identidade.updated_at = datetime.now()

    record_audit_event(
        session,
        event_type="service_credential.issued",
        user_id=actor_user_id,
        resource_id=str(identidade.id),
        metadata={
            "identidade_servico_id": identidade.id,
            "identifier": identidade.identifier,
            "credential_fingerprint": fingerprint,
        },
    )
    return CredencialServicoEmitida(
        identidade_id=identidade.id,
        identifier=identidade.identifier,
        secret=secret,
        fingerprint=fingerprint,
    )


def revogar_credencial_servico(
    session: Session,
    *,
    identidade_id: int,
    actor_user_id: int | None = None,
) -> IdentidadeServico:
    """Revoga a credencial atual de uma identidade de servico.

    A identidade permanece no banco para rastreabilidade, mas passa a falhar em
    novas autenticacoes. O evento de auditoria usa apenas fingerprint e dados da
    identidade.
    """
    identidade = _get_identidade(session, identidade_id)
    now = datetime.now()
    identidade.status = "revogada"
    identidade.revoked_at = now
    identidade.revoked_by_user_id = actor_user_id
    identidade.updated_at = now

    record_audit_event(
        session,
        event_type="service_credential.revoked",
        user_id=actor_user_id,
        resource_id=str(identidade.id),
        metadata={
            "identidade_servico_id": identidade.id,
            "identifier": identidade.identifier,
            "credential_fingerprint": identidade.credential_fingerprint,
        },
    )
    return identidade


def rotacionar_credencial_servico(
    session: Session,
    *,
    identidade_id: int,
    actor_user_id: int | None = None,
) -> CredencialServicoEmitida:
    """Substitui a credencial atual por uma nova.

    A rotacao invalida imediatamente o segredo anterior porque o hash e o
    fingerprint persistidos sao sobrescritos. O novo segredo puro e exibido
    apenas no retorno desta chamada.
    """
    identidade = _get_identidade(session, identidade_id)
    old_fingerprint = identidade.credential_fingerprint
    secret = _generate_secret(identidade.identifier)
    fingerprint = _credential_fingerprint(secret)

    identidade.credential_hash = _credential_hash(secret)
    identidade.credential_fingerprint = fingerprint
    identidade.status = "ativa"
    identidade.updated_at = datetime.now()
    identidade.revoked_at = None
    identidade.revoked_by_user_id = None

    record_audit_event(
        session,
        event_type="service_credential.rotated",
        user_id=actor_user_id,
        resource_id=str(identidade.id),
        metadata={
            "identidade_servico_id": identidade.id,
            "identifier": identidade.identifier,
            "previous_credential_fingerprint": old_fingerprint,
            "credential_fingerprint": fingerprint,
        },
    )
    return CredencialServicoEmitida(
        identidade_id=identidade.id,
        identifier=identidade.identifier,
        secret=secret,
        fingerprint=fingerprint,
    )


def identificar_credencial_servico(
    session: Session,
    secret: str,
) -> IdentidadeServico | None:
    """Identifica a credencial de servico sem exigir identidade ativa.

    A funcao valida fingerprint e hash HMAC. Ela permite que dependencias de
    autorizacao diferenciem segredo invalido de identidade existente porem
    inativa ou revogada, sem expor o segredo puro.
    """
    fingerprint = _credential_fingerprint(secret)
    identidade = (
        session.query(IdentidadeServico)
        .filter(IdentidadeServico.credential_fingerprint == fingerprint)
        .first()
    )
    if identidade is None:
        return None

    expected_hash = _credential_hash(secret)
    if not hmac.compare_digest(identidade.credential_hash, expected_hash):
        return None

    return identidade


def autenticar_credencial_servico(
    session: Session,
    secret: str,
) -> IdentidadeServico | None:
    """Valida um segredo de servico e retorna a identidade ativa correspondente.
    Retorna None se a credencial nao for valida ou estiver revogada."""
    identidade = identificar_credencial_servico(session, secret)
    if identidade is None:
        return None
    if identidade.status != "ativa":
        return None

    identidade.last_used_at = datetime.now()
    return identidade


def _get_identidade(session: Session, identidade_id: int) -> IdentidadeServico:
    """Busca a identidade de servico ou falha com erro claro de dominio."""
    identidade = session.get(IdentidadeServico, identidade_id)
    if identidade is None:
        raise ValueError("Identidade de servico nao encontrada")
    return identidade


def _generate_secret(identifier: str) -> str:
    """Gera segredo opaco com prefixo legivel e entropia criptografica."""
    return f"svc_{identifier}_{secrets.token_urlsafe(32)}"


def _credential_hash(secret: str) -> str:
    """Calcula hash HMAC-SHA256 nao reversivel para persistencia."""
    key = _service_credential_secret().encode("utf-8")
    digest = hmac.new(key, secret.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"hmac-sha256:{digest}"


def _credential_fingerprint(secret: str) -> str:
    """Calcula fingerprint curto para suporte e auditoria segura."""
    key = _service_credential_secret().encode("utf-8")
    digest = hmac.new(key, secret.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"fp_{digest[:16]}"


def _service_credential_secret() -> str:
    """Retorna o segredo servidor usado como chave HMAC das credenciais."""
    secret = settings.SERVICE_CREDENTIAL_SECRET
    if not secret:
        raise RuntimeError("SERVICE_CREDENTIAL_SECRET nao configurado")
    return secret
