"""Pマーク新規申請準備の最小データモデル。

審査機関ごとに申請様式が異なるため、申請先・申請方法・利用する様式体系を
明示判断として保持する。JIPDEC新規申請を選んだ場合だけ、現行の申請様式4〜8を
個別に確認する。単なる「申請可能」フラグではなく、提出前に説明できる事実を記録する。
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ApplicationPreparationState:
    # STEP1: 申請先・方法
    examining_body_name: str | None = None
    application_method: str | None = None  # online / mail / other
    uses_jipdec_forms: bool | None = None

    # STEP2: 申請様式
    business_overview_prepared: bool = False      # JIPDEC 新規 様式4
    office_list_prepared: bool = False            # JIPDEC 新規 様式5
    pms_document_list_prepared: bool = False      # JIPDEC 新規 様式6
    education_summary_prepared: bool = False      # JIPDEC 新規 様式7
    audit_mr_summary_prepared: bool = False       # JIPDEC 新規 様式8
    other_form_set_prepared: bool = False         # JIPDEC以外の審査機関用

    # STEP3: 提出データ・アカウント
    pms_document_bundle_prepared: bool = False
    online_account_ready: bool | None = None

    # STEP4: 最終確認
    final_reviewed_by: str | None = None
    final_reviewed_at: str | None = None
    submission_ready_confirmed: bool = False


@dataclass(frozen=True)
class ApplicationPrerequisites:
    company_profile_ready: bool
    pms_documents_ready: bool
    operations_ready: bool
    pms_review_ready: bool

    @property
    def complete(self) -> bool:
        return (
            self.company_profile_ready
            and self.pms_documents_ready
            and self.operations_ready
            and self.pms_review_ready
        )


@dataclass(frozen=True)
class ApplicationPrepIssue:
    rule_id: str
    message: str


@dataclass(frozen=True)
class ApplicationPrepEvaluationResult:
    issues: list[ApplicationPrepIssue]
    destination_complete: bool
    prerequisites_complete: bool
    forms_complete: bool
    submission_data_complete: bool
    final_review_complete: bool

    @property
    def complete(self) -> bool:
        return (
            self.destination_complete
            and self.prerequisites_complete
            and self.forms_complete
            and self.submission_data_complete
            and self.final_review_complete
        )
