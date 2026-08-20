import hashlib
import os
import tempfile
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Query,
    Response,
    UploadFile,
)
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from api.dependencies import (
    DB_DEPENDENCY,
    get_current_user,
    require_service_company_scope,
)
from core.service_credentials import identificar_credencial_servico
from api.schemas import (
    ClassificacaoMovimentoOperacionalResponse,
    ImportacaoMovimentoOperacionalResponse,
    MovimentoOperacionalFeedbackImportResponse,
    MovimentoOperacionalListResponse,
    MovimentoOperacionalLoteListResponse,
    MovimentoOperacionalResponse,
    MovimentoOperacionalReviewRequest,
)
from core.audit import record_audit_event
from core.models import (
    Empresa,
    LoteImportacaoMovimentoOperacional,
    MovimentoOperacionalImportado,
    IdentidadeServico,
    Usuario,
)
from core.movimentos_operacionais_exporter import (
    MovimentoOperacionalExportError,
    gerar_planilha_classificada,
)
from core.movimentos_operacionais_feedback_importer import (
    MovimentoOperacionalFeedbackImportError,
    importar_feedback_planilha_classificada,
)
from core.movimentos_operacionais_importer import (
    MovimentoOperacionalImportError,
    import_movimentos_operacionais,
)
from core.movimentos_operacionais_classification import (
    MovimentoOperacionalModelNotFound,
    classificar_movimentos_operacionais_pendentes,
)
from core.movimentos_operacionais_parser import MovimentoOperacionalParseError
from core.movimentos_operacionais_review import (
    MovimentoReviewError,
    review_movimento_operacional,
)
from core.movimentos_operacionais_snapshot import (
    LoteOperacionalSnapshotNotFound,
    build_lote_operacional_snapshot,
)


router = APIRouter(prefix="/companies/{company_id}/movimentos-operacionais")
XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _service_audit_metadata(identidade: IdentidadeServico, scope: str) -> dict:
    return {
        "actor_type": "service",
        "identidade_servico_id": identidade.id,
        "identifier": identidade.identifier,
        "credential_fingerprint": identidade.credential_fingerprint,
        "scope": scope,
    }


def _reject_ambiguous_roundtrip_auth(
    authorization: str | None, x_service_credential: str | None
) -> None:
    if authorization and x_service_credential:
        raise HTTPException(status_code=400, detail="Credenciais ambíguas")


def _get_current_user_from_authorization_header(
    authorization: str | None, db: Session
) -> Usuario:
    if not authorization:
        raise HTTPException(status_code=401, detail="Token ausente")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Token inválido")
    credentials = HTTPAuthorizationCredentials(scheme=scheme, credentials=token)
    return get_current_user(credentials=credentials, db=db)


def _ensure_human_download_access(
    current_user: Usuario, empresa: Empresa
) -> tuple[int, dict]:
    denial_detail = _movimentos_read_denial_detail(current_user, empresa.id)
    if denial_detail is not None:
        raise HTTPException(status_code=403, detail=denial_detail)
    return current_user.id, {"actor_type": "user"}


def _ensure_human_feedback_access(
    current_user: Usuario, empresa: Empresa
) -> tuple[int, dict]:
    denial_detail = _movimentos_permission_denial_detail(current_user, empresa.id)
    if denial_detail is not None:
        raise HTTPException(status_code=403, detail=denial_detail)
    return current_user.id, {"actor_type": "user"}


def _service_denial_reason(exc: HTTPException) -> str:
    detail = str(exc.detail)
    if "inativa" in detail:
        return "inactive_or_revoked"
    if "Escopo" in detail:
        return "insufficient_scope"
    if "empresa" in detail or "Acesso negado" in detail:
        return "access_denied"
    return "service_access_denied"


def _record_service_access_denied(
    db: Session,
    *,
    company_id: int,
    scope: str,
    secret: str,
    reason: str,
    resource_id: str | None = None,
) -> None:
    identidade = identificar_credencial_servico(db, secret)
    metadata = {"actor_type": "service", "scope": scope, "reason": reason}
    if identidade is not None:
        metadata.update(_service_audit_metadata(identidade, scope))
        metadata["reason"] = reason
    record_audit_event(
        db,
        event_type="operational_movements.service_access_denied",
        user_id=None,
        empresa_id=company_id,
        resource_id=resource_id,
        metadata=metadata,
    )
    db.commit()


