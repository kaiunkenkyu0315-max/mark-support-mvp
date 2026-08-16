"""委託先管理デモ画面のFastAPIルーティング。

HTTP処理（リクエスト受付・リダイレクト）のみを担当する。
事実データの更新は app.vendor_demo_state に、適合／要対応の判定は
app.vendors.evaluate_vendors に委譲し、ここでは業務判定を行わない。
"""

from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse

from app import intake_demo_state, vendor_demo_state
from app.operational_gate import operational_control_is_adopted, render_inactive_operation_page
from app.vendor_view import render_vendor_page
from app.vendors import evaluate_vendors

router = APIRouter(prefix="/vendors", tags=["vendors"])

CONTROL_ID = "vendor_management"
PAGE_TITLE = "委託先管理"

# 各操作（不足解消）後に表示する、利用者向けの短いフィードバックメッセージ。
ACTION_MESSAGES: dict[str, str] = {
    "complete-initial-assessments": "初回評価を登録しました。",
    "confirm-contracts": "契約確認を更新しました。",
    "complete-periodic-assessments": "定期評価を登録しました。",
}


def _render_current_page(flash: str | None = None) -> str:
    if not operational_control_is_adopted(CONTROL_ID):
        return render_inactive_operation_page(title=PAGE_TITLE, control_id=CONTROL_ID)

    state = vendor_demo_state.get_state()
    result = evaluate_vendors(state.vendors, state.control, state.assessments, state.contracts)
    control_suggestions = intake_demo_state.get_state().control_suggestions
    return render_vendor_page(state, result, control_suggestions, flash=flash)


def _redirect_with_flash(action_key: str) -> RedirectResponse:
    state = vendor_demo_state.get_state()
    result = evaluate_vendors(state.vendors, state.control, state.assessments, state.contracts)
    message = ACTION_MESSAGES[action_key]
    if not result.issues:
        message = f"{message}対応が必要な項目はすべて解消されました。"
    return RedirectResponse(url=f"/vendors?flash={quote(message)}", status_code=303)


def _blocked_action() -> RedirectResponse | None:
    if operational_control_is_adopted(CONTROL_ID):
        return None
    return RedirectResponse(url="/vendors", status_code=303)


@router.get("", response_class=HTMLResponse)
def vendors_page(flash: str | None = None) -> str:
    return _render_current_page(flash)


@router.post("/actions/complete-initial-assessments")
def complete_initial_assessments() -> RedirectResponse:
    blocked = _blocked_action()
    if blocked:
        return blocked
    vendor_demo_state.complete_missing_initial_assessments()
    return _redirect_with_flash("complete-initial-assessments")


@router.post("/actions/confirm-contracts")
def confirm_contracts() -> RedirectResponse:
    blocked = _blocked_action()
    if blocked:
        return blocked
    vendor_demo_state.confirm_missing_contracts()
    return _redirect_with_flash("confirm-contracts")


@router.post("/actions/complete-periodic-assessments")
def complete_periodic_assessments() -> RedirectResponse:
    blocked = _blocked_action()
    if blocked:
        return blocked
    vendor_demo_state.complete_missing_periodic_assessments()
    return _redirect_with_flash("complete-periodic-assessments")


@router.post("/reset")
def reset() -> RedirectResponse:
    vendor_demo_state.reset_state()
    return RedirectResponse(url="/vendors", status_code=303)
