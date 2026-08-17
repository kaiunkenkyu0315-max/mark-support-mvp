"""MVP開発中だけ使う検証用ルート。"""

from fastapi import APIRouter
from fastapi.responses import RedirectResponse

from app.dev_preset import (
    load_application_prep_preset,
    load_operational_review_preset,
    load_pms_review_preset,
)

router = APIRouter(prefix="/dev", tags=["development"])


@router.post("/preset/operations")
def load_operations_preset() -> RedirectResponse:
    load_operational_review_preset()
    return RedirectResponse(url="/", status_code=303)


@router.post("/preset/pms-review")
def load_review_preset() -> RedirectResponse:
    load_pms_review_preset()
    return RedirectResponse(url="/pms-review", status_code=303)


@router.post("/preset/application-prep")
def load_application_preset() -> RedirectResponse:
    load_application_prep_preset()
    return RedirectResponse(url="/application-prep", status_code=303)
