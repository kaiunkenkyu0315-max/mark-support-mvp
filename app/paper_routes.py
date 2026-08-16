"""紙媒体管理デモ画面のFastAPIルーティング。

HTTP処理（リクエスト受付・リダイレクト）のみを担当する。事実データの更新は
app.paper_demo_state に、適合／要対応の判定は app.paper.evaluate_paper_management
に委譲し、ここでは業務判定を行わない。
"""

from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse

from app import intake_demo_state, paper_demo_state
from app.paper import evaluate_paper_management
from app.paper_view import render_paper_page

router = APIRouter(prefix="/paper", tags=["paper"])

# 各操作（不足解消）後に表示する、利用者向けの短いフィードバックメッセージ。
ACTION_MESSAGES: dict[str, str] = {
    "confirm-storage-lock": "施錠管理を確認しました。",
    "define-take-out-rule": "持出しルールを登録しました。",
    "confirm-disposal": "廃棄確認を実施しました。",
    "approve": "承認しました。",
}


def _render_current_page(flash: str | None = None) -> str:
    state = paper_demo_state.get_state()
    result = evaluate_paper_management(state.control, state.status)
    control_suggestions = intake_demo_state.get_state().control_suggestions
    return render_paper_page(state, result, control_suggestions, flash=flash)


def _redirect_with_flash(action_key: str) -> RedirectResponse:
    state = paper_demo_state.get_state()
    result = evaluate_paper_management(state.control, state.status)
    message = ACTION_MESSAGES[action_key]
    if not result.issues:
        message = f"{message}対応が必要な項目はすべて解消されました。"
    return RedirectResponse(url=f"/paper?flash={quote(message)}", status_code=303)


@router.get("", response_class=HTMLResponse)
def paper_page(flash: str | None = None) -> str:
    return _render_current_page(flash)


@router.post("/actions/confirm-storage-lock")
def confirm_storage_lock() -> RedirectResponse:
    paper_demo_state.confirm_storage_lock()
    return _redirect_with_flash("confirm-storage-lock")


@router.post("/actions/define-take-out-rule")
def define_take_out_rule() -> RedirectResponse:
    paper_demo_state.define_take_out_rule()
    return _redirect_with_flash("define-take-out-rule")


@router.post("/actions/confirm-disposal")
def confirm_disposal() -> RedirectResponse:
    paper_demo_state.confirm_disposal()
    return _redirect_with_flash("confirm-disposal")


@router.post("/actions/approve")
def approve_status() -> RedirectResponse:
    paper_demo_state.approve_status()
    return _redirect_with_flash("approve")


@router.post("/reset")
def reset() -> RedirectResponse:
    paper_demo_state.reset_state()
    return RedirectResponse(url="/paper", status_code=303)
