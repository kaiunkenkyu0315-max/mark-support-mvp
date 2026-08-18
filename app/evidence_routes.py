"""証跡ファイルの共通アップロード・参照ルート。"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, RedirectResponse

from app import company_profile
from app.evidence_store import get_default_evidence_store
from app.operational_gate import operational_control_is_adopted

router = APIRouter(prefix="/evidence", tags=["evidence"])


@dataclass(frozen=True)
class EvidenceAreaConfig:
    redirect_url: str
    label: str
    control_id: str | None = None


AREA_CONFIGS = {
    "education": EvidenceAreaConfig("/education", "教育管理", "education"),
    "vendor_management": EvidenceAreaConfig("/vendors", "委託先管理", "vendor_management"),
    "internal_audit": EvidenceAreaConfig("/pms-review", "内部監査"),
    "management_review": EvidenceAreaConfig("/pms-review", "マネジメントレビュー"),
}


def _config(area: str) -> EvidenceAreaConfig:
    config = AREA_CONFIGS.get(area)
    if config is None:
        raise HTTPException(status_code=404, detail="Not Found")
    return config


@router.post("/{area}/upload")
async def upload_evidence(area: str, file: UploadFile = File(...)) -> RedirectResponse:
    config = _config(area)
    if config.control_id and not operational_control_is_adopted(config.control_id):
        return RedirectResponse(url=config.redirect_url, status_code=303)

    try:
        content = await file.read()
        get_default_evidence_store().save(
            area,
            file.filename or "",
            content,
            file.content_type,
            fiscal_year=company_profile.get_state().fiscal_year,
        )
    except ValueError as exc:
        return RedirectResponse(
            url=f"{config.redirect_url}?flash={quote(str(exc))}",
            status_code=303,
        )
    return RedirectResponse(
        url=(
            f"{config.redirect_url}?flash="
            f"{quote(f'{config.label}の証跡ファイルを添付しました。添付だけでは業務工程は完了になりません。')}"
        ),
        status_code=303,
    )


@router.get("/{area}/{evidence_id}")
def download_evidence(area: str, evidence_id: str) -> FileResponse:
    _config(area)
    found = get_default_evidence_store().get(area, evidence_id)
    if found is None:
        raise HTTPException(status_code=404, detail="Not Found")
    item, path = found
    return FileResponse(
        path,
        media_type=item.content_type,
        filename=item.original_name,
    )
