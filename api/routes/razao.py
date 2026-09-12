from fastapi import APIRouter, Depends, HTTPException, Query, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from api.dependencies import (
    DB_DEPENDENCY,
    get_current_user,
    require_company_access,
    require_company_or_service_access,
    require_global_admin,
)
from api.schemas import (
    ImportacaoRazaoResponse,
    RazaoFechamentoListResponse,
    RazaoFechamentoResponse,
    RazaoLancamentoListResponse,
    RazaoLoteListResponse,
    RazaoLoteResponse,
    RazaoLoteStatusResponse,
    RazaoWarningListResponse,
)
from core.audit import record_audit_event
from core.models import (
    Empresa,
    FechamentoRazaoMensal,
    LancamentoRazaoNormalizado,
    LoteImportacaoRazao,
    Usuario,
    WarningImportacaoRazao,
)
from core.config import settings
from core.razao_importer import warning_code_from_message
from core.razao_parser import RazaoParseError, parse_razao_metadata
from core.razao_storage import (
    InsufficientCapacity,
    RazaoStorage,
    TemporaryFileBusy,
    TemporaryFileUnavailable,
    UploadTooLarge,
)


router = APIRouter(prefix="/companies/{company_id}/razao")
admin_router = APIRouter(prefix="/admin/razao")


def get_razao_storage(db: Session = DB_DEPENDENCY) -> RazaoStorage:
    return RazaoStorage.from_settings(
        settings,
        sessions=sessionmaker(
            autocommit=False, autoflush=False, bind=db.get_bind()
        ),
    )


@router.get("/lotes", response_model=RazaoLoteListResponse)
def list_company_razao_lotes(
    company_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=500),
    empresa: Empresa = Depends(require_company_access("leitura")),
    db: Session = DB_DEPENDENCY,
) -> RazaoLoteListResponse:
    query = (
        db.query(LoteImportacaoRazao)
        .filter(LoteImportacaoRazao.empresa_id == empresa.id)
        .order_by(LoteImportacaoRazao.id.asc())
    )
    offset = (page - 1) * limit
    total = query.count()
    lotes = query.offset(offset).limit(limit).all()
    return RazaoLoteListResponse(
        items=[
            RazaoLoteResponse(
                id=lote.id,
                empresa_id=lote.empresa_id,
                original_filename=lote.original_filename,
                status=lote.status,
                total_linhas=lote.total_linhas,
                total_importadas=lote.total_importadas,
                total_invalidas=lote.total_invalidas,
                warnings_saldo_total=len(_balance_warnings(lote.warnings_metadata)),
                created_at=lote.created_at,
            )
            for lote in lotes
        ],
        total=total,
        page=page,
        limit=limit,
        has_next=offset + len(lotes) < total,
    )


@router.get("/lotes/{lote_id}", response_model=RazaoLoteStatusResponse)
def get_company_razao_lote_status(
    company_id: int,
    lote_id: int,
    empresa: Empresa = Depends(require_company_access("leitura")),
    db: Session = DB_DEPENDENCY,
) -> RazaoLoteStatusResponse:
    lote = (
        db.query(LoteImportacaoRazao)
        .filter(
            LoteImportacaoRazao.id == lote_id,
            LoteImportacaoRazao.empresa_id == empresa.id,
        )
        .first()
    )
    if lote is None:
        raise HTTPException(status_code=404, detail="Lote de razão não encontrado")

    warning_totals = (lote.warnings_metadata or {}).get("totals_by_code", {})
    warning_summary = (
        {
            code: total
            for code, total in warning_totals.items()
            if isinstance(code, str) and type(total) is int and total >= 0
        }
        if isinstance(warning_totals, dict)
        else {}
    )
    return RazaoLoteStatusResponse(
        lote_id=lote.id,
        empresa_id=lote.empresa_id,
        status=lote.status,
        total_linhas=lote.total_linhas,
        linhas_processadas=lote.linhas_processadas,
        total_importadas=lote.total_importadas,
        total_invalidas=lote.total_invalidas,
        warnings_total=lote.warnings_total,
        warnings_summary=warning_summary,
        attempt_count=lote.attempt_count,
        tentativas=lote.tentativas,
        created_at=lote.created_at,
        updated_at=lote.updated_at,
        heartbeat_at=lote.heartbeat_at,
        failed_at=lote.failed_at,
        error_code=lote.error_code,
        error_message=lote.error_message,
        error_request_id=lote.error_request_id,
    )