def _ensure_roundtrip_lote_exists(db: Session, *, empresa_id: int, lote_id: int) -> None:
    lote = (
        db.query(LoteImportacaoMovimentoOperacional)
        .filter(
            LoteImportacaoMovimentoOperacional.id == lote_id,
            LoteImportacaoMovimentoOperacional.empresa_id == empresa_id,
        )
        .first()
    )
    if lote is None:
        raise HTTPException(status_code=404, detail="Lote operacional não encontrado")


def _require_roundtrip_service_context(
    db: Session,
    *,
    company_id: int,
    scope: str,
    x_service_credential: str,
):
    try:
        return require_service_company_scope(scope)(
            company_id=company_id,
            x_service_credential=x_service_credential,
            db=db,
        )
    except HTTPException as exc:
        if exc.status_code in {403, 404}:
            _record_service_access_denied(
                db,
                company_id=company_id,
                scope=scope,
                secret=x_service_credential,
                reason=_service_denial_reason(exc),
            )
        raise


@router.get("/lotes", response_model=MovimentoOperacionalLoteListResponse)
def list_company_operational_movement_lotes(
    company_id: int,
    status: str | None = Query(default=None),
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=500),
    current_user: Usuario = Depends(get_current_user),
    db: Session = DB_DEPENDENCY,
) -> MovimentoOperacionalLoteListResponse:
    """Lista lotes operacionais da empresa para diagnostico e revisao."""
    empresa = _ensure_company_for_operational_query(db, company_id)
    denial_detail = _movimentos_read_denial_detail(current_user, company_id)
    if denial_detail is not None:
        raise HTTPException(status_code=403, detail=denial_detail)

    query = (
        db.query(LoteImportacaoMovimentoOperacional)
        .filter(LoteImportacaoMovimentoOperacional.empresa_id == empresa.id)
        .order_by(LoteImportacaoMovimentoOperacional.id.asc())
    )
    if status is not None:
        query = query.filter(LoteImportacaoMovimentoOperacional.status == status)

    offset = (page - 1) * limit
    total = query.count()
    lotes = query.offset(offset).limit(limit).all()
    return MovimentoOperacionalLoteListResponse(
        items=lotes,
        total=total,
        page=page,
        limit=limit,
        has_next=offset + len(lotes) < total,
    )


@router.get(
    "/lotes/{lote_id}/movimentos",
    response_model=MovimentoOperacionalListResponse,
)
def list_company_operational_movements(
    company_id: int,
    lote_id: int,
    status: str | None = Query(default=None),
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=500),
    current_user: Usuario = Depends(get_current_user),
    db: Session = DB_DEPENDENCY,
) -> MovimentoOperacionalListResponse:
    """Lista movimentos de um lote da empresa, com filtro opcional por status."""
    empresa = _ensure_company_for_operational_query(db, company_id)
    denial_detail = _movimentos_read_denial_detail(current_user, company_id)
    if denial_detail is not None:
        raise HTTPException(status_code=403, detail=denial_detail)

    lote = (
        db.query(LoteImportacaoMovimentoOperacional)
        .filter(
            LoteImportacaoMovimentoOperacional.id == lote_id,
            LoteImportacaoMovimentoOperacional.empresa_id == empresa.id,
        )
        .first()
    )
    if lote is None:
        raise HTTPException(status_code=404, detail="Lote operacional não encontrado")

    query = (
        db.query(MovimentoOperacionalImportado)
        .filter(
            MovimentoOperacionalImportado.empresa_id == empresa.id,
            MovimentoOperacionalImportado.lote_id == lote_id,
        )
        .order_by(MovimentoOperacionalImportado.id.asc())
    )
    if status is not None:
        query = query.filter(MovimentoOperacionalImportado.status == status)

    offset = (page - 1) * limit
    total = query.count()
    movimentos = query.offset(offset).limit(limit).all()
    return MovimentoOperacionalListResponse(
        items=movimentos,
        total=total,
        page=page,
        limit=limit,
        has_next=offset + len(movimentos) < total,
    )


