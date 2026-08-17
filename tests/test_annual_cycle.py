from app.annual_cycle import evaluate_annual_cycle
from app.annual_cycle_schemas import AnnualCycleState


def _complete_plan(state: AnnualCycleState) -> None:
    plan = state.plan
    plan.fiscal_year = 2026
    plan.planned_on = "2026-04-01"
    plan.coordinator_name = "山田 花子"
    plan.privacy_manager_name = "鈴木 花子"
    plan.audit_manager_name = "佐藤 次郎"
    plan.top_management_name = "山田 太郎"
    plan.objectives = "PMSを有効に運用する"
    plan.schedule_summary = "年次見直し、教育、監査、マネジメントレビューを実施する"
    plan.approved_by = "山田 太郎"
    plan.approved_at = "2026-04-01"
    plan.evidence_name = "年間PMS運用計画書"


def _complete_review(state: AnnualCycleState) -> None:
    review = state.inventory_risk_review
    review.reviewed_on = "2026-04-05"
    review.reviewed_by = "山田 花子"
    review.review_basis = "業務、台帳、リスク、管理策を確認"
    review.business_change_result = "no_change"
    review.personal_information_result = "no_change"
    review.risk_result = "no_change"
    review.control_result = "no_change"
    review.personal_information_count = 5
    review.risk_count = 5
    review.adopted_control_count = 4
    review.approved_by = "鈴木 花子"
    review.approved_at = "2026-04-05"
    review.evidence_name = "個人情報・リスク年次見直し記録"


def test_annual_cycle_requires_structured_plan_before_review():
    state = AnnualCycleState()
    result = evaluate_annual_cycle(state, expected_fiscal_year=2026)

    assert result.plan_complete is False
    assert result.inventory_risk_review_complete is False
    assert {issue.rule_id for issue in result.issues} == {"ANN-001", "ANN-002"}


def test_no_change_review_completes_when_plan_and_snapshot_are_recorded():
    state = AnnualCycleState()
    _complete_plan(state)
    _complete_review(state)

    result = evaluate_annual_cycle(state, expected_fiscal_year=2026)

    assert result.plan_complete is True
    assert result.inventory_risk_review_complete is True
    assert result.complete is True
    assert result.issues == []


def test_changed_review_requires_change_action_and_completion_date():
    state = AnnualCycleState()
    _complete_plan(state)
    _complete_review(state)
    state.inventory_risk_review.risk_result = "changed"

    result = evaluate_annual_cycle(state, expected_fiscal_year=2026)
    assert result.inventory_risk_review_complete is False
    assert any("反映した内容と完了日" in issue.message for issue in result.issues)

    state.inventory_risk_review.change_action_summary = "リスク評価と管理策を更新"
    state.inventory_risk_review.change_action_completed_on = "2026-04-06"
    result = evaluate_annual_cycle(state, expected_fiscal_year=2026)
    assert result.complete is True


def test_plan_for_wrong_fiscal_year_is_not_complete():
    state = AnnualCycleState()
    _complete_plan(state)
    state.plan.fiscal_year = 2025

    result = evaluate_annual_cycle(state, expected_fiscal_year=2026)

    assert result.plan_complete is False
