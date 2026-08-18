"""証跡ファイルのアップロード・参照ルート。"""

from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, RedirectResponse

from app.evidence_store import get_default_evidence_store
from app.operational_gate import operational_control_is_adopted

router = APIRouter(prefix="/evidence", tags=["evidence"])


@router.post("/education/upload")
async def upload_education_evidence(file: UploadFile = File(...)) -> RedirectResponse:
    if not operational_control_is_adopted("education"):
        return RedirectResponse(url="/education", status_code=303)

    try:
        content = await file.read()
        get_default_evidence_store().save(
            "education",
            file.filename or "",
            content,
            file.content_type,
        )
    except ValueError as exc:
        return RedirectResponse(
            url=f"/education?flash={quote(str(exc))}",
            status_code=303,
        )
    return RedirectResponse(
        url=f"/education?flash={quote('証跡ファイルを添付しました。添付だけでは教育工程は完了になりません。')}",
        status_code=303,
    )


@router.get("/education/{evidence_id}")
def download_education_evidence(evidence_id: str) -> FileResponse:
    found = get_default_evidence_store().get("education", evidence_id)
    if found is None:
        raise HTTPException(status_code=404, detail="Not Found")
    item, path = found
    return FileResponse(
        path,
        media_type=item.content_type,
        filename=item.original_name,
    )
