"""内部監査・是正処置・マネジメントレビュー画面のFastAPIルート。"""

from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse, RedirectResponse

from app import pms_review_demo_state
from app.evidence_panel_view import append_evidence_panel, render_evidence_panel
from app.evidence_store import get_default_evidence_store
from app.pms_review import evaluate_pms_review
from app.pms_review_view import render_pms_review_page

router = APIRouter(prefix="/pms-review", tags=["pms-review"])


def _redirect(message: str) -> RedirectResponse:
    return RedirectResponse(url=f"/pms-review?flash={quote(message)}", status_code=303)


def _render_page(flash: str | None = None) -> str:
    html = render_pms_review_page(pms_review_demo_state.get_state(), flash=flash)
    store = get_default_evidence_store()
    audit_panel = render_evidence_panel(
        area="internal_audit",
        files=store.list("internal_audit"),
        heading="内部監査の証跡ファイル",
        description="内部監査報告書、チェックリスト、監査メモなどの実ファイルを補足証跡として添付できます。",
        canonical_record_text="画面上の内部監査日・基準・範囲・結果・報告記録が正本です。",
    )
    management_review_panel = render_evidence_panel(
        area="management_review",
        files=store.list("management_review"),
        heading="マネジメントレビューの証跡ファイル",
        description="マネジメントレビュー議事録、説明資料、意思決定記録などの実ファイルを補足証跡として添付できます。",
        canonical_record_text="画面上のレビュー日・インプット・決定事項・改善記録が正本です。",
    )
    html = append_evidence_panel(html, audit_panel)
    return append_evidence_panel(html, management_review_panel)


@router.get("", response_class=HTMLResponse)
def pms_review_page(flash: str | None = None) -> str:
    return _render_page(flash)


@router.post("/audit")
def save_audit(
    audit_date: str = Form(...),
    purpose: str = Form(...),
    criteria: str = Form(...),
    scope: str = Form(...),
    auditor_name: str = Form(...),
    auditor_independence_confirmed: str | None = Form(None),
    result_summary: str = Form(...),
    nonconformity_count: int = Form(...),
    report_date: str = Form(...),
    reported_to_top_management: str | None = Form(None),
    evidence_name: str = Form(...),
) -> RedirectResponse:
    pms_review_demo_state.record_internal_audit(
        audit_date=audit_date,
        purpose=purpose,
        criteria=criteria,
        scope=scope,
        auditor_name=auditor_name,
        auditor_independence_confirmed=auditor_independence_confirmed == "yes",
        result_summary=result_summary,
        nonconformity_count=nonconformity_count,
        report_date=report_date,
        reported_to_top_management=reported_to_top_management == "yes",
        evidence_name=evidence_name,
    )
    result = evaluate_pms_review(pms_review_demo_state.get_state())
    if result.corrective_required:
        return _redirect("内部監査記録を保存しました。不適合があるため、次に是正処置を記録してください。")
    return _redirect("内部監査記録を保存しました。不適合がないため、次にマネジメントレビューへ進みます。")


@router.post("/corrective-action")
def save_corrective_action(
    finding_summary: str = Form(...),
    immediate_action: str = Form(...),
    root_cause: str = Form(...),
    corrective_action: str = Form(...),
    implemented_on: str = Form(...),
    effectiveness_result: str = Form(...),
    effectiveness_checked_on: str = Form(...),
    approved_by: str = Form(...),
    approved_at: str = Form(...),
    evidence_name: str = Form(...),
) -> RedirectResponse:
    before = evaluate_pms_review(pms_review_demo_state.get_state())
    if not before.audit_complete:
        return _redirect("現在の工程では是正処置を登録できません。先に内部監査記録を完成させてください。")
    if not before.corrective_required:
        return _redirect("内部監査で不適合が確認されていないため、是正処置の登録は不要です。")

    pms_review_demo_state.record_corrective_action(
        finding_summary=finding_summary,
        immediate_action=immediate_action,
        root_cause=root_cause,
        corrective_action=corrective_action,
        implemented_on=implemented_on,
        effectiveness_result=effectiveness_result,
        effectiveness_checked_on=effectiveness_checked_on,
        approved_by=approved_by,
        approved_at=approved_at,
        evidence_name=evidence_name,
    )
    result = evaluate_pms_review(pms_review_demo_state.get_state())
    if not result.corrective_complete:
        return _redirect("是正処置記録を保存しました。有効性が確認できていないため、追加対応後に再評価してください。")
    return _redirect("是正処置記録を保存しました。有効性確認まで完了したため、次にマネジメントレビューへ進みます。")


@router.post("/management-review")
def save_management_review(
    review_date: str = Form(...),
    top_management_name: str = Form(...),
    input_summary: str = Form(...),
    decision_summary: str = Form(...),
    changes_needed: str = Form(...),
    improvement_actions: str = Form(""),
    evidence_name: str = Form(...),
) -> RedirectResponse:
    before = evaluate_pms_review(pms_review_demo_state.get_state())
    if not before.audit_complete:
        return _redirect("現在の工程ではマネジメントレビューを登録できません。先に内部監査記録を完成させてください。")
    if before.corrective_required and not before.corrective_complete:
        return _redirect("現在の工程ではマネジメントレビューを登録できません。先に必要な是正処置と有効性確認を完了してください。")

    pms_review_demo_state.record_management_review(
        review_date=review_date,
        top_management_name=top_management_name,
        input_summary=input_summary,
        decision_summary=decision_summary,
        changes_needed=changes_needed == "yes",
        improvement_actions=improvement_actions,
        evidence_name=evidence_name,
    )
    result = evaluate_pms_review(pms_review_demo_state.get_state())
    if result.complete:
        return _redirect("マネジメントレビュー記録を保存しました。PMS評価・改善の記録が整いました。")
    return _redirect("マネジメントレビュー記録を保存しました。未完了項目を確認してください。")
