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


def record_destination(
    *,
    examining_body_name: str,
    application_method: str,
    uses_jipdec_forms: bool,
) -> None:
    state = _state
    state.examining_body_name = examining_body_name.strip() or None
    state.application_method = application_method
    state.uses_jipdec_forms = uses_jipdec_forms

    # 申請先・様式体系を変更したら、別様式の完了状態を持ち越さない。
    if uses_jipdec_forms:
        state.other_form_set_prepared = False
    else:
        state.business_overview_prepared = False
        state.office_list_prepared = False
        state.pms_document_list_prepared = False
        state.education_summary_prepared = False
        state.audit_mr_summary_prepared = False

    if application_method != "online":
        state.online_account_ready = None


def record_forms(
    *,
    business_overview_prepared: bool = False,
    office_list_prepared: bool = False,
    pms_document_list_prepared: bool = False,
    education_summary_prepared: bool = False,
    audit_mr_summary_prepared: bool = False,
    other_form_set_prepared: bool = False,
) -> None:
    state = _state
    if state.uses_jipdec_forms is True:
        state.business_overview_prepared = business_overview_prepared
        state.office_list_prepared = office_list_prepared
        state.pms_document_list_prepared = pms_document_list_prepared
        state.education_summary_prepared = education_summary_prepared
        state.audit_mr_summary_prepared = audit_mr_summary_prepared
        state.other_form_set_prepared = False
    elif state.uses_jipdec_forms is False:
        state.other_form_set_prepared = other_form_set_prepared


def record_submission_data(
    *,
    pms_document_bundle_prepared: bool,
    online_account_ready: bool | None,
) -> None:
    state = _state
    state.pms_document_bundle_prepared = pms_document_bundle_prepared
    state.online_account_ready = (
        online_account_ready if state.application_method == "online" else None
    )


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
