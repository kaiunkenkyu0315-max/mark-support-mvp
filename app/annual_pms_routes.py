"""年間PMS運用の年度計画・年次見直しルート。"""

from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse, RedirectResponse

from app import annual_cycle_demo_state, company_profile
from app.annual_cycle import evaluate_annual_cycle
from app.annual_pms_context import build_annual_pms_context
from app.annual_pms_view import render_annual_pms_page
from app.intake_schemas import SetupStatus

router = APIRouter(prefix="/annual-pms", tags=["annual-pms"])


def _redirect(message: str) -> RedirectResponse:
    return RedirectResponse(url=f"/annual-pms?flash={quote(message)}", status_code=303)


@router.get("", response_class=HTMLResponse)
def annual_pms_page(flash: str | None = None) -> str:
    return render_annual_pms_page(build_annual_pms_context(), flash=flash)


@router.post("/annual-plan")
def save_annual_plan(
    fiscal_year: int = Form(...),
    planned_on: str = Form(...),
    coordinator_name: str = Form(...),
    privacy_manager_name: str = Form(...),
    audit_manager_name: str = Form(...),
    top_management_name: str = Form(...),
    objectives: str = Form(...),
    schedule_summary: str = Form(...),
    approved_by: str = Form(...),
    approved_at: str = Form(...),
    evidence_name: str = Form(...),
) -> RedirectResponse:
    profile = company_profile.get_state()
    if fiscal_year != profile.fiscal_year:
        return _redirect(
            f"対象年度は会社・PMS基本情報の{profile.fiscal_year}年度と一致させてください。"
        )

    required = (
        planned_on,
        coordinator_name,
        privacy_manager_name,
        audit_manager_name,
        top_management_name,
        objectives,
        schedule_summary,
        approved_by,
        approved_at,
        evidence_name,
    )
    if not all(value.strip() for value in required):
        return _redirect("年度運用計画の必須項目をすべて入力してください。")

    annual_cycle_demo_state.record_annual_plan(
        fiscal_year=fiscal_year,
        planned_on=planned_on,
        coordinator_name=coordinator_name,
        privacy_manager_name=privacy_manager_name,
        audit_manager_name=audit_manager_name,
        top_management_name=top_management_name,
        objectives=objectives,
        schedule_summary=schedule_summary,
        approved_by=approved_by,
        approved_at=approved_at,
        evidence_name=evidence_name,
    )
    return _redirect("年度運用計画を保存しました。次に個人情報台帳・リスクの年次見直しを記録してください。")


@router.post("/inventory-risk-review")
def save_inventory_risk_review(
    reviewed_on: str = Form(...),
    reviewed_by: str = Form(...),
    review_basis: str = Form(...),
    business_change_result: str = Form(...),
    personal_information_result: str = Form(...),
    risk_result: str = Form(...),
    control_result: str = Form(...),
    change_action_summary: str = Form(""),
    change_action_completed_on: str = Form(""),
    approved_by: str = Form(...),
    approved_at: str = Form(...),
    evidence_name: str = Form(...),
) -> RedirectResponse:
    profile = company_profile.get_state()
    before = evaluate_annual_cycle(
        annual_cycle_demo_state.get_state(),
        expected_fiscal_year=profile.fiscal_year,
    )
    if not before.plan_complete:
        return _redirect("先に対象年度のPMS運用計画を完成させてください。")

    context = build_annual_pms_context()
    if context.dashboard_data.setup_status != SetupStatus.COMPLETE:
        return _redirect("個人情報・リスク・管理策の正本に未確認項目があります。先に初期設定側を更新・確認してください。")

    decisions = (
        business_change_result,
        personal_information_result,
        risk_result,
        control_result,
    )
    if any(value not in {"changed", "no_change"} for value in decisions):
        return _redirect("4つの見直し項目について、変更あり・変更なしを明示してください。")

    change_detected = any(value == "changed" for value in decisions)
    if change_detected and not (
        change_action_summary.strip() and change_action_completed_on.strip()
    ):
        return _redirect("変更ありの項目について、正本へ反映した内容と変更反映完了日を記録してください。")

    required = (reviewed_on, reviewed_by, review_basis, approved_by, approved_at, evidence_name)
    if not all(value.strip() for value in required):
        return _redirect("年次見直しの必須項目をすべて入力してください。")

    annual_cycle_demo_state.record_inventory_risk_review(
        reviewed_on=reviewed_on,
        reviewed_by=reviewed_by,
        review_basis=review_basis,
        business_change_result=business_change_result,
        personal_information_result=personal_information_result,
        risk_result=risk_result,
        control_result=control_result,
        personal_information_count=context.confirmed_personal_information_count,
        risk_count=context.confirmed_risk_count,
        adopted_control_count=context.adopted_control_count,
        change_action_summary=change_action_summary,
        change_action_completed_on=change_action_completed_on,
        approved_by=approved_by,
        approved_at=approved_at,
        evidence_name=evidence_name,
    )

    result = evaluate_annual_cycle(
        annual_cycle_demo_state.get_state(),
        expected_fiscal_year=profile.fiscal_year,
    )
    if result.complete:
        return _redirect("年度開始の見直し記録が整いました。年間計画の次の運用工程へ進んでください。")
    return _redirect("年次見直し記録を保存しました。未完了項目を確認してください。")
