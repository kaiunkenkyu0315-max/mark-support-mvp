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


@router.get("", response_class=HTMLResponse)
def paper_page(flash: str | None = None) -> str:
    return _render_current_page(flash)


@router.post("/actions/confirm-storage-lock")
def confirm_storage_lock(
    storage_location: str | None = Form(None),
    locked: str | None = Form(None),
    checked_on: str | None = Form(None),
    checked_by: str | None = Form(None),
    check_method: str | None = Form(None),
    evidence: str | None = Form(None),
) -> RedirectResponse:
    blocked = _blocked_action()
    if blocked:
        return blocked
    paper_demo_state.confirm_storage_lock(
        locked=locked != "no",
        checked_on=checked_on,
        checked_by=checked_by,
        check_method=check_method,
        evidence=evidence,
        storage_location=storage_location,
    )
    return _redirect_with_flash("confirm-storage-lock")


@router.post("/actions/define-take-out-rule")
def define_take_out_rule(
    rule: str | None = Form(None),
    defined_on: str | None = Form(None),
    defined_by: str | None = Form(None),
) -> RedirectResponse:
    blocked = _blocked_action()
    if blocked:
        return blocked
    paper_demo_state.define_take_out_rule(
        rule=rule,
        defined_on=defined_on,
        defined_by=defined_by,
    )
    return _redirect_with_flash("define-take-out-rule")


@router.post("/actions/confirm-disposal")
def confirm_disposal(
    disposal_method: str | None = Form(None),
    confirmed: str | None = Form(None),
    confirmed_on: str | None = Form(None),
    confirmed_by: str | None = Form(None),
    evidence: str | None = Form(None),
) -> RedirectResponse:
    blocked = _blocked_action()
    if blocked:
        return blocked
    paper_demo_state.confirm_disposal(
        confirmed=confirmed != "no",
        confirmed_on=confirmed_on,
        confirmed_by=confirmed_by,
        evidence=evidence,
        disposal_method=disposal_method,
    )
    return _redirect_with_flash("confirm-disposal")


@router.post("/actions/approve")
def approve_status(
    approved_by: str | None = Form(None),
    approved_at: str | None = Form(None),
) -> RedirectResponse:
    blocked = _blocked_action()
    if blocked:
        return blocked
    paper_demo_state.approve_status(
        approved_by=approved_by,
        approved_at=approved_at,
    )
    return _redirect_with_flash("approve")


@router.post("/reset")
def reset() -> RedirectResponse:
    paper_demo_state.reset_state()
    return RedirectResponse(url="/paper", status_code=303)
