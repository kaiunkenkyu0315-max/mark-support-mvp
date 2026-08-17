from app import application_prep_demo_state


def test_changing_application_destination_invalidates_downstream_confirmations():
    application_prep_demo_state.reset_state()
    application_prep_demo_state.record_destination(
        eligibility_confirmed=True,
        examining_body_name="JIPDEC",
        application_method="online",
        uses_jipdec_forms=True,
    )
    application_prep_demo_state.record_forms(
        business_overview_prepared=True,
        office_list_prepared=True,
        pms_document_list_prepared=True,
        education_summary_prepared=True,
        audit_mr_summary_prepared=True,
    )
    application_prep_demo_state.record_submission_data(
        pms_document_bundle_prepared=True,
        online_account_ready=True,
    )
    application_prep_demo_state.record_final_review(
        final_reviewed_by="担当者",
        final_reviewed_at="2026-08-10",
        submission_ready_confirmed=True,
    )

    application_prep_demo_state.record_destination(
        eligibility_confirmed=True,
        examining_body_name="JIPDEC",
        application_method="mail",
        uses_jipdec_forms=True,
    )
    state = application_prep_demo_state.get_state()

    assert state.business_overview_prepared is False
    assert state.jipdec_mail_form_set_prepared is False
    assert state.pms_document_bundle_prepared is False
    assert state.online_account_ready is None
    assert state.final_reviewed_by is None
    assert state.final_reviewed_at is None
    assert state.submission_ready_confirmed is False

    application_prep_demo_state.reset_state()
