"""アクセス権限管理デモ画面のFastAPIルーティング。

HTTP処理（リクエスト受付・リダイレクト）のみを担当する。事実データの更新は
app.access_control_demo_state に、適合／要対応の判定は
app.access_control.evaluate_access_control に委譲し、ここでは業務判定を行わない。
"""

from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse

from app import access_control_demo_state, intake_demo_state
from app.access_control import evaluate_access_control
from app.access_control_view import render_access_control_page

router = APIRouter(prefix="/access-control", tags=["access-control"])

# 各操作（不足解消）後に表示する、利用者向けの短いフィードバックメッセージ。
ACTION_MESSAGES: dict[str, str] = {
    "complete-account-reviews": "アカウント確認を更新しました。",
    "remove-unnecessary-accounts": "不要アカウントを削除しました。",
    "complete-review-cycle": "権限レビューを実施しました。",
    "approve-review-cycle": "承認しました。",
}


def _render_current_page(flash: str | None = None) -> str:
    state = access_control_demo_state.get_state()
    result = evaluate_access_control(state.accounts, state.control, state.cycle)
    control_suggestions = intake_demo_state.get_state().control_suggestions
    return render_access_control_page(state, result, control_suggestions, flash=flash)


def _redirect_with_flash(action_key: str) -> RedirectResponse:
    state = access_control_demo_state.get_state()
    result = evaluate_access_control(state.accounts, state.control, state.cycle)
    message = ACTION_MESSAGES[action_key]
    if not result.issues:
        message = f"{message}対応が必要な項目はすべて解消されました。"
    return RedirectResponse(url=f"/access-control?flash={quote(message)}", status_code=303)


@router.get("", response_class=HTMLResponse)
def access_control_page(flash: str | None = None) -> str:
    return _render_current_page(flash)


@router.post("/actions/complete-account-reviews")
def complete_account_reviews() -> RedirectResponse:
    access_control_demo_state.complete_missing_account_reviews()
    return _redirect_with_flash("complete-account-reviews")


@router.post("/actions/remove-unnecessary-accounts")
def remove_unnecessary_accounts() -> RedirectResponse:
    access_control_demo_state.remove_unnecessary_accounts()
    return _redirect_with_flash("remove-unnecessary-accounts")


@router.post("/actions/complete-review-cycle")
def complete_review_cycle() -> RedirectResponse:
    access_control_demo_state.complete_review_cycle()
    return _redirect_with_flash("complete-review-cycle")


@router.post("/actions/approve-review-cycle")
def approve_review_cycle() -> RedirectResponse:
    access_control_demo_state.approve_review_cycle()
    return _redirect_with_flash("approve-review-cycle")


@router.post("/reset")
def reset() -> RedirectResponse:
    access_control_demo_state.reset_state()
    return RedirectResponse(url="/access-control", status_code=303)
