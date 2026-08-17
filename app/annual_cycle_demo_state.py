"""年間PMS運用のインメモリ検証状態。"""

from __future__ import annotations

from app.annual_cycle_schemas import AnnualCycleState


_state = AnnualCycleState()


def get_state() -> AnnualCycleState:
    return _state


def reset_state() -> AnnualCycleState:
    global _state
    _state = AnnualCycleState()
    return _state


def record_annual_plan(
    *,
    fiscal_year: int,
    planned_on: str,
    coordinator_name: str,
    privacy_manager_name: str,
    audit_manager_name: str,
    top_management_name: str,
    objectives: str,
    schedule_summary: str,
    approved_by: str,
    approved_at: str,
    evidence_name: str,
) -> None:
    record = _state.plan
    record.fiscal_year = fiscal_year
    record.planned_on = planned_on.strip()
    record.coordinator_name = coordinator_name.strip()
    record.privacy_manager_name = privacy_manager_name.strip()
    record.audit_manager_name = audit_manager_name.strip()
    record.top_management_name = top_management_name.strip()
    record.objectives = objectives.strip()
    record.schedule_summary = schedule_summary.strip()
    record.approved_by = approved_by.strip()
    record.approved_at = approved_at.strip()
    record.evidence_name = evidence_name.strip()


def record_inventory_risk_review(
    *,
    reviewed_on: str,
    reviewed_by: str,
    review_basis: str,
    business_change_result: str,
    personal_information_result: str,
    risk_result: str,
    control_result: str,
    personal_information_count: int,
    risk_count: int,
    adopted_control_count: int,
    change_action_summary: str,
    change_action_completed_on: str,
    approved_by: str,
    approved_at: str,
    evidence_name: str,
) -> None:
    record = _state.inventory_risk_review
    record.reviewed_on = reviewed_on.strip()
    record.reviewed_by = reviewed_by.strip()
    record.review_basis = review_basis.strip()
    record.business_change_result = business_change_result
    record.personal_information_result = personal_information_result
    record.risk_result = risk_result
    record.control_result = control_result
    record.personal_information_count = personal_information_count
    record.risk_count = risk_count
    record.adopted_control_count = adopted_control_count
    record.change_action_summary = change_action_summary.strip()
    record.change_action_completed_on = change_action_completed_on.strip()
    record.approved_by = approved_by.strip()
    record.approved_at = approved_at.strip()
    record.evidence_name = evidence_name.strip()
