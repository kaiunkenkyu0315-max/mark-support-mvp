"""既存MVP状態から申請準備の前提条件を集約する。

申請準備側で教育・委託先・アクセス権限・紙媒体・PMSレビューの評価基準を
再定義せず、既存評価ロジックと初期設定側の管理策採用判断を正本として利用する。
"""

from __future__ import annotations

from app import (
    access_control_demo_state,
    company_profile,
    demo_state,
    intake_demo_state,
    paper_demo_state,
    pms_review_demo_state,
    vendor_demo_state,
)
from app.access_control import evaluate_access_control
from app.application_prep_schemas import ApplicationPrerequisites
from app.document_routes import get_current_documents
from app.document_schemas import DocumentStatus
from app.education import evaluate_training
from app.intake_schemas import ControlDecisionStatus
from app.paper import evaluate_paper_management
from app.pms_review import evaluate_pms_review
from app.vendors import evaluate_vendors


def build_application_prerequisites() -> ApplicationPrerequisites:
    profile = company_profile.get_state()
    documents = get_current_documents()
    intake_state = intake_demo_state.get_state()

    education_state = demo_state.get_state()
    education_result = evaluate_training(
        education_state.employees,
        education_state.control,
        education_state.plan,
        education_state.records,
    )

    vendor_state = vendor_demo_state.get_state()
    vendor_result = evaluate_vendors(
        vendor_state.vendors,
        vendor_state.control,
        vendor_state.assessments,
        vendor_state.contracts,
    )

    access_state = access_control_demo_state.get_state()
    access_result = evaluate_access_control(
        access_state.accounts,
        access_state.control,
        access_state.cycle,
    )

    paper_state = paper_demo_state.get_state()
    paper_result = evaluate_paper_management(paper_state.control, paper_state.status)

    pms_review_result = evaluate_pms_review(pms_review_demo_state.get_state())

    active_documents = [
        document
        for document in documents
        if document.status != DocumentStatus.NOT_APPLICABLE
    ]
    pms_documents_ready = bool(active_documents) and all(
        document.status == DocumentStatus.READY for document in active_documents
    )

    adopted_ids = {
        suggestion.control_id
        for suggestion in intake_state.control_suggestions
        if suggestion.status == ControlDecisionStatus.ADOPTED
    }
    results_by_control = {
        "education": education_result,
        "vendor_management": vendor_result,
        "access_control": access_result,
        "paper_management": paper_result,
    }
    operations_ready = all(
        not results_by_control[control_id].issues
        for control_id in adopted_ids
        if control_id in results_by_control
    )

    return ApplicationPrerequisites(
        company_profile_ready=profile.configured,
        pms_documents_ready=pms_documents_ready,
        operations_ready=operations_ready,
        pms_review_ready=pms_review_result.complete,
    )
