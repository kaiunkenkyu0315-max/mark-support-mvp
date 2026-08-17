from app.application_prep import evaluate_application_prep
from app.application_prep_schemas import ApplicationPreparationState, ApplicationPrerequisites


def _ready_prerequisites() -> ApplicationPrerequisites:
    return ApplicationPrerequisites(
        company_profile_ready=True,
        pms_documents_ready=True,
        operations_ready=True,
        pms_review_ready=True,
    )


def test_jipdec_online_application_requires_forms_4_to_8_and_online_account():
    state = ApplicationPreparationState(
        examining_body_name="JIPDEC",
        application_method="online",
        uses_jipdec_forms=True,
        business_overview_prepared=True,
        office_list_prepared=True,
        pms_document_list_prepared=True,
        education_summary_prepared=True,
        audit_mr_summary_prepared=False,
        pms_document_bundle_prepared=True,
        online_account_ready=False,
    )

    result = evaluate_application_prep(state, _ready_prerequisites())

    assert result.destination_complete is True
    assert result.forms_complete is False
    assert result.submission_data_complete is False
    assert {issue.rule_id for issue in result.issues} >= {"APP-006", "APP-009"}


def test_non_jipdec_mail_application_uses_other_form_set_and_does_not_require_online_account():
    state = ApplicationPreparationState(
        examining_body_name="指定審査機関A",
        application_method="mail",
        uses_jipdec_forms=False,
        other_form_set_prepared=True,
        pms_document_bundle_prepared=True,
        final_reviewed_by="担当者",
        final_reviewed_at="2026-08-10",
        submission_ready_confirmed=True,
    )

    result = evaluate_application_prep(state, _ready_prerequisites())

    assert result.forms_complete is True
    assert result.submission_data_complete is True
    assert result.final_review_complete is True
    assert result.complete is True
    assert "APP-009" not in {issue.rule_id for issue in result.issues}


def test_application_cannot_be_complete_when_existing_pms_prerequisites_are_missing():
    state = ApplicationPreparationState(
        examining_body_name="JIPDEC",
        application_method="mail",
        uses_jipdec_forms=True,
        business_overview_prepared=True,
        office_list_prepared=True,
        pms_document_list_prepared=True,
        education_summary_prepared=True,
        audit_mr_summary_prepared=True,
        pms_document_bundle_prepared=True,
        final_reviewed_by="担当者",
        final_reviewed_at="2026-08-10",
        submission_ready_confirmed=True,
    )
    prerequisites = ApplicationPrerequisites(
        company_profile_ready=True,
        pms_documents_ready=True,
        operations_ready=True,
        pms_review_ready=False,
    )

    result = evaluate_application_prep(state, prerequisites)

    assert result.prerequisites_complete is False
    assert result.complete is False
    assert "APP-005" in {issue.rule_id for issue in result.issues}
