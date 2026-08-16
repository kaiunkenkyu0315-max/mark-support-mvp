"""MVP開発中だけ使う検証用ルート。"""

from fastapi import APIRouter
from fastapi.responses import RedirectResponse

from app.dev_preset import load_operational_review_preset

router = APIRouter(prefix="/dev", tags=["development"])


@router.post("/preset/operations")
def load_operations_preset() -> RedirectResponse:
    load_operational_review_preset()
    return RedirectResponse(url="/", status_code=303)
