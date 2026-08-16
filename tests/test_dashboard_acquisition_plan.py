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
from app.dev_preset import load_operational_review_preset, load_pms_review_preset
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


def test_acquisition_plan_is_the_top_level_forest_before_todo_details():
    _reset_all()
    response = client.get("/")
    _reset_all()

    assert response.status_code == 200
    assert "Pマーク取得の全体計画" in response.text
    assert "実装範囲進捗：0 / 5 工程 完了" in response.text
    assert "現在地：1. 初期設定" in response.text
    assert "内部監査・是正" in response.text
    assert "マネジメントレビュー" in response.text
    assert "申請準備" in response.text
    assert "後続工程" in response.text

    plan_index = response.text.index("Pマーク取得の全体計画")
    todo_index = response.text.index("今やること")
    preparation_index = response.text.index("Pマーク準備状況")
    assert plan_index < todo_index < preparation_index


def test_operational_review_preset_places_current_location_at_operations_and_groups_todos():
    _reset_all()
    load_operational_review_preset()
    response = client.get("/")
    _reset_all()

    assert response.status_code == 200
    assert "実装範囲進捗：2 / 5 工程 完了" in response.text
    assert "現在地：3. 採用管理策の運用" in response.text
    assert "今やること　4件" in response.text
    assert response.text.count("教育管理：") == 1
    assert response.text.count("委託先管理：") == 1
    assert response.text.count("アクセス権限管理：") == 1
    assert response.text.count("紙媒体管理：") == 1


def test_pms_review_preset_moves_current_location_to_internal_audit():
    _reset_all()
    load_pms_review_preset()
    response = client.get("/")
    _reset_all()

    assert response.status_code == 200
    assert "実装範囲進捗：3 / 5 工程 完了" in response.text
    assert "現在地：4. 内部監査・是正" in response.text
    assert "PMS評価・改善：" in response.text
    assert 'href="/pms-review"' in response.text


def test_acquisition_plan_moves_to_management_review_after_audit_without_findings():
    _reset_all()
    load_pms_review_preset()
    pms_review_demo_state.record_internal_audit(
        audit_date="2026-08-01",
        purpose="PMSの適合性と有効性を確認",
        criteria="PMS規程・Pマーク構築運用指針",
        scope="全社PMS",
        auditor_name="佐藤 次郎",
        auditor_independence_confirmed=True,
        result_summary="重大な問題なし",
        nonconformity_count=0,
        report_date="2026-08-02",
        reported_to_top_management=True,
        evidence_name="内部監査報告書",
    )

    response = client.get("/")
    _reset_all()

    assert "実装範囲進捗：4 / 5 工程 完了" in response.text
    assert "現在地：5. マネジメントレビュー" in response.text


def test_acquisition_plan_marks_current_scope_complete_after_management_review():
    _reset_all()
    load_pms_review_preset()
    pms_review_demo_state.record_internal_audit(
        audit_date="2026-08-01",
        purpose="PMSの適合性と有効性を確認",
        criteria="PMS規程・Pマーク構築運用指針",
        scope="全社PMS",
        auditor_name="佐藤 次郎",
        auditor_independence_confirmed=True,
        result_summary="重大な問題なし",
        nonconformity_count=0,
        report_date="2026-08-02",
        reported_to_top_management=True,
        evidence_name="内部監査報告書",
    )
    pms_review_demo_state.record_management_review(
        review_date="2026-08-05",
        top_management_name="山田 太郎",
        input_summary="監査・リスク・運用状況を確認",
        decision_summary="現行PMSを維持し継続的改善を行う",
        changes_needed=False,
        improvement_actions="",
        evidence_name="マネジメントレビュー議事録",
    )

    response = client.get("/")
    _reset_all()

    assert response.status_code == 200
    assert "実装範囲進捗：5 / 5 工程 完了" in response.text
    assert "現在地：MVP実装範囲完了（次の後続工程：6. 申請準備）" in response.text
