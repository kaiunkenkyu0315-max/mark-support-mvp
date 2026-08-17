"""年間PMS運用の年度開始・定期見直し記録。

個人情報台帳・リスク・管理策そのものは既存の初期設定側を正本とし、ここでは
年度計画と「何を確認し、変更有無をどう判断し、必要な変更をどう反映したか」の
年次記録だけを保持する。
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AnnualOperationPlanRecord:
    fiscal_year: int | None = None
    planned_on: str | None = None
    coordinator_name: str | None = None
    privacy_manager_name: str | None = None
    audit_manager_name: str | None = None
    top_management_name: str | None = None
    objectives: str | None = None
    schedule_summary: str | None = None
    approved_by: str | None = None
    approved_at: str | None = None
    evidence_name: str | None = None


@dataclass
class AnnualInventoryRiskReviewRecord:
    reviewed_on: str | None = None
    reviewed_by: str | None = None
    review_basis: str | None = None

    business_change_result: str | None = None  # changed / no_change
    personal_information_result: str | None = None  # changed / no_change
    risk_result: str | None = None  # changed / no_change
    control_result: str | None = None  # changed / no_change

    personal_information_count: int | None = None
    risk_count: int | None = None
    adopted_control_count: int | None = None

    change_action_summary: str | None = None
    change_action_completed_on: str | None = None

    approved_by: str | None = None
    approved_at: str | None = None
    evidence_name: str | None = None


@dataclass
class AnnualCycleState:
    plan: AnnualOperationPlanRecord = field(default_factory=AnnualOperationPlanRecord)
    inventory_risk_review: AnnualInventoryRiskReviewRecord = field(
        default_factory=AnnualInventoryRiskReviewRecord
    )


@dataclass(frozen=True)
class AnnualCycleIssue:
    rule_id: str
    message: str


@dataclass(frozen=True)
class AnnualCycleEvaluationResult:
    issues: list[AnnualCycleIssue]
    plan_complete: bool
    inventory_risk_review_complete: bool

    @property
    def complete(self) -> bool:
        return self.plan_complete and self.inventory_risk_review_complete
