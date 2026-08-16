"""intakeフロー（会社・PMS基本情報〜業務ヒアリング〜個人情報確認〜リスク〜管理策）のFastAPIルーティング。

HTTP処理（リクエスト受付・リダイレクト）のみを担当する。
会社・PMS基本情報は app.company_profile、事実・候補データの更新は app.intake_demo_state、
候補生成・再計算ロジックは app.intake / app.risk に委譲する。
"""

from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app import company_profile, intake_demo_state
from app.intake_schemas import QuestionnaireAnswers
from app.intake_step2_batch_view import render_setup_page_with_batch_step2

router = APIRouter(prefix="/setup", tags=["setup"])


def _parse_tristate_bool(value: object) -> bool | None:
    """台帳フォームのtri-state radio（yes/no/unknown）をbool | Noneへ変換する。"""

    if value == "yes":
        return True
    if value == "no":
        return False
    return None


def _render_current_page() -> str:
    state = intake_demo_state.get_state()
    return render_setup_page_with_batch_step2(state)


@router.get("", response_class=HTMLResponse)
def setup_page() -> str:
    return _render_current_page()


@router.post("/company")
def submit_company_profile(
    name: str = Form(...),
    employee_count: int = Form(...),
    fiscal_year: int = Form(...),
    name_kana: str = Form(""),
    corporate_number: str = Form(""),
    registered_address: str = Form(""),
    representative_title: str = Form(""),
    representative_name: str = Form(""),
    privacy_manager_name: str = Form(""),
    privacy_manager_department_role: str = Form(""),
    audit_manager_name: str = Form(""),
    audit_manager_department_role: str = Form(""),
    application_contact_name: str = Form(""),
    application_contact_department_role: str = Form(""),
    application_contact_email: str = Form(""),
) -> RedirectResponse:
    """STEP0の会社・PMS基本情報を共通データとして保存し、業務情報へ進む。"""

    company_profile.update_profile(
        name=name,
        employee_count=employee_count,
        fiscal_year=fiscal_year,
        name_kana=name_kana,
        corporate_number=corporate_number,
        registered_address=registered_address,
        representative_title=representative_title,
        representative_name=representative_name,
        privacy_manager_name=privacy_manager_name,
        privacy_manager_department_role=privacy_manager_department_role,
        audit_manager_name=audit_manager_name,
        audit_manager_department_role=audit_manager_department_role,
        application_contact_name=application_contact_name,
        application_contact_department_role=application_contact_department_role,
        application_contact_email=application_contact_email,
    )
    return RedirectResponse(url="/setup#step1", status_code=303)


@router.post("/answers")
async def submit_answers(request: Request) -> RedirectResponse:
    form = await request.form()
    profile = company_profile.get_state()

    values = {field: form.get(field) == "yes" for field, _ in intake_demo_state.QUESTIONS}
    if profile.configured:
        # 従業者数はSTEP0を正本とし、STEP1では同じ事実を再入力させない。
        values["has_employees"] = profile.employee_count > 0

    answers = QuestionnaireAnswers(**values)
    intake_demo_state.submit_answers(answers)
    return RedirectResponse(url="/setup#step2", status_code=303)


@router.post("/candidates/decide")
async def decide_candidates(request: Request) -> RedirectResponse:
    """STEP2の個人情報候補をまとめて保存し、次のSTEPへ進む。"""

    form = await request.form()
    decisions: dict[int, bool] = {}
    for candidate in intake_demo_state.get_state().candidates:
        value = form.get(f"candidate_{candidate.id}")
        if value == "yes":
            decisions[candidate.id] = True
        elif value == "no":
            decisions[candidate.id] = False
    intake_demo_state.decide_candidates(decisions)
    return RedirectResponse(url="/setup#step3", status_code=303)


@router.post("/candidates/{candidate_id}/confirm")
def confirm_candidate(candidate_id: int) -> RedirectResponse:
    """既存互換用。通常UIでは一括回答を使用する。"""

    intake_demo_state.confirm_candidate(candidate_id)
    return RedirectResponse(url="/setup#step2", status_code=303)


@router.post("/candidates/{candidate_id}/exclude")
def exclude_candidate(candidate_id: int) -> RedirectResponse:
    """既存互換用。通常UIでは一括回答を使用する。"""

    intake_demo_state.exclude_candidate(candidate_id)
    return RedirectResponse(url="/setup#step2", status_code=303)


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
    return RedirectResponse(url="/setup#step3", status_code=303)


@router.post("/risks/{risk_candidate_id}/confirm")
def confirm_risk(risk_candidate_id: int) -> RedirectResponse:
    intake_demo_state.confirm_risk(risk_candidate_id)
    return RedirectResponse(url="/setup#step4", status_code=303)


@router.post("/risks/{risk_candidate_id}/exclude")
def exclude_risk(risk_candidate_id: int) -> RedirectResponse:
    intake_demo_state.exclude_risk(risk_candidate_id)
    return RedirectResponse(url="/setup#step4", status_code=303)


@router.post("/risks/{risk_candidate_id}/evaluate")
def update_risk_evaluation(
    risk_candidate_id: int, impact: int = Form(...), likelihood: int = Form(...)
) -> RedirectResponse:
    intake_demo_state.update_risk_evaluation(risk_candidate_id, impact, likelihood)
    return RedirectResponse(url="/setup#step4", status_code=303)


@router.post("/controls/{control_id}/adopt")
def adopt_control(control_id: str) -> RedirectResponse:
    intake_demo_state.adopt_control(control_id)
    return RedirectResponse(url="/setup#step5", status_code=303)


@router.post("/controls/{control_id}/not-applicable")
def mark_control_not_applicable(control_id: str, reason: str = Form(...)) -> RedirectResponse:
    reason = reason.strip()
    if reason:
        intake_demo_state.mark_control_not_applicable(control_id, reason)
    return RedirectResponse(url="/setup#step5", status_code=303)


@router.post("/reset")
def reset() -> RedirectResponse:
    company_profile.reset_state()
    intake_demo_state.reset_state()
    return RedirectResponse(url="/setup", status_code=303)
