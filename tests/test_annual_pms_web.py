from fastapi.testclient import TestClient

from app import (
    access_control_demo_state,
    annual_cycle_demo_state,
    application_prep_demo_state,
    company_profile,
    demo_state,
    intake_demo_state,
    paper_demo_state,
    pms_review_demo_state,
    vendor_demo_state,
)
from app.dev_preset import load_annual_pms_preset
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
    annual_cycle_demo_state.reset_state()


def setup_function():
    _reset_all()


def teardown_function():
    _reset_all()


ANNUAL_PLAN_FORM = {
    "fiscal_year": "2026",
    "planned_on": "2026-04-01",
    "coordinator_name": "山田 花子",
    "privacy_manager_name": "鈴木 花子",
    "audit_manager_name": "佐藤 次郎",
    "top_management_name": "山田 太郎",
    "objectives": "PMSを有効に運用する",
    "schedule_summary": "年次見直し、各管理策運用、内部監査、マネジメントレビューを実施する",
    "approved_by": "山田 太郎",
    "approved_at": "2026-04-01",
    "evidence_name": "年間PMS運用計画書",
}

NO_CHANGE_REVIEW_FORM = {
    "reviewed_on": "2026-04-05",
    "reviewed_by": "山田 花子",
    "review_basis": "業務、組織、システム、委託先、台帳、リスク、管理策を確認",
    "business_change_result": "no_change",
    "personal_information_result": "no_change",
    "risk_result": "no_change",
    "control_result": "no_change",
    "change_action_summary": "",
    "change_action_completed_on": "",
    "approved_by": "鈴木 花子",
    "approved_at": "2026-04-05",
    "evidence_name": "個人情報・リスク年次見直し記録",
}


def _complete_annual_start() -> None:
    client.post("/annual-pms/annual-plan", data=ANNUAL_PLAN_FORM)
    client.post("/annual-pms/inventory-risk-review", data=NO_CHANGE_REVIEW_FORM)


def test_annual_pms_starts_with_full_nine_step_forest_and_only_step1_form():
    load_annual_pms_preset()

    response = client.get("/annual-pms")

    assert response.status_code == 200
    assert "年間PMS運用計画" in response.text
    assert "年間サイクル進捗：0 / 9 工程 完了" in response.text
    assert "現在地：1. 年度運用計画・体制確認" in response.text
    assert "1. 年度運用計画・体制確認" in response.text
    assert "個人情報台帳・リスク見直し" in response.text
    assert "内部監査" in response.text
    assert "マネジメントレビュー・次年度計画" in response.text
    assert 'action="/annual-pms/annual-plan"' in response.text
    assert 'action="/annual-pms/inventory-risk-review"' not in response.text
    assert "山田 花子" in response.text
    assert "鈴木 花子" in response.text
    assert "佐藤 次郎" in response.text


def test_annual_review_cannot_bypass_annual_plan():
    load_annual_pms_preset()

    response = client.post(
        "/annual-pms/inventory-risk-review",
        data=NO_CHANGE_REVIEW_FORM,
        follow_redirects=True,
    )

    assert "先に対象年度のPMS運用計画を完成させてください" in response.text
    assert annual_cycle_demo_state.get_state().inventory_risk_review.reviewed_on is None


def test_annual_plan_then_no_change_review_moves_current_location_to_education():
    load_annual_pms_preset()

    response = client.post(
        "/annual-pms/annual-plan",
        data=ANNUAL_PLAN_FORM,
        follow_redirects=True,
    )
    assert "年間サイクル進捗：1 / 9 工程 完了" in response.text
    assert "現在地：2. 個人情報台帳・リスク見直し" in response.text
    assert 'action="/annual-pms/inventory-risk-review"' in response.text
    assert 'action="/annual-pms/annual-plan"' not in response.text
    assert "確認済み個人情報：<strong>" in response.text
    assert "確認済みリスク：<strong>" in response.text
    assert "採用済み管理策：<strong>4件" in response.text
    assert response.text.count("選択してください") >= 4

    response = client.post(
        "/annual-pms/inventory-risk-review",
        data=NO_CHANGE_REVIEW_FORM,
        follow_redirects=True,
    )
    assert "年間サイクル進捗：2 / 9 工程 完了" in response.text
    assert "現在地：3. 教育" in response.text
    assert "年度開始の2工程が完了しました" in response.text
    assert 'href="/education"' in response.text

    saved = annual_cycle_demo_state.get_state().inventory_risk_review
    assert saved.personal_information_count is not None
    assert saved.risk_count is not None
    assert saved.adopted_control_count == 4


def test_changed_review_does_not_complete_without_source_update_record():
    load_annual_pms_preset()
    client.post("/annual-pms/annual-plan", data=ANNUAL_PLAN_FORM)

    changed = dict(NO_CHANGE_REVIEW_FORM)
    changed["risk_result"] = "changed"
    response = client.post(
        "/annual-pms/inventory-risk-review",
        data=changed,
        follow_redirects=True,
    )

    assert "正本へ反映した内容と変更反映完了日" in response.text
    assert "現在地：2. 個人情報台帳・リスク見直し" in response.text
    assert annual_cycle_demo_state.get_state().inventory_risk_review.reviewed_on is None

    changed["change_action_summary"] = "リスク評価を見直し、関連する管理策の内容を更新した"
    changed["change_action_completed_on"] = "2026-04-06"
    response = client.post(
        "/annual-pms/inventory-risk-review",
        data=changed,
        follow_redirects=True,
    )
    assert "現在地：3. 教育" in response.text


def test_full_annual_cycle_reaches_nine_of_nine_without_fake_completion_buttons():
    load_annual_pms_preset()
    _complete_annual_start()

    demo_state.register_material_evidence()
    demo_state.complete_all_trainings()
    demo_state.register_missing_comprehension()
    demo_state.approve_plan()

    vendor_demo_state.complete_missing_initial_assessments()
    vendor_demo_state.confirm_missing_contracts()
    vendor_demo_state.complete_missing_periodic_assessments()

    access_control_demo_state.complete_missing_account_reviews()
    access_control_demo_state.remove_unnecessary_accounts()
    access_control_demo_state.complete_review_cycle()
    access_control_demo_state.approve_review_cycle()

    paper_demo_state.confirm_storage_lock()
    paper_demo_state.define_take_out_rule()
    paper_demo_state.confirm_disposal()
    paper_demo_state.approve_status()

    pms_review_demo_state.record_internal_audit(
        audit_date="2026-08-01",
        purpose="PMSの適合性・有効性確認",
        criteria="PMS規程・Pマーク構築運用指針",
        scope="全社PMS",
        auditor_name="佐藤 次郎",
        auditor_independence_confirmed=True,
        result_summary="重大な不適合なし",
        nonconformity_count=0,
        report_date="2026-08-02",
        reported_to_top_management=True,
        evidence_name="内部監査報告書",
    )
    pms_review_demo_state.record_management_review(
        review_date="2026-08-05",
        top_management_name="山田 太郎",
        input_summary="年度見直し、各管理策運用、内部監査結果を確認",
        decision_summary="現行PMSを維持し継続的に改善する",
        changes_needed=False,
        improvement_actions="",
        evidence_name="マネジメントレビュー議事録",
    )

    response = client.get("/annual-pms")

    assert response.status_code == 200
    assert "年間サイクル進捗：9 / 9 工程 完了" in response.text
    assert "現在地：年間PMS運用サイクル完了" in response.text
    assert "年度開始の2工程が完了しました" not in response.text
