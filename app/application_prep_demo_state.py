"""申請準備MVPのインメモリ状態と記録操作。"""

from __future__ import annotations

from app.application_prep_schemas import ApplicationPreparationState


_state = ApplicationPreparationState()


def get_state() -> ApplicationPreparationState:
    return _state


def reset_state() -> ApplicationPreparationState:
    global _state
    _state = ApplicationPreparationState()
    return _state


def _clear_forms_and_later(state: ApplicationPreparationState) -> None:
    state.business_overview_prepared = False
    state.office_list_prepared = False
    state.pms_document_list_prepared = False
    state.education_summary_prepared = False
    state.audit_mr_summary_prepared = False
    state.jipdec_mail_form_set_prepared = False
    state.other_form_set_prepared = False
    _clear_submission_and_final(state)


def _clear_submission_and_final(state: ApplicationPreparationState) -> None:
    state.pms_document_bundle_prepared = False
    state.online_account_ready = None
    _clear_final_review(state)


def _clear_final_review(state: ApplicationPreparationState) -> None:
    state.final_reviewed_by = None
    state.final_reviewed_at = None
    state.submission_ready_confirmed = False


def record_destination(
    *,
    eligibility_confirmed: bool,
    examining_body_name: str,
    application_method: str,
    uses_jipdec_forms: bool,
) -> None:
    state = _state
    new_destination = (
        eligibility_confirmed,
        examining_body_name.strip() or None,
        application_method,
        uses_jipdec_forms,
    )
    old_destination = (
        state.eligibility_confirmed,
        state.examining_body_name,
        state.application_method,
        state.uses_jipdec_forms,
    )
    if new_destination != old_destination:
        _clear_forms_and_later(state)

    state.eligibility_confirmed = eligibility_confirmed
    state.examining_body_name = new_destination[1]
    state.application_method = application_method
    state.uses_jipdec_forms = uses_jipdec_forms


def record_forms(
    *,
    business_overview_prepared: bool = False,
    office_list_prepared: bool = False,
    pms_document_list_prepared: bool = False,
    education_summary_prepared: bool = False,
    audit_mr_summary_prepared: bool = False,
    jipdec_mail_form_set_prepared: bool = False,
    other_form_set_prepared: bool = False,
) -> None:
    state = _state
    old_forms = (
        state.business_overview_prepared,
        state.office_list_prepared,
        state.pms_document_list_prepared,
        state.education_summary_prepared,
        state.audit_mr_summary_prepared,
        state.jipdec_mail_form_set_prepared,
        state.other_form_set_prepared,
    )

    if state.uses_jipdec_forms is True and state.application_method == "online":
        state.business_overview_prepared = business_overview_prepared
        state.office_list_prepared = office_list_prepared
        state.pms_document_list_prepared = pms_document_list_prepared
        state.education_summary_prepared = education_summary_prepared
        state.audit_mr_summary_prepared = audit_mr_summary_prepared
        state.jipdec_mail_form_set_prepared = False
        state.other_form_set_prepared = False
    elif state.uses_jipdec_forms is True:
        state.business_overview_prepared = False
        state.office_list_prepared = False
        state.pms_document_list_prepared = False
        state.education_summary_prepared = False
        state.audit_mr_summary_prepared = False
        state.jipdec_mail_form_set_prepared = jipdec_mail_form_set_prepared
        state.other_form_set_prepared = False
    elif state.uses_jipdec_forms is False:
        state.business_overview_prepared = False
        state.office_list_prepared = False
        state.pms_document_list_prepared = False
        state.education_summary_prepared = False
        state.audit_mr_summary_prepared = False
        state.jipdec_mail_form_set_prepared = False
        state.other_form_set_prepared = other_form_set_prepared

    new_forms = (
        state.business_overview_prepared,
        state.office_list_prepared,
        state.pms_document_list_prepared,
        state.education_summary_prepared,
        state.audit_mr_summary_prepared,
        state.jipdec_mail_form_set_prepared,
        state.other_form_set_prepared,
    )
    if new_forms != old_forms:
        _clear_submission_and_final(state)


def record_submission_data(
    *,
    pms_document_bundle_prepared: bool,
    online_account_ready: bool | None,
) -> None:
    state = _state
    normalized_account = (
        online_account_ready if state.application_method == "online" else None
    )
    changed = (
        state.pms_document_bundle_prepared != pms_document_bundle_prepared
        or state.online_account_ready != normalized_account
    )
    state.pms_document_bundle_prepared = pms_document_bundle_prepared
    state.online_account_ready = normalized_account
    if changed:
        _clear_final_review(state)


def record_final_review(
    *,
    final_reviewed_by: str,
    final_reviewed_at: str,
    submission_ready_confirmed: bool,
) -> None:
    state = _state
    state.final_reviewed_by = final_reviewed_by.strip() or None
    state.final_reviewed_at = final_reviewed_at.strip() or None
    state.submission_ready_confirmed = submission_ready_confirmed
