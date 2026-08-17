"""年度運用計画と個人情報・リスク定期見直しの整合性評価。"""

from __future__ import annotations

from app.annual_cycle_schemas import AnnualCycleEvaluationResult, AnnualCycleIssue, AnnualCycleState


_VALID_REVIEW_RESULTS = {"changed", "no_change"}


def _filled(value: str | None) -> bool:
    return bool((value or "").strip())


def evaluate_annual_cycle(
    state: AnnualCycleState,
    *,
    expected_fiscal_year: int,
) -> AnnualCycleEvaluationResult:
    issues: list[AnnualCycleIssue] = []
    plan = state.plan

    plan_complete = all(
        (
            plan.fiscal_year == expected_fiscal_year,
            _filled(plan.planned_on),
            _filled(plan.coordinator_name),
            _filled(plan.privacy_manager_name),
            _filled(plan.audit_manager_name),
            _filled(plan.top_management_name),
            _filled(plan.objectives),
            _filled(plan.schedule_summary),
            _filled(plan.approved_by),
            _filled(plan.approved_at),
            _filled(plan.evidence_name),
        )
    )
    if not plan_complete:
        issues.append(
            AnnualCycleIssue(
                "ANN-001",
                "対象年度のPMS運用計画・担当体制・承認・証跡を完成させてください。",
            )
        )

    review = state.inventory_risk_review
    decisions = (
        review.business_change_result,
        review.personal_information_result,
        review.risk_result,
        review.control_result,
    )
    decisions_complete = all(value in _VALID_REVIEW_RESULTS for value in decisions)
    snapshots_complete = all(
        value is not None and value >= 0
        for value in (
            review.personal_information_count,
            review.risk_count,
            review.adopted_control_count,
        )
    )
    change_detected = any(value == "changed" for value in decisions)
    change_action_complete = (
        not change_detected
        or (
            _filled(review.change_action_summary)
            and _filled(review.change_action_completed_on)
        )
    )

    inventory_risk_review_complete = bool(
        plan_complete
        and _filled(review.reviewed_on)
        and _filled(review.reviewed_by)
        and _filled(review.review_basis)
        and decisions_complete
        and snapshots_complete
        and change_action_complete
        and _filled(review.approved_by)
        and _filled(review.approved_at)
        and _filled(review.evidence_name)
    )

    if not inventory_risk_review_complete:
        if change_detected and not change_action_complete:
            message = (
                "変更ありと判断した項目について、既存の台帳・リスク・管理策へ反映した内容と完了日を記録してください。"
            )
        else:
            message = (
                "個人情報台帳・リスク・管理策の年次見直し結果、変更有無、承認・証跡を完成させてください。"
            )
        issues.append(AnnualCycleIssue("ANN-002", message))

    return AnnualCycleEvaluationResult(
        issues=issues,
        plan_complete=plan_complete,
        inventory_risk_review_complete=inventory_risk_review_complete,
    )
