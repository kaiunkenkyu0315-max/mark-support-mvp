"""MVP開発中だけ使う検証用ルート。"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse

from app.dev_preset import (
    load_annual_pms_preset,
    load_application_goal_preset,
    load_application_prep_preset,
    load_operational_review_preset,
    load_pms_review_preset,
)
from app.prototype_settings import dev_tools_enabled


def require_dev_tools() -> None:
    """通常利用時は開発用URL自体を公開しない。"""

    if not dev_tools_enabled():
        raise HTTPException(status_code=404, detail="Not Found")


router = APIRouter(
    prefix="/dev",
    tags=["development"],
    dependencies=[Depends(require_dev_tools)],
)


@router.post("/preset/operations")
def load_operations_preset() -> RedirectResponse:
    load_operational_review_preset()
    return RedirectResponse(url="/", status_code=303)


@router.post("/preset/annual-pms")
def load_annual_preset() -> RedirectResponse:
    load_annual_pms_preset()
    return RedirectResponse(url="/annual-pms", status_code=303)


@router.post("/preset/pms-review")
def load_review_preset() -> RedirectResponse:
    load_pms_review_preset()
    return RedirectResponse(url="/pms-review", status_code=303)


@router.post("/preset/application-prep")
def load_application_preset() -> RedirectResponse:
    load_application_prep_preset()
    return RedirectResponse(url="/application-prep", status_code=303)


@router.post("/preset/application-goal")
def load_application_goal() -> RedirectResponse:
    load_application_goal_preset()
    return RedirectResponse(url="/application-prep", status_code=303)
