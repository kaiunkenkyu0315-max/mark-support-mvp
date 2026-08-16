"""教育管理デモ画面のFastAPIルーティング。

HTTP処理（リクエスト受付・リダイレクト）のみを担当する。
事実データの更新は app.demo_state に、適合／要対応の判定は
app.education.evaluate_training に委譲し、ここでは業務判定を行わない。
"""

from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse

from app import demo_state, intake_demo_state
from app.education import evaluate_training
from app.education_view import render_education_page

router = APIRouter(prefix="/education", tags=["education"])

# 各操作（不足解消）後に表示する、利用者向けの短いフィードバックメッセージ。
ACTION_MESSAGES: dict[str, str] = {
    "complete-trainings": "受講状況を更新しました。",
    "register-comprehension": "理解度確認結果を登録しました。",
    "register-material-evidence": "教材記録を登録しました。",
    "approve": "承認しました。",
}


def _render_current_page(flash: str | None = None) -> str:
    state = demo_state.get_state()
    result = evaluate_training(state.employees, state.control, state.plan, state.records)
    control_suggestions = intake_demo_state.get_state().control_suggestions
    return render_education_page(state, result, control_suggestions, flash=flash)


def _redirect_with_flash(action_key: str) -> RedirectResponse:
    state = demo_state.get_state()
    result = evaluate_training(state.employees, state.control, state.plan, state.records)
    message = ACTION_MESSAGES[action_key]
    if not result.issues:
        message = f"{message}対応が必要な項目はすべて解消されました。"
    return RedirectResponse(url=f"/education?flash={quote(message)}", status_code=303)


@router.get("", response_class=HTMLResponse)
def education_page(flash: str | None = None) -> str:
    return _render_current_page(flash)


@router.post("/actions/complete-trainings")
def complete_trainings() -> RedirectResponse:
    demo_state.complete_all_trainings()
    return _redirect_with_flash("complete-trainings")


@router.post("/actions/register-comprehension")
def register_comprehension() -> RedirectResponse:
    demo_state.register_missing_comprehension()
    return _redirect_with_flash("register-comprehension")


@router.post("/actions/register-material-evidence")
def register_material_evidence() -> RedirectResponse:
    demo_state.register_material_evidence()
    return _redirect_with_flash("register-material-evidence")


@router.post("/actions/approve")
def approve() -> RedirectResponse:
    demo_state.approve_plan()
    return _redirect_with_flash("approve")


@router.post("/reset")
def reset() -> RedirectResponse:
    demo_state.reset_state()
    return RedirectResponse(url="/education", status_code=303)
