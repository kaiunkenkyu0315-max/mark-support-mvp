"""内部監査・是正処置・マネジメントレビューの最小データモデル。

JIS Q 15001:2023準拠のPマーク構築・運用指針 J.6.2 / J.6.3 / J.7.1 を
MVPで記録できる粒度へ落とし込む。単なる完了フラグではなく、後から説明できる
事実・記録を保持し、その記録を評価ロジックが判定する。
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class InternalAuditRecord:
    audit_date: str | None = None
    purpose: str | None = None
    criteria: str | None = None
    scope: str | None = None
    auditor_name: str | None = None
    auditor_independence_confirmed: bool = False
    result_summary: str | None = None
    nonconformity_count: int | None = None
    report_date: str | None = None
    reported_to_top_management: bool = False
    evidence_name: str | None = None


@dataclass
class CorrectiveActionRecord:
    finding_summary: str | None = None
    immediate_action: str | None = None
    root_cause: str | None = None
    corrective_action: str | None = None
    implemented_on: str | None = None
    effectiveness_result: str | None = None  # effective / ineffective
    effectiveness_checked_on: str | None = None
    approved_by: str | None = None
    approved_at: str | None = None
    evidence_name: str | None = None


@dataclass
class ManagementReviewRecord:
    review_date: str | None = None
    top_management_name: str | None = None
    input_summary: str | None = None
    decision_summary: str | None = None
    changes_needed: bool | None = None
    improvement_actions: str | None = None
    evidence_name: str | None = None


@dataclass
class PmsReviewState:
    audit: InternalAuditRecord = field(default_factory=InternalAuditRecord)
    corrective_action: CorrectiveActionRecord = field(default_factory=CorrectiveActionRecord)
    management_review: ManagementReviewRecord = field(default_factory=ManagementReviewRecord)


@dataclass(frozen=True)
class PmsReviewIssue:
    rule_id: str
    message: str


@dataclass(frozen=True)
class PmsReviewEvaluationResult:
    issues: list[PmsReviewIssue]
    audit_complete: bool
    corrective_required: bool
    corrective_complete: bool
    management_review_complete: bool

    @property
    def complete(self) -> bool:
        return (
            self.audit_complete
            and (not self.corrective_required or self.corrective_complete)
            and self.management_review_complete
        )