@router.get("/lotes/{lote_id}/planilha-classificada")
def download_company_operational_classified_sheet(
    company_id: int,
    lote_id: int,
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_service_credential: str | None = Header(
        default=None, alias="X-Service-Credential"
    ),
    db: Session = DB_DEPENDENCY,
) -> Response:
    """Baixa a planilha classificada de um lote operacional da empresa."""
    _reject_ambiguous_roundtrip_auth(authorization, x_service_credential)
    empresa = _ensure_company_for_operational_query(db, company_id)
    if x_service_credential:
        service_context = _require_roundtrip_service_context(
            db,
            company_id=company_id,
            scope="movimentos:download",
            x_service_credential=x_service_credential,
        )
        actor_user_id = None
        actor_metadata = _service_audit_metadata(
            service_context.identidade, "movimentos:download"
        )
    else:
        current_user = _get_current_user_from_authorization_header(authorization, db)
        actor_user_id, actor_metadata = _ensure_human_download_access(
            current_user, empresa
        )

    try:
        snapshot = build_lote_operacional_snapshot(
            db,
            empresa_id=empresa.id,
            lote_id=lote_id,
        )
        content = gerar_planilha_classificada(snapshot)
    except LoteOperacionalSnapshotNotFound as exc:
        if x_service_credential:
            _record_service_access_denied(
                db,
                company_id=company_id,
                scope="movimentos:download",
                secret=x_service_credential,
                reason="lote_not_found",
                resource_id=str(lote_id),
            )
        raise HTTPException(
            status_code=404,
            detail="Lote operacional não encontrado",
        ) from exc
    except MovimentoOperacionalExportError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    record_audit_event(
        db,
        event_type="operational_movements.classified_sheet_downloaded",
        user_id=actor_user_id,
        empresa_id=empresa.id,
        resource_id=str(lote_id),
        metadata={
            **actor_metadata,
            "lote_id": lote_id,
            "export_revision": snapshot.export_revision,
            "layout_version": snapshot.layout_version,
            "total_movimentos": len(snapshot.movimentos),
        },
    )
    db.commit()

    filename = _classified_sheet_filename(empresa.cnpj_cpf, lote_id)
    return Response(
        content=content,
        media_type=XLSX_MEDIA_TYPE,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.post(
    "/lotes/{lote_id}/planilha-classificada/feedback",
    response_model=MovimentoOperacionalFeedbackImportResponse,
)
def import_company_operational_classified_sheet_feedback(
    company_id: int,
    lote_id: int,
    file: UploadFile,
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_service_credential: str | None = Header(
        default=None, alias="X-Service-Credential"
    ),
    db: Session = DB_DEPENDENCY,
) -> MovimentoOperacionalFeedbackImportResponse:
    """Importa revisoes em lote da planilha classificada."""
    _reject_ambiguous_roundtrip_auth(authorization, x_service_credential)
    empresa = _ensure_company_for_operational_query(db, company_id)
    if x_service_credential:
        service_context = _require_roundtrip_service_context(
            db,
            company_id=company_id,
            scope="movimentos:feedback",
            x_service_credential=x_service_credential,
        )
        actor_user_id = None
        actor_metadata = _service_audit_metadata(
            service_context.identidade, "movimentos:feedback"
        )
    else:
        current_user = _get_current_user_from_authorization_header(authorization, db)
        actor_user_id, actor_metadata = _ensure_human_feedback_access(
            current_user, empresa
        )

    try:
        _ensure_roundtrip_lote_exists(db, empresa_id=empresa.id, lote_id=lote_id)
    except HTTPException as exc:
        if x_service_credential and exc.status_code == 404:
            _record_service_access_denied(
                db,
                company_id=company_id,
                scope="movimentos:feedback",
                secret=x_service_credential,
                reason="lote_not_found",
                resource_id=str(lote_id),
            )
        raise

    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Arquivo deve ser .xlsx")

    temp_path = _save_upload_to_temp_xlsx(file)
    try:
        resumo = importar_feedback_planilha_classificada(
            db,
            temp_path,
            empresa_id=empresa.id,
            lote_id=lote_id,
            usuario_id=actor_user_id,
            actor_metadata=actor_metadata,
        )
        db.commit()
        return MovimentoOperacionalFeedbackImportResponse.model_validate(
            resumo,
            from_attributes=True,
        )
    except MovimentoOperacionalFeedbackImportError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise
    finally:
        os.unlink(temp_path)


@router.post("/import", response_model=ImportacaoMovimentoOperacionalResponse)
def import_company_operational_movements(
    company_id: int,
    file: UploadFile,
    current_user: Usuario = Depends(get_current_user),
    db: Session = DB_DEPENDENCY,
) -> ImportacaoMovimentoOperacionalResponse:
    """Importa uma planilha operacional `.xlsx` para revisao por empresa.

    A rota valida autenticacao, permissao operacional na empresa, tipo do
    arquivo e delega as regras de dominio ao servico de importacao. Eventos de
    auditoria registram apenas metadados operacionais, sem historico/documento
    das linhas importadas.
    """
    temp_path = _save_upload_to_temp_xlsx(file)
    file_hash = _file_hash(temp_path)
    try:
        empresa = db.get(Empresa, company_id)
        if empresa is None:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")

        denial_detail = _movimentos_permission_denial_detail(current_user, company_id)
        if denial_detail is not None:
            record_audit_event(
                db,
                event_type="operational_movements.import_denied",
                user_id=current_user.id,
                empresa_id=company_id,
                metadata={
                    "file_hash": file_hash,
                    "reason": (
                        "insufficient_permission"
                        if denial_detail == "Permissão insuficiente"
                        else "access_denied"
                    ),
                },
            )
            db.commit()
            raise HTTPException(status_code=403, detail=denial_detail)

        if not file.filename or not file.filename.lower().endswith(".xlsx"):
            record_audit_event(
                db,
                event_type="operational_movements.import_failed",
                user_id=current_user.id,
                empresa_id=company_id,
                metadata={
                    "file_hash": file_hash,
                    "total_linhas": 0,
                    "total_importadas": 0,
                    "total_invalidas": 0,
                    "warnings": [],
                    "error_type": "InvalidFileType",
                    "error": "Arquivo deve ser .xlsx",
                    "reason": "invalid_file_type",
                },
            )
            db.commit()
            raise HTTPException(status_code=400, detail="Arquivo deve ser .xlsx")

        resumo = import_movimentos_operacionais(
            db,
            temp_path,
            empresa_id=company_id,
            usuario_id=current_user.id,
            original_filename=file.filename,
        )
        record_audit_event(
            db,
            event_type="operational_movements.imported",
            user_id=current_user.id,
            empresa_id=company_id,
            resource_id=str(resumo.lote_id),
            metadata={
                "file_hash": file_hash,
                "total_linhas": resumo.total_linhas,
                "total_importadas": resumo.total_importadas,
                "total_invalidas": resumo.total_invalidas,
                "warnings": resumo.warnings,
            },
        )
        db.commit()
    except (MovimentoOperacionalImportError, MovimentoOperacionalParseError) as exc:
        db.rollback()
        record_audit_event(
            db,
            event_type="operational_movements.import_failed",
            user_id=current_user.id,
            empresa_id=company_id,
            metadata={
                "file_hash": file_hash,
                "total_linhas": 0,
                "total_importadas": 0,
                "total_invalidas": 0,
                "warnings": [],
                "error_type": type(exc).__name__,
                "error": str(exc),
                "reason": _failure_reason(exc),
            },
        )
        db.commit()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise
    finally:
        os.unlink(temp_path)

    return ImportacaoMovimentoOperacionalResponse(**resumo.__dict__)


@router.post(
    "/classificar",
    response_model=ClassificacaoMovimentoOperacionalResponse,
)
def classify_company_pending_operational_movements(
    company_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: Session = DB_DEPENDENCY,
) -> ClassificacaoMovimentoOperacionalResponse:
    """Classifica movimentos operacionais pendentes sem aprovar automaticamente."""
    empresa = _ensure_company_for_operational_query(db, company_id)
    denial_detail = _movimentos_permission_denial_detail(current_user, empresa.id)
    if denial_detail is not None:
        raise HTTPException(status_code=403, detail=denial_detail)

    try:
        result = classificar_movimentos_operacionais_pendentes(
            db,
            empresa_id=empresa.id,
        )
        db.commit()
        return ClassificacaoMovimentoOperacionalResponse(**result)
    except MovimentoOperacionalModelNotFound as exc:
        db.commit()
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/lotes/{lote_id}/movimentos/{movimento_id}/review",
    response_model=MovimentoOperacionalResponse,
)
def review_company_operational_movement(
    company_id: int,
    lote_id: int,
    movimento_id: int,
    request: MovimentoOperacionalReviewRequest,
    current_user: Usuario = Depends(get_current_user),
    db: Session = DB_DEPENDENCY,
) -> MovimentoOperacionalResponse:
    """Revisa (aprova, corrige, rejeita) um movimento operacional individual."""
    empresa = _ensure_company_for_operational_query(db, company_id)
    denial_detail = _movimentos_permission_denial_detail(current_user, empresa.id)
    if denial_detail is not None:
        raise HTTPException(status_code=403, detail=denial_detail)

    try:
        mov = review_movimento_operacional(
            db=db,
            movimento_id=movimento_id,
            empresa_id=empresa.id,
            usuario_id=current_user.id,
            action=request.action,
            conta_final=request.conta_final,
        )
        if mov.lote_id != lote_id:
            raise HTTPException(status_code=404, detail="Movimento não encontrado neste lote")
            
        db.commit()
        return MovimentoOperacionalResponse.model_validate(mov)
    except MovimentoReviewError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))



