"""教育管理デモ画面のFastAPIルーティング。

HTTP処理（リクエスト受付・リダイレクト）のみを担当する。
事実データの更新は app.demo_state に、適合／要対応の判定は
app.education.evaluate_training に委譲し、ここでは業務判定を行わない。
"""

from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse, RedirectResponse

from app import demo_state, intake_demo_state
from app.education import evaluate_training
from app.education_record_view import enhance_education_page
from app.education_view import render_education_page
from app.operational_gate import operational_control_is_adopted, render_inactive_operation_page
from app.schemas import ComprehensionResult

router = APIRouter(prefix="/education", tags=["education"])

CONTROL_ID = "education"
PAGE_TITLE = "教育管理"

# 各操作後に表示する、利用者向けの短いフィードバックメッセージ。
ACTION_MESSAGES: dict[str, str] = {
    "complete-trainings": "受講記録を登録しました。",
    "register-comprehension": "理解度確認記録を登録しました。",
    "register-material-evidence": "教育実施・教材記録を登録しました。",
    "approve": "承認記録を登録しました。",
}


def _render_current_page(flash: str | None = None) -> str:
    if not operational_control_is_adopted(CONTROL_ID):
        return render_inactive_operation_page(title=PAGE_TITLE, control_id=CONTROL_ID)

    state = demo_state.get_state()
    result = evaluate_training(state.employees, state.control, state.plan, state.records)
    control_suggestions = intake_demo_state.get_state().control_suggestions
    html = render_education_page(state, result, control_suggestions, flash=flash)
    return enhance_education_page(html, state, result)


def _redirect_with_flash(action_key: str) -> RedirectResponse:
    state = demo_state.get_state()
    result = evaluate_training(state.employees, state.control, state.plan, state.records)
    message = ACTION_MESSAGES[action_key]
    if not result.issues:
        message = f"{message}対応が必要な項目はすべて解消されました。"
    return RedirectResponse(url=f"/education?flash={quote(message)}", status_code=303)


def _blocked_action() -> RedirectResponse | None:
    if operational_control_is_adopted(CONTROL_ID):
        return None
    return RedirectResponse(url="/education", status_code=303)


@router.get("", response_class=HTMLResponse)
def education_page(flash: str | None = None) -> str:
    return _render_current_page(flash)


@router.post("/actions/complete-trainings")
def complete_trainings(completed_on: str = Form("")) -> RedirectResponse:
    blocked = _blocked_action()
    if blocked:
        return blocked
    demo_state.complete_all_trainings(completed_on=completed_on)
    return _redirect_with_flash("complete-trainings")


@router.post("/actions/register-comprehension")
def register_comprehension(
    comprehension_method: str = Form(""),
    result: str = Form("passed"),
) -> RedirectResponse:
    blocked = _blocked_action()
    if blocked:
        return blocked
    comprehension_result = (
        ComprehensionResult.FAILED if result == "failed" else ComprehensionResult.PASSED
    )
    demo_state.register_missing_comprehension(
        comprehension_result,
        method=comprehension_method,
    )
    return _redirect_with_flash("register-comprehension")


@router.post("/actions/register-material-evidence")
def register_material_evidence(
    execution_date: str = Form(""),
    delivery_method: str = Form(""),
    material_name: str = Form(""),
    instructor_name: str = Form(""),
) -> RedirectResponse:
    blocked = _blocked_action()
    if blocked:
        return blocked

    # 旧テスト・既存デモ操作から空POSTされた場合だけ、従来互換の既定記録を使用する。
    if not any((execution_date, delivery_method, material_name, instructor_name)):
        demo_state.register_material_evidence()
    else:
        demo_state.register_training_execution(
            execution_date=execution_date,
            delivery_method=delivery_method,
            material_name=material_name,
            instructor_name=instructor_name,
        )
    return _redirect_with_flash("register-material-evidence")


@router.post("/actions/approve")
def approve(
    approved_by: str = Form(""),
    approved_at: str = Form(""),
) -> RedirectResponse:
    blocked = _blocked_action()
    if blocked:
        return blocked
    demo_state.approve_plan(approved_by=approved_by, approved_at=approved_at)
    return _redirect_with_flash("approve")


@router.post("/reset")
def reset() -> RedirectResponse:
    demo_state.reset_state()
    return RedirectResponse(url="/education", status_code=303)