@router.post(
    "/lotes/{lote_id}/retry",
    response_model=ImportacaoRazaoResponse,
    status_code=202,
)
def retry_company_razao_lote(
    company_id: int,
    lote_id: int,
    response: Response,
    empresa: Empresa = Depends(require_company_access("operacao")),
    current_user: Usuario = Depends(get_current_user),
    db: Session = DB_DEPENDENCY,
    storage: RazaoStorage = Depends(get_razao_storage),
) -> ImportacaoRazaoResponse:
    lote = (
        db.query(LoteImportacaoRazao)
        .filter(
            LoteImportacaoRazao.id == lote_id,
            LoteImportacaoRazao.empresa_id == empresa.id,
        )
        .first()
    )
    if lote is None:
        raise HTTPException(status_code=404, detail="Lote de razão não encontrado")
    if lote.status != "failed":
        raise HTTPException(
            status_code=409, detail="Lote não está disponível para repetição"
        )

    try:
        with storage.retry_guard(lote_id) as (retry_db, retry_lote, _stream):
            retry_lote.status = "queued"
            retry_lote.total_linhas = None
            retry_lote.linhas_processadas = 0
            retry_lote.total_importadas = 0
            retry_lote.total_invalidas = 0
            retry_lote.warnings_total = 0
            retry_lote.warnings_metadata = {"totals_by_code": {}}
            retry_lote.lease_token = None
            retry_lote.lease_owner = None
            retry_lote.lease_expires_at = None
            retry_lote.heartbeat_at = None
            retry_lote.error_code = None
            retry_lote.error_message = None
            retry_lote.error_request_id = None
            retry_lote.failed_at = None
            record_audit_event(
                retry_db,
                event_type="razao.job.manual_retry",
                user_id=current_user.id,
                empresa_id=company_id,
                resource_id=str(lote_id),
                metadata={"attempt_count": retry_lote.attempt_count},
            )
    except TemporaryFileBusy as exc:
        raise HTTPException(
            status_code=409, detail="Lote não está disponível para repetição"
        ) from exc
    except TemporaryFileUnavailable as exc:
        db.expire_all()
        current_status = db.scalar(
            select(LoteImportacaoRazao.status).where(
                LoteImportacaoRazao.id == lote_id,
                LoteImportacaoRazao.empresa_id == company_id,
            )
        )
        if current_status is not None and current_status != "failed":
            raise HTTPException(
                status_code=409, detail="Lote não está disponível para repetição"
            ) from exc
        raise HTTPException(
            status_code=410, detail="Arquivo temporário não está mais disponível"
        ) from exc

    response.headers["Retry-After"] = "3"
    return ImportacaoRazaoResponse(
        lote_id=lote_id,
        status="queued",
        status_url=f"/api/v1/companies/{company_id}/razao/lotes/{lote_id}",
    )


