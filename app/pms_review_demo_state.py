"""内部監査・是正処置・マネジメントレビューのインメモリデモ状態。"""

from __future__ import annotations

from app.pms_review_schemas import PmsReviewState


_state = PmsReviewState()


def get_state() -> PmsReviewState:
    return _state


def reset_state() -> PmsReviewState:
    global _state
    _state = PmsReviewState()
    return _state


def record_internal_audit(
    *,
    audit_date: str,
    purpose: str,
    criteria: str,
    scope: str,
    auditor_name: str,
    auditor_independence_confirmed: bool,
    result_summary: str,
    nonconformity_count: int,
    report_date: str,
    reported_to_top_management: bool,
    evidence_name: str,
) -> None:
    audit = _state.audit
    audit.audit_date = audit_date.strip() or None
    audit.purpose = purpose.strip() or None
    audit.criteria = criteria.strip() or None
    audit.scope = scope.strip() or None
    audit.auditor_name = auditor_name.strip() or None
    audit.auditor_independence_confirmed = auditor_independence_confirmed
    audit.result_summary = result_summary.strip() or None
    audit.nonconformity_count = max(0, nonconformity_count)
    audit.report_date = report_date.strip() or None
    audit.reported_to_top_management = reported_to_top_management
    audit.evidence_name = evidence_name.strip() or None

    # 監査結果が変わった場合、不要な是正記録を残して「実施済み」に見せない。
    if audit.nonconformity_count == 0:
        from app.pms_review_schemas import CorrectiveActionRecord

        _state.corrective_action = CorrectiveActionRecord()


def record_corrective_action(
    *,
    finding_summary: str,
    immediate_action: str,
    root_cause: str,
    corrective_action: str,
    implemented_on: str,
    effectiveness_result: str,
    effectiveness_checked_on: str,
    approved_by: str,
    approved_at: str,
    evidence_name: str,
) -> None:
    record = _state.corrective_action
    record.finding_summary = finding_summary.strip() or None
    record.immediate_action = immediate_action.strip() or None
    record.root_cause = root_cause.strip() or None
    record.corrective_action = corrective_action.strip() or None
    record.implemented_on = implemented_on.strip() or None
    record.effectiveness_result = effectiveness_result.strip() or None
    record.effectiveness_checked_on = effectiveness_checked_on.strip() or None
    record.approved_by = approved_by.strip() or None
    record.approved_at = approved_at.strip() or None
    record.evidence_name = evidence_name.strip() or None


def record_management_review(
    *,
    review_date: str,
    top_management_name: str,
    input_summary: str,
    decision_summary: str,
    changes_needed: bool,
    improvement_actions: str,
    evidence_name: str,
) -> None:
    review = _state.management_review
    review.review_date = review_date.strip() or None
    review.top_management_name = top_management_name.strip() or None
    review.input_summary = input_summary.strip() or None
    review.decision_summary = decision_summary.strip() or None
    review.changes_needed = changes_needed
    review.improvement_actions = improvement_actions.strip() or None
    review.evidence_name = evidence_name.strip() or None
