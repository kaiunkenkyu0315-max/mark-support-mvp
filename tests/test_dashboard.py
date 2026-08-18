"""管理者ダッシュボード（トップページ）と、状態表示の統一（app.control_status）を
検証するテスト。

「未採用」の管理策を「要対応」と表示しないこと、管理策がadoptedになって
初めて運用評価（要対応／適合）を表示すること、ダッシュボードの集計が
既存の評価ロジック・採用可否の正本（setup側のControlSuggestion.status）と
整合していることを確認する。
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import (
    access_control_demo_state,
    demo_state,
    intake_demo_state,
    paper_demo_state,
    vendor_demo_state,
)
from app.access_control import evaluate_access_control
from app.dashboard import build_dashboard_data
from app.education import evaluate_training
from app.intake_schemas import ControlDecisionStatus, ControlSuggestion, SetupStatus
from app.main import app
from app.paper import evaluate_paper_management
from app.vendors import evaluate_vendors

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_all_state():
    intake_demo_state.reset_state()
    demo_state.reset_state()
    vendor_demo_state.reset_state()
    access_control_demo_state.reset_state()
    paper_demo_state.reset_state()
    yield
    intake_demo_state.reset_state()
    demo_state.reset_state()
    vendor_demo_state.reset_state()
    access_control_demo_state.reset_state()
    paper_demo_state.reset_state()


def _submit_answers(**overrides):
    form = {
        "has_employees": "no",
        "recruits_people": "no",
        "manages_customer_contacts": "no",
        "receives_inquiries": "no",
        "outsources_personal_data_processing": "no",
        "uses_external_cloud_services": "no",
        "stores_personal_data_on_paper": "no",
        "allows_remote_access": "no",
    }
    for field, value in overrides.items():
        form[field] = "yes" if value else "no"
    client.post("/setup/answers", data=form)


# --- 1. 初期設定未完了時、未採用管理策を要対応表示しない ---


def test_dashboard_does_not_show_needs_action_before_any_setup():
    response = client.get("/")

    assert response.status_code == 200
    assert "要対応" not in response.text


# --- 1b. 初期設定未着手時、運用状況の各エリアは「初期設定待ち」（「未採用」ではない） ---


def test_dashboard_shows_setup_pending_for_operational_areas_before_setup_starts():
    response = client.get("/")

    assert ">初期設定待ち<" in response.text
    assert ">適合<" not in response.text
    assert ">要対応<" not in response.text


# --- 1c. 初期設定未着手時、文書カードは対応可能な「情報不足」を示さない ---


def test_dashboard_document_card_does_not_show_actionable_shortage_before_setup_starts():
    response = client.get("/")

    assert "情報不足" not in response.text


# --- 1d. 初期設定未着手時、「次にやること」は初期設定の1件だけを主表示する ---


def test_dashboard_todo_list_has_only_setup_item_before_setup_starts():
    response = client.get("/")

    assert "<h2>次にやること</h2>" in response.text
    assert response.text.count('class="primary-action"') == 1
    assert "そのほかの対応予定" not in response.text
    assert "の入力が不足しています" not in response.text
    assert "初期設定" in response.text


# --- 2. suggested管理策 → 要確認または採用判断待ち ---


def test_dashboard_shows_pending_decision_for_suggested_control():
    _submit_answers(has_employees=True)

    response = client.get("/")

    assert "教育管理" in response.text
    assert "採用判断待ち" in response.text


# --- 3. not_applicable → 非適用表示 ---


def test_dashboard_shows_not_applicable_for_non_applicable_control():
    _submit_answers(has_employees=True)
    client.post(
        "/setup/controls/education/not-applicable",
        data={"reason": "対象業務がないため"},
    )

    response = client.get("/")

    assert "非適用" in response.text


# --- 4. adoptedかつ不足あり → 要対応 ---


def test_dashboard_shows_needs_action_for_adopted_control_with_issues():
    _submit_answers(has_employees=True)
    client.post("/setup/controls/education/adopt")

    response = client.get("/")

    assert "要対応" in response.text


# --- 5. adoptedかつ不足なし → 適合 ---


def test_dashboard_shows_compliant_for_adopted_control_without_issues():
    _submit_answers(has_employees=True)
    client.post("/setup/controls/education/adopt")
    client.post("/education/actions/complete-trainings")
    client.post("/education/actions/register-comprehension")
    client.post("/education/actions/register-material-evidence")
    client.post("/education/actions/approve")

    response = client.get("/")

    assert "適合" in response.text
    assert "要対応" not in response.text


# --- 6. ダッシュボードの各状態が既存評価ロジックと整合する ---


def test_dashboard_data_matches_underlying_evaluation_results():
    _submit_answers(has_employees=True, outsources_personal_data_processing=True)
    client.post("/setup/controls/education/adopt")

    intake_state = intake_demo_state.get_state()
    education_state = demo_state.get_state()
    vendor_state = vendor_demo_state.get_state()
    access_control_state = access_control_demo_state.get_state()
    paper_state = paper_demo_state.get_state()

    education_result = evaluate_training(
        education_state.employees, education_state.control, education_state.plan, education_state.records
    )
    vendor_result = evaluate_vendors(
        vendor_state.vendors, vendor_state.control, vendor_state.assessments, vendor_state.contracts
    )
    access_control_result = evaluate_access_control(
        access_control_state.accounts, access_control_state.control, access_control_state.cycle
    )
    paper_result = evaluate_paper_management(paper_state.control, paper_state.status)

    data = build_dashboard_data(
        setup_status=intake_demo_state.get_setup_status(intake_state),
        candidates=intake_state.candidates,
        risks=intake_state.risks,
        control_suggestions=intake_state.control_suggestions,
        documents=[],
        education_result=education_result,
        vendor_result=vendor_result,
        access_control_result=access_control_result,
        paper_result=paper_result,
    )

    education_area = next(a for a in data.operational_areas if a.control_id == "education")
    assert education_area.adopted is True
    assert education_area.label == "要対応"
    assert len(education_result.issues) > 0

    vendor_area = next(a for a in data.operational_areas if a.control_id == "vendor_management")
    assert vendor_area.adopted is False
    assert vendor_area.label == "採用判断待ち"


# --- 7. 初期設定完了後の要対応todoは採用済み管理策のみから集計される ---


def test_dashboard_todo_items_only_come_from_adopted_controls_after_setup_complete():
    suggested_but_not_adopted = ControlSuggestion(
        control_id="vendor_management",
        name="委託先管理",
        reason="テスト用",
        status=ControlDecisionStatus.SUGGESTED,
    )
    adopted = ControlSuggestion(
        control_id="education",
        name="個人情報保護教育",
        reason="テスト用",
        status=ControlDecisionStatus.ADOPTED,
    )

    education_state = demo_state.get_state()
    education_result = evaluate_training(
        education_state.employees, education_state.control, education_state.plan, education_state.records
    )
    vendor_state = vendor_demo_state.get_state()
    vendor_result = evaluate_vendors(
        vendor_state.vendors, vendor_state.control, vendor_state.assessments, vendor_state.contracts
    )
    access_control_state = access_control_demo_state.get_state()
    access_control_result = evaluate_access_control(
        access_control_state.accounts, access_control_state.control, access_control_state.cycle
    )
    paper_state = paper_demo_state.get_state()
    paper_result = evaluate_paper_management(paper_state.control, paper_state.status)

    assert vendor_result.issues, "前提：委託先管理には初期状態で不足がある"

    data = build_dashboard_data(
        setup_status=SetupStatus.COMPLETE,
        candidates=[],
        risks=[],
        control_suggestions=[suggested_but_not_adopted, adopted],
        documents=[],
        education_result=education_result,
        vendor_result=vendor_result,
        access_control_result=access_control_result,
        paper_result=paper_result,
    )

    todo_areas = {item.area for item in data.todo_items}
    assert "委託先管理" not in todo_areas
    assert "教育管理" in todo_areas
    assert len([item for item in data.todo_items if item.area == "教育管理"]) == len(
        education_result.issues
    )


# --- 8. 個人情報管理画面に既存台帳の管理方法が表示される ---


FULL_LEDGER_FORM = {
    "acquisition_method": "本人提出",
    "storage_method": "クラウド＋紙",
    "storage_location": "総務部キャビネット",
    "outsourced": "yes",
    "third_party_provided": "no",
    "retention_period": "退職後5年",
    "disposal_method": "電子削除＋紙廃棄",
    "responsible_role": "総務部長",
}


def test_setup_page_shows_ledger_management_method_and_related_controls():
    _submit_answers(has_employees=True, outsources_personal_data_processing=True)
    target = next(
        c for c in intake_demo_state.get_state().candidates if c.source_key == "has_employees"
    )
    client.post(f"/setup/candidates/{target.id}/confirm")
    client.post(f"/setup/candidates/{target.id}/ledger", data=FULL_LEDGER_FORM)

    response = client.get("/setup")

    assert "管理方法：" in response.text
    assert "取得方法：本人提出" in response.text
    assert "保管形態：クラウド＋紙" in response.text
    assert "関連する管理策：" in response.text
    assert "個人情報保護教育" in response.text


# --- 9. 初期設定中は文書不足todoを割り込ませず、現在工程1件だけを主表示する ---


def test_dashboard_hides_document_shortage_todo_while_setup_is_in_progress():
    _submit_answers(has_employees=True)
    target = intake_demo_state.get_state().candidates[0]
    client.post(f"/setup/candidates/{target.id}/confirm")

    response = client.get("/")

    assert "<h2>次にやること</h2>" in response.text
    assert response.text.count('class="primary-action"') == 1
    assert "個人情報台帳" in response.text
    assert "文書：個人情報管理台帳の入力が不足しています。" not in response.text


# --- 10. 利用者向け画面に不必要な「setup」表記が残っていない ---


def test_no_developer_facing_setup_wording_on_user_screens():
    _submit_answers(has_employees=True)
    client.post("/setup/controls/education/adopt")

    for path in ("/", "/setup", "/education", "/vendors", "/access-control", "/paper", "/documents"):
        response = client.get(path)
        assert "setupで" not in response.text, f"{path} still shows developer-facing 'setup' wording"
        assert "セットアップ" not in response.text, f"{path} still shows katakana 'セットアップ'"


# --- 11. 既存機能が従来どおり動作する（スモークテスト） ---


def test_existing_pages_still_work_end_to_end():
    assert client.get("/").status_code == 200
    assert client.get("/setup").status_code == 200
    assert client.get("/education").status_code == 200
    assert client.get("/vendors").status_code == 200
    assert client.get("/access-control").status_code == 200
    assert client.get("/paper").status_code == 200
    assert client.get("/documents").status_code == 200
