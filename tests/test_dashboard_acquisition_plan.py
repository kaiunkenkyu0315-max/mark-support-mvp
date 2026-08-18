from fastapi.testclient import TestClient

from app import (
    access_control_demo_state,
    application_prep_demo_state,
    company_profile,
    demo_state,
    intake_demo_state,
    paper_demo_state,
    pms_review_demo_state,
    vendor_demo_state,
)
from app.dev_preset import (
    load_application_prep_preset,
    load_operational_review_preset,
    load_pms_review_preset,
)
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
    application_prep_demo_state.reset_state()


def test_acquisition_plan_is_the_top_level_forest_before_next_action_and_details():
    _reset_all()
    response = client.get("/")
    _reset_all()

    assert response.status_code == 200
    assert "Pマーク取得の全体計画" in response.text
    assert "実装範囲進捗：0 / 6 工程 完了" in response.text
    assert "現在地：1. 初期設定" in response.text
    assert "内部監査・是正" in response.text
    assert "マネジメントレビュー" in response.text
    assert "申請準備" in response.text
    assert "申請・審査" in response.text
    assert "外部工程" in response.text

    plan_index = response.text.index('<h2 style="margin-top:0;">Pマーク取得の全体計画</h2>')
    next_action_index = response.text.index("<h2>次にやること</h2>")
    preparation_index = response.text.index("Pマーク準備状況を詳しく見る")
    assert plan_index < next_action_index < preparation_index


def test_operational_review_preset_places_current_location_at_operations_and_keeps_one_primary_action():
    _reset_all()
    load_operational_review_preset()
    response = client.get("/")
    _reset_all()

    assert response.status_code == 200
    assert "実装範囲進捗：2 / 6 工程 完了" in response.text
    assert "現在地：3. 採用管理策の運用" in response.text
    assert "<h2>次にやること</h2>" in response.text
    assert response.text.count('class="primary-action"') == 1
    assert "<h3>教育管理</h3>" in response.text
    assert "そのほかの対応予定　3件" in response.text
    assert "委託先管理" in response.text
    assert "アクセス権限管理" in response.text
    assert "紙媒体管理" in response.text


def test_pms_review_preset_moves_current_location_to_internal_audit():
    _reset_all()
    load_pms_review_preset()
    response = client.get("/")
    _reset_all()

    assert response.status_code == 200
    assert "実装範囲進捗：3 / 6 工程 完了" in response.text
    assert "現在地：4. 内部監査・是正" in response.text
    assert "<h3>PMS評価・改善</h3>" in response.text
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

    assert "実装範囲進捗：4 / 6 工程 完了" in response.text
    assert "現在地：5. マネジメントレビュー" in response.text


def test_acquisition_plan_moves_to_application_prep_after_management_review():
    _reset_all()
    load_application_prep_preset()

    response = client.get("/")
    _reset_all()

    assert response.status_code == 200
    assert "実装範囲進捗：5 / 6 工程 完了" in response.text
    assert "現在地：6. 申請準備" in response.text
    assert "<h3>申請準備</h3>" in response.text
    assert 'href="/application-prep"' in response.text


def test_acquisition_plan_marks_application_prep_complete_but_keeps_external_review_separate():
    _reset_all()
    load_application_prep_preset()
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
        final_reviewed_by="山田 花子",
        final_reviewed_at="2026-08-10",
        submission_ready_confirmed=True,
    )

    response = client.get("/")
    _reset_all()

    assert response.status_code == 200
    assert "実装範囲進捗：6 / 6 工程 完了" in response.text
    assert "現在地：MVP実装範囲完了（次の外部工程：7. 申請・審査）" in response.text
    assert "外部工程" in response.text
    assert "Pマーク取得完了" not in response.text
