"""Pマーク新規申請準備画面のFastAPIルート。"""

from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse, RedirectResponse

from app import application_prep_demo_state
from app.application_prep import evaluate_application_prep
from app.application_prep_context import build_application_prerequisites
from app.application_prep_view import render_application_prep_page

router = APIRouter(prefix="/application-prep", tags=["application-prep"])


def _redirect(message: str) -> RedirectResponse:
    return RedirectResponse(url=f"/application-prep?flash={quote(message)}", status_code=303)


@router.get("", response_class=HTMLResponse)
def application_prep_page(flash: str | None = None) -> str:
    return render_application_prep_page(
        application_prep_demo_state.get_state(),
        build_application_prerequisites(),
        flash=flash,
    )


@router.post("/destination")
def save_destination(
    eligibility_confirmed: str | None = Form(None),
    examining_body_name: str = Form(...),
    application_method: str = Form(...),
    uses_jipdec_forms: str = Form(...),
) -> RedirectResponse:
    if eligibility_confirmed != "yes":
        return _redirect("申請資格・欠格事由・担当者要件を確認してください。")
    if not examining_body_name.strip():
        return _redirect("申請先の審査機関を入力してください。")
    if application_method not in {"online", "mail", "other"}:
        return _redirect("申請方法を選択してください。")
    if uses_jipdec_forms not in {"yes", "no"}:
        return _redirect("使用する申請様式体系を選択してください。")
    if uses_jipdec_forms == "yes" and application_method == "other":
        return _redirect("JIPDECの申請方法はオンラインまたは郵送・持参から選択してください。")

    application_prep_demo_state.record_destination(
        eligibility_confirmed=True,
        examining_body_name=examining_body_name,
        application_method=application_method,
        uses_jipdec_forms=uses_jipdec_forms == "yes",
    )
    return _redirect("申請資格・申請先・申請方法を記録しました。")


@router.post("/forms")
def save_forms(
    business_overview_prepared: str | None = Form(None),
    office_list_prepared: str | None = Form(None),
    pms_document_list_prepared: str | None = Form(None),
    education_summary_prepared: str | None = Form(None),
    audit_mr_summary_prepared: str | None = Form(None),
    jipdec_mail_form_set_prepared: str | None = Form(None),
    other_form_set_prepared: str | None = Form(None),
) -> RedirectResponse:
    before = evaluate_application_prep(
        application_prep_demo_state.get_state(),
        build_application_prerequisites(),
    )
    if not before.destination_complete:
        return _redirect("先に申請資格・申請先・申請方法を確定してください。")

    application_prep_demo_state.record_forms(
        business_overview_prepared=business_overview_prepared == "yes",
        office_list_prepared=office_list_prepared == "yes",
        pms_document_list_prepared=pms_document_list_prepared == "yes",
        education_summary_prepared=education_summary_prepared == "yes",
        audit_mr_summary_prepared=audit_mr_summary_prepared == "yes",
        jipdec_mail_form_set_prepared=jipdec_mail_form_set_prepared == "yes",
        other_form_set_prepared=other_form_set_prepared == "yes",
    )
    return _redirect("申請様式の準備状況を記録しました。")


@router.post("/submission-data")
def save_submission_data(
    pms_document_bundle_prepared: str | None = Form(None),
    online_account_ready: str | None = Form(None),
) -> RedirectResponse:
    before = evaluate_application_prep(
        application_prep_demo_state.get_state(),
        build_application_prerequisites(),
    )
    if not before.destination_complete or not before.forms_complete:
        return _redirect("先に申請先と申請様式の準備を完了してください。")
    if not before.prerequisites_complete:
        return _redirect("PMS文書・運用・内部監査等の前提記録を先に完了してください。")

    application_prep_demo_state.record_submission_data(
        pms_document_bundle_prepared=pms_document_bundle_prepared == "yes",
        online_account_ready=(online_account_ready == "yes") if online_account_ready is not None else None,
    )
    return _redirect("提出データ・アカウントの準備状況を記録しました。")


@router.post("/final-review")
def save_final_review(
    final_reviewed_by: str = Form(...),
    final_reviewed_at: str = Form(...),
    submission_ready_confirmed: str | None = Form(None),
) -> RedirectResponse:
    before = evaluate_application_prep(
        application_prep_demo_state.get_state(),
        build_application_prerequisites(),
    )
    if not (
        before.destination_complete
        and before.prerequisites_complete
        and before.forms_complete
        and before.submission_data_complete
    ):
        return _redirect("現在の工程では最終確認を登録できません。先行する準備を完了してください。")

    application_prep_demo_state.record_final_review(
        final_reviewed_by=final_reviewed_by,
        final_reviewed_at=final_reviewed_at,
        submission_ready_confirmed=submission_ready_confirmed == "yes",
    )
    result = evaluate_application_prep(
        application_prep_demo_state.get_state(),
        build_application_prerequisites(),
    )
    if result.complete:
        return _redirect("最終確認を記録しました。申請提出前の準備確認が完了しました。")
    return _redirect("最終確認を記録しました。未完了項目を確認してください。")