@router.get(
    "/lotes/{lote_id}/warnings",
    response_model=RazaoWarningListResponse,
)
def list_company_razao_warnings(
    company_id: int,
    lote_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    codigo: str | None = Query(None),
    linha: int | None = Query(None, ge=1),
    empresa: Empresa = Depends(
        require_company_or_service_access("leitura", "empresas:read")
    ),
    db: Session = DB_DEPENDENCY,
) -> RazaoWarningListResponse:
    lote = (
        db.query(LoteImportacaoRazao)
        .filter(
            LoteImportacaoRazao.id == lote_id,
            LoteImportacaoRazao.empresa_id == empresa.id,
        )
        .first()
    )
    if lote is None:
        raise HTTPException(status_code=404, detail="Lote de razão não encontrado")
    _ensure_razao_results_available(lote)

    legacy_warnings = (lote.warnings_metadata or {}).get("warnings")
    if isinstance(legacy_warnings, list):
        warnings = _adapt_legacy_warnings(legacy_warnings)
        if codigo is not None:
            warnings = [warning for warning in warnings if warning["codigo"] == codigo]
        if linha is not None:
            warnings = [warning for warning in warnings if warning["linha"] == linha]
        offset = (page - 1) * limit
        items = warnings[offset : offset + limit]
        return RazaoWarningListResponse(
            source="legacy",
            items=items,
            total=len(warnings),
            page=page,
            limit=limit,
            has_next=offset + len(items) < len(warnings),
        )

    query = db.query(WarningImportacaoRazao).filter(
        WarningImportacaoRazao.lote_id == lote.id
    )
    if codigo is not None:
        query = query.filter(WarningImportacaoRazao.codigo == codigo)
    if linha is not None:
        query = query.filter(WarningImportacaoRazao.linha == linha)
    query = query.order_by(WarningImportacaoRazao.id.asc())
    offset = (page - 1) * limit
    total = query.count()
    warnings = query.offset(offset).limit(limit).all()
    return RazaoWarningListResponse(
        source="normalized",
        items=[
            {
                "linha": warning.linha,
                "codigo": warning.codigo,
                "mensagem": warning.mensagem,
                "detalhes": _safe_warning_details(warning.detalhes),
            }
            for warning in warnings
        ],
        total=total,
        page=page,
        limit=limit,
        has_next=offset + len(warnings) < total,
    )


def _adapt_legacy_warnings(warnings: list) -> list[dict]:
    adapted = []
    for warning in warnings:
        if not isinstance(warning, dict):
            continue
        explicit_message = warning.get("mensagem")
        messages = (
            [explicit_message]
            if explicit_message is not None
            else warning.get("warnings") or ["Aviso do razao."]
        )
        if not isinstance(messages, list):
            messages = [messages]
        linha = warning.get("linha")
        if type(linha) is not int or linha < 1:
            linha = None
        for raw_message in messages:
            message = str(raw_message)
            adapted.append(
                {
                    "linha": linha,
                    "codigo": str(
                        warning.get("codigo") or warning_code_from_message(message)
                    ),
                    "mensagem": message,
                    "detalhes": _safe_warning_details(warning.get("detalhes")),
                }
            )
    return adapted


def _safe_warning_details(details) -> dict:
    if not isinstance(details, dict):
        return {}
    safe = {}
    for key in ("bloco_id", "conta_codigo"):
        if key in details:
            safe[key] = details[key]
    for key in ("saldo_calculado", "saldo_observado"):
        value = details.get(key)
        if isinstance(value, dict):
            safe[key] = {
                nested_key: value[nested_key]
                for nested_key in (
                    "fonte",
                    "valor_original",
                    "valor_decimal",
                    "natureza",
                )
                if nested_key in value
            }
    return safe


@router.get("/lotes/{lote_id}/lancamentos", response_model=RazaoLancamentoListResponse)
def list_company_razao_lancamentos(
    company_id: int,
    lote_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=500),
    empresa: Empresa = Depends(require_company_access("leitura")),
    db: Session = DB_DEPENDENCY,
) -> RazaoLancamentoListResponse:
    lote = (
        db.query(LoteImportacaoRazao)
        .filter(
            LoteImportacaoRazao.id == lote_id,
            LoteImportacaoRazao.empresa_id == empresa.id,
        )
        .first()
    )
    if lote is None:
        raise HTTPException(status_code=404, detail="Lote de razão não encontrado")
    _ensure_razao_results_available(lote)

    query = (
        db.query(LancamentoRazaoNormalizado)
        .filter(
            LancamentoRazaoNormalizado.empresa_id == empresa.id,
            LancamentoRazaoNormalizado.lote_id == lote_id,
        )
        .order_by(LancamentoRazaoNormalizado.id.asc())
    )
    offset = (page - 1) * limit
    total = query.count()
    lancamentos = query.offset(offset).limit(limit).all()
    return RazaoLancamentoListResponse(
        items=lancamentos,
        total=total,
        page=page,
        limit=limit,
        has_next=offset + len(lancamentos) < total,
    )


