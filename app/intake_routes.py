"""intakeフロー（業務ヒアリング〜個人情報確認〜リスクアセスメント〜管理策候補提示）
のFastAPIルーティング。

HTTP処理（リクエスト受付・リダイレクト）のみを担当する。
事実・候補データの更新は app.intake_demo_state に、候補生成・再計算ロジックは
app.intake / app.risk に委譲し、ここでは業務判定を行わない。
"""

from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app import intake_demo_state
from app.intake_schemas import QuestionnaireAnswers
from app.intake_view import render_setup_page

router = APIRouter(prefix="/setup", tags=["setup"])


def _parse_tristate_bool(value: object) -> bool | None:
    """台帳フォームのtri-state radio（yes/no/unknown）をbool | Noneへ変換する。

    "yes"/"no"以外（未送信・"unknown"等）はすべてNone（未回答）として扱う。
    """

    if value == "yes":
        return True
    if value == "no":
        return False
    return None


def _render_current_page() -> str:
    state = intake_demo_state.get_state()
    return render_setup_page(state)


@router.get("", response_class=HTMLResponse)
def setup_page() -> str:
    return _render_current_page()


@router.post("/answers")
async def submit_answers(request: Request) -> RedirectResponse:
    form = await request.form()
    values = {field: form.get(field) == "yes" for field, _ in intake_demo_state.QUESTIONS}
    answers = QuestionnaireAnswers(**values)
    intake_demo_state.submit_answers(answers)
    return RedirectResponse(url="/setup", status_code=303)


@router.post("/candidates/{candidate_id}/confirm")
def confirm_candidate(candidate_id: int) -> RedirectResponse:
    intake_demo_state.confirm_candidate(candidate_id)
    return RedirectResponse(url="/setup", status_code=303)


@router.post("/candidates/{candidate_id}/exclude")
def exclude_candidate(candidate_id: int) -> RedirectResponse:
    intake_demo_state.exclude_candidate(candidate_id)
    return RedirectResponse(url="/setup", status_code=303)


@router.post("/candidates/{candidate_id}/ledger")
async def update_ledger_entry(candidate_id: int, request: Request) -> RedirectResponse:
    form = await request.form()
    intake_demo_state.update_ledger_entry(
        candidate_id,
        acquisition_method=str(form.get("acquisition_method") or ""),
        storage_method=str(form.get("storage_method") or ""),
        storage_location=str(form.get("storage_location") or ""),
        outsourced=_parse_tristate_bool(form.get("outsourced")),
        third_party_provided=_parse_tristate_bool(form.get("third_party_provided")),
        retention_period=str(form.get("retention_period") or ""),
        disposal_method=str(form.get("disposal_method") or ""),
        responsible_role=str(form.get("responsible_role") or ""),
    )
    return RedirectResponse(url="/setup", status_code=303)


@router.post("/risks/{risk_candidate_id}/confirm")
def confirm_risk(risk_candidate_id: int) -> RedirectResponse:
    intake_demo_state.confirm_risk(risk_candidate_id)
    return RedirectResponse(url="/setup", status_code=303)


@router.post("/risks/{risk_candidate_id}/exclude")
def exclude_risk(risk_candidate_id: int) -> RedirectResponse:
    intake_demo_state.exclude_risk(risk_candidate_id)
    return RedirectResponse(url="/setup", status_code=303)


@router.post("/risks/{risk_candidate_id}/evaluate")
def update_risk_evaluation(
    risk_candidate_id: int, impact: int = Form(...), likelihood: int = Form(...)
) -> RedirectResponse:
    intake_demo_state.update_risk_evaluation(risk_candidate_id, impact, likelihood)
    return RedirectResponse(url="/setup", status_code=303)


@router.post("/controls/{control_id}/adopt")
def adopt_control(control_id: str) -> RedirectResponse:
    intake_demo_state.adopt_control(control_id)
    return RedirectResponse(url="/setup", status_code=303)


@router.post("/controls/{control_id}/not-applicable")
def mark_control_not_applicable(control_id: str, reason: str = Form(...)) -> RedirectResponse:
    reason = reason.strip()
    if reason:
        # 非適用の理由は必須とする。空欄の場合は状態を変更せず、そのまま画面に戻す。
        intake_demo_state.mark_control_not_applicable(control_id, reason)
    return RedirectResponse(url="/setup", status_code=303)


@router.post("/reset")
def reset() -> RedirectResponse:
    intake_demo_state.reset_state()
    return RedirectResponse(url="/setup", status_code=303)
