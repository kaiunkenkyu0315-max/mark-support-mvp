"""紙媒体管理デモ画面のFastAPIルーティング。

HTTP処理（リクエスト受付・リダイレクト）のみを担当する。事実データの更新は
app.paper_demo_state に、適合／要対応の判定は app.paper.evaluate_paper_management
に委譲し、ここでは業務判定を行わない。
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse

from app import intake_demo_state, paper_demo_state
from app.paper import evaluate_paper_management
from app.paper_view import render_paper_page

router = APIRouter(prefix="/paper", tags=["paper"])


def _render_current_page() -> str:
    state = paper_demo_state.get_state()
    result = evaluate_paper_management(state.control, state.status)
    control_suggestions = intake_demo_state.get_state().control_suggestions
    return render_paper_page(state, result, control_suggestions)


@router.get("", response_class=HTMLResponse)
def paper_page() -> str:
    return _render_current_page()


@router.post("/actions/confirm-storage-lock")
def confirm_storage_lock() -> RedirectResponse:
    paper_demo_state.confirm_storage_lock()
    return RedirectResponse(url="/paper", status_code=303)


@router.post("/actions/define-take-out-rule")
def define_take_out_rule() -> RedirectResponse:
    paper_demo_state.define_take_out_rule()
    return RedirectResponse(url="/paper", status_code=303)


@router.post("/actions/confirm-disposal")
def confirm_disposal() -> RedirectResponse:
    paper_demo_state.confirm_disposal()
    return RedirectResponse(url="/paper", status_code=303)


@router.post("/actions/approve")
def approve_status() -> RedirectResponse:
    paper_demo_state.approve_status()
    return RedirectResponse(url="/paper", status_code=303)


@router.post("/reset")
def reset() -> RedirectResponse:
    paper_demo_state.reset_state()
    return RedirectResponse(url="/paper", status_code=303)