@router.get(
    "/lotes/{lote_id}/fechamentos",
    response_model=RazaoFechamentoListResponse,
)
def list_company_razao_fechamentos(
    company_id: int,
    lote_id: int,
    conta_codigo: int | None = Query(None),
    ano: int | None = Query(None),
    mes: int | None = Query(None, ge=1, le=12),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    empresa: Empresa = Depends(require_company_access("leitura")),
    db: Session = DB_DEPENDENCY,
) -> RazaoFechamentoListResponse:
    lote = (
        db.query(LoteImportacaoRazao)
        .filter(
            LoteImportacaoRazao.id == lote_id,
            LoteImportacaoRazao.empresa_id == empresa.id,
        )
        .first()
    )
    if lote is None:
        raise HTTPException(status_code=404, detail="Lote de razão não encontrado")
    _ensure_razao_results_available(lote)

    query = db.query(FechamentoRazaoMensal).filter(
        FechamentoRazaoMensal.empresa_id == empresa.id,
        FechamentoRazaoMensal.lote_id == lote_id,
    )
    if conta_codigo is not None:
        query = query.filter(FechamentoRazaoMensal.conta_codigo == conta_codigo)
    if ano is not None:
        query = query.filter(FechamentoRazaoMensal.ano == ano)
    if mes is not None:
        query = query.filter(FechamentoRazaoMensal.mes == mes)
    query = query.order_by(
        FechamentoRazaoMensal.conta_codigo.asc(),
        FechamentoRazaoMensal.ano.asc(),
        FechamentoRazaoMensal.mes.asc(),
        FechamentoRazaoMensal.id.asc(),
    )
    offset = (page - 1) * limit
    total = query.count()
    fechamentos = query.offset(offset).limit(limit).all()
    warnings_saldo = _balance_warnings(lote.warnings_metadata)
    warnings_saldo_total = len(warnings_saldo)
    return RazaoFechamentoListResponse(
        lote_id=lote.id,
        empresa_id=empresa.id,
        status=lote.status,
        warnings_saldo=warnings_saldo[:100],
        warnings_saldo_total=warnings_saldo_total,
        warnings_saldo_truncados=warnings_saldo_total > 100,
        items=[
            RazaoFechamentoResponse(
                id=fechamento.id,
                lote_id=fechamento.lote_id,
                empresa_id=fechamento.empresa_id,
                conta_codigo=fechamento.conta_codigo,
                ano=fechamento.ano,
                mes=fechamento.mes,
                saldo_observado_original=fechamento.saldo_observado_original,
                saldo_observado_decimal=fechamento.saldo_observado_decimal,
                saldo_observado_natureza=fechamento.saldo_observado_natureza,
                saldo_observado_fonte=fechamento.saldo_observado_fonte,
                saldo_calculado_decimal=fechamento.saldo_calculado_decimal,
                divergente=any(
                    warning.get("codigo") == "saldo_divergente"
                    for warning in fechamento.warnings_saldo
                ),
                warnings_saldo=fechamento.warnings_saldo,
                created_at=fechamento.created_at,
                updated_at=fechamento.updated_at,
            )
            for fechamento in fechamentos
        ],
        total=total,
        page=page,
        limit=limit,
        has_next=offset + len(fechamentos) < total,
    )


def _balance_warnings(source: dict | list | None) -> list[dict]:
    warnings = (
        source
        if isinstance(source, list)
        else (source or {}).get("warnings", [])
    )
    return [
        warning
        for warning in warnings
        if isinstance(warning, dict)
        and warning.get("codigo")
        in {"saldo_ausente", "saldo_invalido", "saldo_divergente"}
    ]


def _ensure_razao_results_available(lote: LoteImportacaoRazao) -> None:
    if lote.status in {"queued", "processing"}:
        raise HTTPException(
            status_code=409, detail="Resultados ainda não estão disponíveis"
        )


