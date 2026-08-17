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


def test_annual_pms_starts_with_full_nine_step_forest_and_only_step1_form():
    load_annual_pms_preset()

    response = client.get("/annual-pms")

    assert response.status_code == 200
    assert "年間PMS運用計画" in response.text
    assert "年間サイクル進捗：0 / 9 工程 完了" in response.text
    assert "現在地：1. 年度運用計画・体制確認" in response.text
    assert "1. 年度運用計画・体制確認" in response.text
    assert "2. 個人情報台帳・リスク見直し" in response.text
    assert "7. 内部監査" in response.text
    assert "9. マネジメントレビュー・次年度計画" in response.text
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
