"""アクセス権限管理デモ画面のFastAPIルーティング。

HTTP処理（リクエスト受付・リダイレクト）のみを担当する。事実データの更新は
app.access_control_demo_state に、適合／要対応の判定は
app.access_control.evaluate_access_control に委譲し、ここでは業務判定を行わない。
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse

from app import access_control_demo_state, intake_demo_state
from app.access_control import evaluate_access_control
from app.access_control_view import render_access_control_page

router = APIRouter(prefix="/access-control", tags=["access-control"])


def _render_current_page() -> str:
    state = access_control_demo_state.get_state()
    result = evaluate_access_control(state.accounts, state.control, state.cycle)
    control_suggestions = intake_demo_state.get_state().control_suggestions
    return render_access_control_page(state, result, control_suggestions)


@router.get("", response_class=HTMLResponse)
def access_control_page() -> str:
    return _render_current_page()


@router.post("/actions/complete-account-reviews")
def complete_account_reviews() -> RedirectResponse:
    access_control_demo_state.complete_missing_account_reviews()
    return RedirectResponse(url="/access-control", status_code=303)


@router.post("/actions/remove-unnecessary-accounts")
def remove_unnecessary_accounts() -> RedirectResponse:
    access_control_demo_state.remove_unnecessary_accounts()
    return RedirectResponse(url="/access-control", status_code=303)


@router.post("/actions/complete-review-cycle")
def complete_review_cycle() -> RedirectResponse:
    access_control_demo_state.complete_review_cycle()
    return RedirectResponse(url="/access-control", status_code=303)


@router.post("/actions/approve-review-cycle")
def approve_review_cycle() -> RedirectResponse:
    access_control_demo_state.approve_review_cycle()
    return RedirectResponse(url="/access-control", status_code=303)


@router.post("/reset")
def reset() -> RedirectResponse:
    access_control_demo_state.reset_state()
    return RedirectResponse(url="/access-control", status_code=303)
