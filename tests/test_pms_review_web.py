from fastapi.testclient import TestClient

from app import (
    access_control_demo_state,
    company_profile,
    demo_state,
    intake_demo_state,
    paper_demo_state,
    pms_review_demo_state,
    vendor_demo_state,
)
from app.dev_preset import load_pms_review_preset
from app.main import app

client = TestClient(app)


def _reset_all() -> None:
    company_profile.reset_state()
    intake_demo_state.reset_state()
    demo_state.reset_state()
    vendor_demo_state.reset_state()
    access_control_demo_state.reset_state()
    paper_demo_state.reset_state()
    pms_review_demo_state.reset_state()


def setup_function():
    _reset_all()


def teardown_function():
    _reset_all()


def _load_review_ready_state() -> None:
    load_pms_review_preset()


def test_pms_review_page_starts_with_audit_only():
    _load_review_ready_state()
    response = client.get("/pms-review")

    assert response.status_code == 200
    assert "PMS評価・改善の全体工程" in response.text
    assert "現在地：1. 内部監査" in response.text
    assert 'action="/pms-review/audit"' in response.text
    assert 'action="/pms-review/corrective-action"' not in response.text
    assert 'action="/pms-review/management-review"' not in response.text
    assert "客観性・公平性を確認した" in response.text
    assert "Pマーク構築・運用指針 JIS Q 15001:2023準拠 ver1.0" in response.text


def test_direct_post_cannot_bypass_audit_and_corrective_sequence():
    _load_review_ready_state()

    corrective_response = client.post(
        "/pms-review/corrective-action",
        data={
            "finding_summary": "先行登録テスト",
            "immediate_action": "修正",
            "root_cause": "原因",
            "corrective_action": "是正",
            "implemented_on": "2026-08-01",
            "effectiveness_result": "effective",
            "effectiveness_checked_on": "2026-08-02",
            "approved_by": "山田 太郎",
            "approved_at": "2026-08-02",
            "evidence_name": "是正処置記録",
        },
        follow_redirects=True,
    )
    assert "先に内部監査記録を完成させてください" in corrective_response.text
    assert pms_review_demo_state.get_state().corrective_action.finding_summary is None

    review_response = client.post(
        "/pms-review/management-review",
        data={
            "review_date": "2026-08-03",
            "top_management_name": "山田 太郎",
            "input_summary": "先行登録テスト",
            "decision_summary": "決定",
            "changes_needed": "no",
            "improvement_actions": "",
            "evidence_name": "マネジメントレビュー議事録",
        },
        follow_redirects=True,
    )
    assert "先に内部監査記録を完成させてください" in review_response.text
    assert pms_review_demo_state.get_state().management_review.review_date is None


def test_audit_without_findings_skips_corrective_form_and_opens_management_review():
    _load_review_ready_state()
    response = client.post(
        "/pms-review/audit",
        data={
            "audit_date": "2026-08-01",
            "purpose": "PMSの適合性・有効性確認",
            "criteria": "PMS規程・Pマーク構築運用指針",
            "scope": "全社PMS",
            "auditor_name": "佐藤 次郎",
            "auditor_independence_confirmed": "yes",
            "result_summary": "重大な問題なし",
            "nonconformity_count": "0",
            "report_date": "2026-08-02",
            "reported_to_top_management": "yes",
            "evidence_name": "内部監査報告書",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "現在地：3. マネジメントレビュー" in response.text
    assert "2. 不適合・是正処置</strong>　対象なし" in response.text
    assert 'action="/pms-review/corrective-action"' not in response.text
    assert 'action="/pms-review/management-review"' in response.text


def test_audit_with_findings_requires_corrective_action_and_ineffective_result_does_not_advance():
    _load_review_ready_state()
    client.post(
        "/pms-review/audit",
        data={
            "audit_date": "2026-08-01",
            "purpose": "PMSの適合性・有効性確認",
            "criteria": "PMS規程・Pマーク構築運用指針",
            "scope": "全社PMS",
            "auditor_name": "佐藤 次郎",
            "auditor_independence_confirmed": "yes",
            "result_summary": "承認漏れを1件確認",
            "nonconformity_count": "1",
            "report_date": "2026-08-02",
            "reported_to_top_management": "yes",
            "evidence_name": "内部監査報告書",
        },
    )

    response = client.get("/pms-review")
    assert "現在地：2. 不適合・是正処置" in response.text
    assert 'action="/pms-review/corrective-action"' in response.text
    assert 'action="/pms-review/management-review"' not in response.text

    response = client.post(
        "/pms-review/corrective-action",
        data={
            "finding_summary": "承認漏れ",
            "immediate_action": "未承認記録を承認",
            "root_cause": "確認手順が不明確",
            "corrective_action": "月次確認を追加",
            "implemented_on": "2026-08-03",
            "effectiveness_result": "ineffective",
            "effectiveness_checked_on": "2026-08-05",
            "approved_by": "山田 太郎",
            "approved_at": "2026-08-05",
            "evidence_name": "是正処置記録",
        },
        follow_redirects=True,
    )
    assert "現在地：2. 不適合・是正処置" in response.text
    assert "追加対応後に再評価" in response.text


def test_effective_corrective_action_then_management_review_completes_flow():
    _load_review_ready_state()
    client.post(
        "/pms-review/audit",
        data={
            "audit_date": "2026-08-01",
            "purpose": "PMSの適合性・有効性確認",
            "criteria": "PMS規程・Pマーク構築運用指針",
            "scope": "全社PMS",
            "auditor_name": "佐藤 次郎",
            "auditor_independence_confirmed": "yes",
            "result_summary": "承認漏れを1件確認",
            "nonconformity_count": "1",
            "report_date": "2026-08-02",
            "reported_to_top_management": "yes",
            "evidence_name": "内部監査報告書",
        },
    )
    client.post(
        "/pms-review/corrective-action",
        data={
            "finding_summary": "承認漏れ",
            "immediate_action": "未承認記録を承認",
            "root_cause": "確認手順が不明確",
            "corrective_action": "月次確認を追加",
            "implemented_on": "2026-08-03",
            "effectiveness_result": "effective",
            "effectiveness_checked_on": "2026-08-10",
            "approved_by": "山田 太郎",
            "approved_at": "2026-08-10",
            "evidence_name": "是正処置記録",
        },
    )
    response = client.get("/pms-review")
    assert "現在地：3. マネジメントレビュー" in response.text

    response = client.post(
        "/pms-review/management-review",
        data={
            "review_date": "2026-08-12",
            "top_management_name": "山田 太郎",
            "input_summary": "監査・是正・リスク・運用状況を確認",
            "decision_summary": "現行PMSを維持し改善を継続する",
            "changes_needed": "no",
            "improvement_actions": "",
            "evidence_name": "マネジメントレビュー議事録",
        },
        follow_redirects=True,
    )
    assert "現在地：全工程完了" in response.text
    assert "今やること　0件" in response.text
    assert "PMS評価・改善の記録が整いました" in response.text
