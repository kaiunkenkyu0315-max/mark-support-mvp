"""Pマーク新規申請準備の評価ロジック。

既存PMSの準備状況と、申請資格・申請先・提出書類・アカウント・最終確認の記録を評価する。
JIPDECはオンラインと郵送・持参で申請書類の構成が異なるため、申請方法に応じて判定する。
"""

from __future__ import annotations

from app.application_prep_schemas import (
    ApplicationPreparationState,
    ApplicationPrerequisites,
    ApplicationPrepEvaluationResult,
    ApplicationPrepIssue,
)


def evaluate_application_prep(
    state: ApplicationPreparationState,
    prerequisites: ApplicationPrerequisites,
) -> ApplicationPrepEvaluationResult:
    issues: list[ApplicationPrepIssue] = []

    destination_complete = bool(
        state.eligibility_confirmed
        and state.examining_body_name
        and state.application_method in {"online", "mail", "other"}
        and state.uses_jipdec_forms is not None
    )
    if not destination_complete:
        issues.append(
            ApplicationPrepIssue(
                "APP-001",
                "申請資格・申請先・申請方法・使用する申請様式体系を確認してください。",
            )
        )

    prerequisites_complete = prerequisites.complete
    if not prerequisites.company_profile_ready:
        issues.append(ApplicationPrepIssue("APP-002", "会社・PMS基本情報が不足しています。"))
    if not prerequisites.pms_documents_ready:
        issues.append(ApplicationPrepIssue("APP-003", "提出前にPMS文書の準備を完了してください。"))
    if not prerequisites.operations_ready:
        issues.append(ApplicationPrepIssue("APP-004", "採用した管理策の運用記録を完了してください。"))
    if not prerequisites.pms_review_ready:
        issues.append(ApplicationPrepIssue("APP-005", "内部監査・是正・マネジメントレビューを完了してください。"))

    if state.uses_jipdec_forms is True and state.application_method == "online":
        forms_complete = all(
            (
                state.business_overview_prepared,
                state.office_list_prepared,
                state.pms_document_list_prepared,
                state.education_summary_prepared,
                state.audit_mr_summary_prepared,
            )
        )
        if not forms_complete:
            issues.append(
                ApplicationPrepIssue(
                    "APP-006",
                    "JIPDECオンライン新規申請の申請様式4〜8をすべて準備してください。",
                )
            )
    elif state.uses_jipdec_forms is True:
        forms_complete = state.jipdec_mail_form_set_prepared
        if not forms_complete:
            issues.append(
                ApplicationPrepIssue(
                    "APP-006",
                    "JIPDECの郵送・持参用『新規申請書類一式』を準備してください。",
                )
            )
    elif state.uses_jipdec_forms is False:
        forms_complete = state.other_form_set_prepared
        if not forms_complete:
            issues.append(
                ApplicationPrepIssue(
                    "APP-007",
                    "申請先の指定審査機関が定める新規申請様式一式を準備してください。",
                )
            )
    else:
        forms_complete = False

    account_complete = (
        state.online_account_ready is True
        if state.application_method == "online"
        else True
    )
    submission_data_complete = state.pms_document_bundle_prepared and account_complete
    if not state.pms_document_bundle_prepared:
        issues.append(
            ApplicationPrepIssue(
                "APP-008",
                "申請方法に応じて、提出するPMS文書一式を準備してください。",
            )
        )
    if state.application_method == "online" and state.online_account_ready is not True:
        issues.append(
            ApplicationPrepIssue(
                "APP-009",
                "オンライン申請に使用するアカウントの準備を確認してください。",
            )
        )

    final_review_complete = bool(
        state.final_reviewed_by
        and state.final_reviewed_at
        and state.submission_ready_confirmed
    )
    if not final_review_complete:
        issues.append(
            ApplicationPrepIssue(
                "APP-010",
                "申請書類と提出データの最終確認記録を残してください。",
            )
        )

    return ApplicationPrepEvaluationResult(
        issues=issues,
        destination_complete=destination_complete,
        prerequisites_complete=prerequisites_complete,
        forms_complete=forms_complete,
        submission_data_complete=submission_data_complete,
        final_review_complete=final_review_complete,
    )
