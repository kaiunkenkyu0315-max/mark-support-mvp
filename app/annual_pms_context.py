"""年間PMS画面で使う既存状態の集約。

教育・委託先・アクセス権限・紙媒体・内部監査等の評価基準は再定義せず、
既存モジュールの評価結果を年間計画へ渡す。
"""

from __future__ import annotations

from dataclasses import dataclass

from app import (
    access_control_demo_state,
    annual_cycle_demo_state,
    company_profile,
    demo_state,
    intake_demo_state,
    paper_demo_state,
    pms_review_demo_state,
    vendor_demo_state,
)
from app.access_control import evaluate_access_control
from app.annual_cycle import evaluate_annual_cycle
from app.annual_cycle_schemas import AnnualCycleEvaluationResult
from app.dashboard import DashboardData, build_dashboard_data
from app.document_routes import get_current_documents
from app.education import evaluate_training
from app.intake_schemas import ControlDecisionStatus, PersonalInformationCandidateStatus
from app.paper import evaluate_paper_management
from app.pms_review import evaluate_pms_review
from app.pms_review_schemas import PmsReviewEvaluationResult
from app.risk_schemas import RiskCandidateStatus
from app.setup_progress import get_effective_setup_status
from app.vendors import evaluate_vendors


@dataclass(frozen=True)
class AnnualPmsContext:
    dashboard_data: DashboardData
    annual_cycle_result: AnnualCycleEvaluationResult
    pms_review_result: PmsReviewEvaluationResult
    confirmed_personal_information_count: int
    confirmed_risk_count: int
    adopted_control_count: int


def build_annual_pms_context() -> AnnualPmsContext:
    intake_state = intake_demo_state.get_state()
    education_state = demo_state.get_state()
    vendor_state = vendor_demo_state.get_state()
    access_state = access_control_demo_state.get_state()
    paper_state = paper_demo_state.get_state()

    dashboard_data = build_dashboard_data(
        setup_status=get_effective_setup_status(intake_state),
        candidates=intake_state.candidates,
        risks=intake_state.risks,
        control_suggestions=intake_state.control_suggestions,
        documents=get_current_documents(),
        education_result=evaluate_training(
            education_state.employees,
            education_state.control,
            education_state.plan,
            education_state.records,
        ),
        vendor_result=evaluate_vendors(
            vendor_state.vendors,
            vendor_state.control,
            vendor_state.assessments,
            vendor_state.contracts,
        ),
        access_control_result=evaluate_access_control(
            access_state.accounts,
            access_state.control,
            access_state.cycle,
        ),
        paper_result=evaluate_paper_management(paper_state.control, paper_state.status),
    )

    profile = company_profile.get_state()
    return AnnualPmsContext(
        dashboard_data=dashboard_data,
        annual_cycle_result=evaluate_annual_cycle(
            annual_cycle_demo_state.get_state(),
            expected_fiscal_year=profile.fiscal_year,
        ),
        pms_review_result=evaluate_pms_review(pms_review_demo_state.get_state()),
        confirmed_personal_information_count=sum(
            1
            for candidate in intake_state.candidates
            if candidate.status == PersonalInformationCandidateStatus.CONFIRMED
        ),
        confirmed_risk_count=sum(
            1 for risk in intake_state.risks if risk.status == RiskCandidateStatus.CONFIRMED
        ),
        adopted_control_count=sum(
            1
            for suggestion in intake_state.control_suggestions
            if suggestion.status == ControlDecisionStatus.ADOPTED
        ),
    )