def _classified_sheet_filename(cnpj_cpf: str, lote_id: int) -> str:
    """Monta nome de download sem dados livres da empresa."""
    documento = "".join(char for char in cnpj_cpf if char.isdigit())
    return f"{documento}-lote{lote_id}-classificada.xlsx"


def _save_upload_to_temp_xlsx(file: UploadFile) -> str:
    """Salva o upload em arquivo temporario para leitura pelo importador."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as temp_file:
        temp_file.write(file.file.read())
        return temp_file.name


def _file_hash(path: str) -> str:
    """Calcula o hash sha256 do arquivo temporario recebido."""
    digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    return f"sha256:{digest}"


def _movimentos_permission_denial_detail(
    user: Usuario,
    company_id: int,
) -> str | None:
    """Retorna o motivo de bloqueio quando usuario nao pode importar."""
    if user.papel == "admin":
        return None

    permission_link = next(
        (
            permission
            for permission in user.permissoes_empresas
            if permission.empresa_id == company_id
        ),
        None,
    )
    if permission_link is None:
        return "Acesso negado"
    if permission_link.permissao not in {"operacao", "admin_empresa"}:
        return "Permissão insuficiente"
    return None


def _movimentos_read_denial_detail(
    user: Usuario,
    company_id: int,
) -> str | None:
    """Retorna o motivo de bloqueio quando usuario nao pode consultar."""
    if user.papel == "admin":
        return None

    permission_link = next(
        (
            permission
            for permission in user.permissoes_empresas
            if permission.empresa_id == company_id
        ),
        None,
    )
    if permission_link is None:
        return "Acesso negado"
    return None


def _ensure_company_for_operational_query(db: Session, company_id: int) -> Empresa:
    """Carrega empresa da rota ou retorna erro HTTP estavel."""
    empresa = db.get(Empresa, company_id)
    if empresa is None:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    return empresa


def _failure_reason(exc: Exception) -> str:
    """Traduz excecoes conhecidas em motivos estaveis para auditoria."""
    if (
        isinstance(exc, MovimentoOperacionalImportError)
        and "Arquivo ja importado" in str(exc)
    ):
        return "duplicate_file_hash"
    if (
        isinstance(exc, MovimentoOperacionalImportError)
        and "CNPJ da planilha operacional nao corresponde" in str(exc)
    ):
        return "company_mismatch"
    return "invalid_file"