@router.post(
    "/import",
    response_model=ImportacaoRazaoResponse,
    status_code=202,
    responses={
        200: {"model": ImportacaoRazaoResponse},
        409: {"model": ImportacaoRazaoResponse},
    },
)
def import_company_razao(
    company_id: int,
    file: UploadFile,
    response: Response,
    current_user: Usuario = Depends(get_current_user),
    db: Session = DB_DEPENDENCY,
    storage: RazaoStorage = Depends(get_razao_storage),
) -> ImportacaoRazaoResponse:
    empresa = db.get(Empresa, company_id)
    if empresa is None:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    denial_detail = _razao_permission_denial_detail(current_user, company_id)
    if denial_detail is not None:
        record_audit_event(
            db,
            event_type="ledger.import_denied",
            user_id=current_user.id,
            empresa_id=company_id,
            metadata={
                "reason": (
                    "insufficient_permission"
                    if denial_detail == "Permissão insuficiente"
                    else "access_denied"
                )
            },
        )
        db.commit()
        raise HTTPException(status_code=403, detail=denial_detail)
    if not empresa.is_active:
        raise HTTPException(
            status_code=400,
            detail=(
                "empresa do razao esta inativa; reative a empresa antes de "
                "importar."
            ),
        )
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Arquivo deve ser .xlsx")

    try:
        with storage.admit(iter(lambda: file.file.read(65536), b"")) as upload:
            metadata = parse_razao_metadata(upload)
            if metadata.cnpj_cpf != empresa.cnpj_cpf:
                raise RazaoParseError("CNPJ do razao nao corresponde a empresa da importacao.")
            lote = db.query(LoteImportacaoRazao).filter_by(
                empresa_id=company_id, file_hash=upload.file_hash
            ).first()
            if lote is None:
                lote = LoteImportacaoRazao(
                    empresa_id=company_id, usuario_id=current_user.id,
                    original_filename=file.filename, file_hash=upload.file_hash,
                    status="queued",
                )
                db.add(lote)
                try:
                    db.flush()
                except IntegrityError:
                    db.rollback()
                    lote = db.query(LoteImportacaoRazao).filter_by(
                        empresa_id=company_id, file_hash=upload.file_hash
                    ).one()
                else:
                    upload.bind(db, lote)
            record_audit_event(
                db,
                event_type="ledger.import_received",
                user_id=current_user.id,
                empresa_id=company_id,
                resource_id=str(lote.id),
                metadata={"file_hash": upload.file_hash, "status": lote.status},
            )
            db.commit()
    except UploadTooLarge as exc:
        db.rollback()
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except InsufficientCapacity as exc:
        db.rollback()
        raise HTTPException(status_code=507, detail=str(exc)) from exc
    except RazaoParseError as exc:
        db.rollback()
        record_audit_event(
            db,
            event_type="ledger.import_failed",
            user_id=current_user.id,
            empresa_id=company_id,
            metadata={
                "error_type": type(exc).__name__,
                "reason": (
                    "company_mismatch" if "CNPJ" in str(exc) else "invalid_file"
                ),
            },
        )
        db.commit()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    status_url = f"/api/v1/companies/{company_id}/razao/lotes/{lote.id}"
    retry_url = f"{status_url}/retry" if lote.status == "failed" else None
    if lote.status in {"queued", "processing"}:
        response.status_code = 202
        response.headers["Retry-After"] = "3"
    elif lote.status in {"completed", "completed_with_warnings"}:
        response.status_code = 200
    else:
        response.status_code = 409
    return ImportacaoRazaoResponse(
        lote_id=lote.id,
        status=lote.status,
        status_url=status_url,
        retry_url=retry_url,
    )


def _razao_permission_denial_detail(user: Usuario, company_id: int) -> str | None:
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


@admin_router.delete("/lotes/{lote_id}", status_code=204)
def delete_ledger_import_batch(
    lote_id: int,
    admin: Usuario = Depends(require_global_admin),
    db: Session = DB_DEPENDENCY,
) -> None:
    lote = db.get(LoteImportacaoRazao, lote_id)
    if lote is None:
        raise HTTPException(status_code=404, detail="Lote de razão não encontrado")

    metadata = {
        "lote_id": lote.id,
        "original_filename": lote.original_filename,
        "file_hash": lote.file_hash,
        "status": lote.status,
        "created_at": lote.created_at.isoformat(),
    }
    record_audit_event(
        db,
        event_type="ledger.deleted",
        user_id=admin.id,
        empresa_id=lote.empresa_id,
        resource_id=str(lote.id),
        metadata=metadata,
    )
    db.delete(lote)
    db.commit()
    return None
