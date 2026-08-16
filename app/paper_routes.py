"""紙媒体管理デモ画面のFastAPIルーティング。

HTTP処理（リクエスト受付・リダイレクト）のみを担当する。事実データの更新は
app.paper_demo_state に、適合／要対応の判定は app.paper.evaluate_paper_management
に委譲し、ここでは業務判定を行わない。
"""

from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse, RedirectResponse

from app import intake_demo_state, paper_demo_state
from app.operational_gate import operational_control_is_adopted, render_inactive_operation_page
from app.paper import evaluate_paper_management
from app.paper_view import render_paper_page
from app.paper_workflow_view import enhance_paper_page

router = APIRouter(prefix="/paper", tags=["paper"])

CONTROL_ID = "paper_management"
PAGE_TITLE = "紙媒体管理"

ACTION_MESSAGES: dict[str, str] = {
    "confirm-storage-lock": "保管・施錠確認記録を登録しました。",
    "define-take-out-rule": "持出しルールを登録しました。",
    "confirm-disposal": "廃棄確認記録を登録しました。",
    "approve": "承認記録を登録しました。",
}


def _render_current_page(flash: str | None = None) -> str:
    if not operational_control_is_adopted(CONTROL_ID):
        return render_inactive_operation_page(title=PAGE_TITLE, control_id=CONTROL_ID)

    state = paper_demo_state.get_state()
    result = evaluate_paper_management(state.control, state.status)
    control_suggestions = intake_demo_state.get_state().control_suggestions
    html = render_paper_page(state, result, control_suggestions, flash=flash)
    return enhance_paper_page(html, state, result)


def _redirect_with_flash(action_key: str) -> RedirectResponse:
    state = paper_demo_state.get_state()
    result = evaluate_paper_management(state.control, state.status)
    message = ACTION_MESSAGES[action_key]
    if not result.issues:
        message = f"{message}対応が必要な項目はすべて解消されました。"
    return RedirectResponse(url=f"/paper?flash={quote(message)}", status_code=303)


def _blocked_action() -> RedirectResponse | None:
    if operational_control_is_adopted(CONTROL_ID):
        return None
    return RedirectResponse(url="/paper", status_code=303)


@app_placeholder
