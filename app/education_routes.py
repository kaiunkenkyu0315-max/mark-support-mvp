"""教育管理デモ画面のFastAPIルーティング。

HTTP処理（リクエスト受付・リダイレクト）のみを担当する。
事実データの更新は app.demo_state に、適合／要対応の判定は
app.education.evaluate_training に委譲し、ここでは業務判定を行わない。
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse

from app import demo_state, intake_demo_state
from app.education import evaluate_training
from app.education_view import render_education_page

router = APIRouter(prefix="/education", tags=["education"])


def _render_current_page() -> str:
    state = demo_state.get_state()
    result = evaluate_training(state.employees, state.control, state.plan, state.records)
    control_suggestions = intake_demo_state.get_state().control_suggestions
    return render_education_page(state, result, control_suggestions)


@router.get("", response_class=HTMLResponse)
def education_page() -> str:
    return _render_current_page()


@router.post("/actions/complete-trainings")
def complete_trainings() -> RedirectResponse:
    demo_state.complete_all_trainings()
    return RedirectResponse(url="/education", status_code=303)


@router.post("/actions/register-comprehension")
def register_comprehension() -> RedirectResponse:
    demo_state.register_missing_comprehension()
    return RedirectResponse(url="/education", status_code=303)


@router.post("/actions/register-material-evidence")
def register_material_evidence() -> RedirectResponse:
    demo_state.register_material_evidence()
    return RedirectResponse(url="/education", status_code=303)


@router.post("/actions/approve")
def approve() -> RedirectResponse:
    demo_state.approve_plan()
    return RedirectResponse(url="/education", status_code=303)


@router.post("/reset")
def reset() -> RedirectResponse:
    demo_state.reset_state()
    return RedirectResponse(url="/education", status_code=303)
