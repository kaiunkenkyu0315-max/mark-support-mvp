from app import pms_review_demo_state
from app.pms_review import evaluate_pms_review


def setup_function():
    pms_review_demo_state.reset_state()


def teardown_function():
    pms_review_demo_state.reset_state()


def _record_audit(nonconformity_count: int) -> None:
    pms_review_demo_state.record_internal_audit(
        audit_date="2026-08-01",
        purpose="PMSの適合性・有効性確認",
        criteria="PMS規程・Pマーク構築運用指針",
        scope="全社PMS",
        auditor_name="監査責任者",
        auditor_independence_confirmed=True,
        result_summary="監査を実施",
        nonconformity_count=nonconformity_count,
        report_date="2026-08-02",
        reported_to_top_management=True,
        evidence_name="内部監査報告書",
    )


def test_initial_state_requires_internal_audit():
    result = evaluate_pms_review(pms_review_demo_state.get_state())

    assert result.audit_complete is False
    assert result.complete is False
    assert any(issue.rule_id == "AUD-001" for issue in result.issues)


def test_no_audit_findings_skip_corrective_action():
    _record_audit(0)
    result = evaluate_pms_review(pms_review_demo_state.get_state())

    assert result.audit_complete is True
    assert result.corrective_required is False
    assert result.corrective_complete is True
    assert result.management_review_complete is False


def test_audit_findings_require_effective_corrective_action():
    _record_audit(1)
    result = evaluate_pms_review(pms_review_demo_state.get_state())
    assert result.corrective_required is True
    assert result.corrective_complete is False

    pms_review_demo_state.record_corrective_action(
        finding_summary="監査記録の承認漏れ",
        immediate_action="未承認記録を承認",
        root_cause="承認確認手順が不明確だった",
        corrective_action="月次確認チェックを追加",
        implemented_on="2026-08-03",
        effectiveness_result="ineffective",
        effectiveness_checked_on="2026-08-05",
        approved_by="代表者",
        approved_at="2026-08-05",
        evidence_name="是正処置記録",
    )
    result = evaluate_pms_review(pms_review_demo_state.get_state())
    assert result.corrective_complete is False
    assert any("有効性" in issue.message for issue in result.issues if issue.rule_id == "CAR-001")

    pms_review_demo_state.record_corrective_action(
        finding_summary="監査記録の承認漏れ",
        immediate_action="未承認記録を承認",
        root_cause="承認確認手順が不明確だった",
        corrective_action="月次確認チェックを追加",
        implemented_on="2026-08-03",
        effectiveness_result="effective",
        effectiveness_checked_on="2026-08-10",
        approved_by="代表者",
        approved_at="2026-08-10",
        evidence_name="是正処置記録",
    )
    result = evaluate_pms_review(pms_review_demo_state.get_state())
    assert result.corrective_complete is True


def test_management_review_requires_improvement_action_when_change_is_needed():
    _record_audit(0)
    pms_review_demo_state.record_management_review(
        review_date="2026-08-05",
        top_management_name="代表者",
        input_summary="監査・リスク・運用状況を確認",
        decision_summary="PMS変更が必要",
        changes_needed=True,
        improvement_actions="",
        evidence_name="マネジメントレビュー議事録",
    )
    result = evaluate_pms_review(pms_review_demo_state.get_state())
    assert result.management_review_complete is False

    pms_review_demo_state.record_management_review(
        review_date="2026-08-05",
        top_management_name="代表者",
        input_summary="監査・リスク・運用状況を確認",
        decision_summary="PMS変更が必要",
        changes_needed=True,
        improvement_actions="教育手順を改定し次年度計画へ反映する",
        evidence_name="マネジメントレビュー議事録",
    )
    result = evaluate_pms_review(pms_review_demo_state.get_state())
    assert result.management_review_complete is True
    assert result.complete is True
