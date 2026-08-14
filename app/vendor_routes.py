"""委託先管理デモ画面のFastAPIルーティング。

HTTP処理（リクエスト受付・リダイレクト）のみを担当する。
事実データの更新は app.vendor_demo_state に、適合／要対応の判定は
app.vendors.evaluate_vendors に委譲し、ここでは業務判定を行わない。
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse

from app import vendor_demo_state
from app.vendor_view import render_vendor_page
from app.vendors import evaluate_vendors

router = APIRouter(prefix="/vendors", tags=["vendors"])


def _render_current_page() -> str:
    state = vendor_demo_state.get_state()
    result = evaluate_vendors(state.vendors, state.control, state.assessments, state.contracts)
    return render_vendor_page(state, result)


@router.get("", response_class=HTMLResponse)
def vendors_page() -> str:
    return _render_current_page()


@router.post("/actions/complete-initial-assessments")
def complete_initial_assessments() -> RedirectResponse:
    vendor_demo_state.complete_missing_initial_assessments()
    return RedirectResponse(url="/vendors", status_code=303)


@router.post("/actions/confirm-contracts")
def confirm_contracts() -> RedirectResponse:
    vendor_demo_state.confirm_missing_contracts()
    return RedirectResponse(url="/vendors", status_code=303)


@router.post("/actions/complete-periodic-assessments")
def complete_periodic_assessments() -> RedirectResponse:
    vendor_demo_state.complete_missing_periodic_assessments()
    return RedirectResponse(url="/vendors", status_code=303)


@router.post("/reset")
def reset() -> RedirectResponse:
    vendor_demo_state.reset_state()
    return RedirectResponse(url="/vendors", status_code=303)
