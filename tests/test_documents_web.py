import pytest
from fastapi.testclient import TestClient

from app import company_profile, demo_state, intake_demo_state, vendor_demo_state
from app.intake_schemas import QuestionnaireAnswers
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_all_state():
    """各テストの前後で全デモ状態を初期化し、テスト間の状態汚染を防ぐ。"""

    company_profile.reset_state()
    intake_demo_state.reset_state()
    demo_state.reset_state()
    vendor_demo_state.reset_state()
    yield
    company_profile.reset_state()
    intake_demo_state.reset_state()
    demo_state.reset_state()
    vendor_demo_state.reset_state()


def make_answers(**overrides):
    defaults = dict(
        has_employees=False,
        recruits_people=False,
        manages_customer_contacts=False,
        receives_inquiries=False,
        outsources_personal_data_processing=False,
        uses_external_cloud_services=False,
        stores_personal_data_on_paper=False,
        allows_remote_access=False,
    )
    defaults.update(overrides)
    return QuestionnaireAnswers(**defaults)


FULL_LEDGER_FORM = {
    "acquisition_method": "申込フォームからの入力",
    "storage_method": "社内システムに保存",
    "storage_location": "社内サーバー",
    "outsourced": "no",
    "third_party_provided": "no",
    "retention_period": "退職後5年",
    "disposal_method": "システムから削除",
    "responsible_role": "総務部長",
}


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


# --- 8. 文書表示ページが200 ---


def test_document_list_page_returns_200():
    response = client.get("/documents")

    assert response.status_code == 200
    assert "個人情報管理台帳" in response.text
    assert "個人情報保護教育手順" in response.text
    assert "委託先管理手順" in response.text


def test_document_detail_page_returns_200_for_each_document():
    for document_id in (
        "personal_information_ledger",
        "education_procedure",
        "vendor_management_procedure",
    ):
        response = client.get(f"/documents/{document_id}")
        assert response.status_code == 200


def test_document_detail_page_returns_404_for_unknown_id():
    response = client.get("/documents/unknown_document")

    assert response.status_code == 404


# --- 未生成・下書き・準備完了の表示 ---


def test_education_procedure_shows_not_applicable_before_adoption():
    response = client.get("/documents/education_procedure")

    assert "未生成" in response.text
    assert "採用されていません" in response.text or "候補として提示されていません" in response.text


def test_education_procedure_shows_ready_after_adoption():
    _submit_answers(has_employees=True)
    client.post("/setup/controls/education/adopt")

    response = client.get("/documents/education_procedure")

    assert "準備完了" in response.text
    assert "対象者" in response.text


def test_ledger_shows_draft_with_missing_fields_before_ledger_filled():
    _submit_answers(has_employees=True)
    target = intake_demo_state.get_state().candidates[0]
    client.post(f"/setup/candidates/{target.id}/confirm")

    response = client.get("/documents/personal_information_ledger")

    assert "下書き" in response.text
    assert "不足" in response.text
    assert "従業員情報" in response.text


def test_ledger_shows_ready_after_ledger_filled():
    _submit_answers(has_employees=True)
    target = intake_demo_state.get_state().candidates[0]
    client.post(f"/setup/candidates/{target.id}/confirm")
    client.post(f"/setup/candidates/{target.id}/ledger", data=FULL_LEDGER_FORM)

    response = client.get("/documents/personal_information_ledger")

    assert "準備完了" in response.text
    assert "社内サーバー" in response.text


# --- 7. 元データ変更後にプレビュー内容も変化する（Web経由） ---


def test_ledger_preview_reflects_source_data_change():
    _submit_answers(has_employees=True)
    target = intake_demo_state.get_state().candidates[0]
    client.post(f"/setup/candidates/{target.id}/confirm")
    client.post(f"/setup/candidates/{target.id}/ledger", data=FULL_LEDGER_FORM)

    before = client.get("/documents/personal_information_ledger")
    assert "社内サーバー" in before.text

    updated_form = dict(FULL_LEDGER_FORM)
    updated_form["storage_location"] = "クラウドストレージ"
    client.post(f"/setup/candidates/{target.id}/ledger", data=updated_form)

    after = client.get("/documents/personal_information_ledger")
    assert "クラウドストレージ" in after.text
    assert "社内サーバー" not in after.text


# --- 6. related_control_idsの表示（画面上での関連管理策表示） ---


def test_document_detail_shows_related_control_name():
    _submit_answers(has_employees=True)
    client.post("/setup/controls/education/adopt")

    response = client.get("/documents/education_procedure")

    assert "個人情報保護教育" in response.text


# --- トップページ・setupからの導線 ---


def test_top_page_links_to_setup_before_personal_information_is_confirmed():
    response = client.get("/")

    assert "/documents" not in response.text
    assert "初期設定待ち" in response.text
    assert "/setup" in response.text


def test_top_page_links_to_documents_after_personal_information_is_confirmed():
    _submit_answers(has_employees=True)
    target = intake_demo_state.get_state().candidates[0]
    client.post(f"/setup/candidates/{target.id}/confirm")

    response = client.get("/")

    assert "/documents" in response.text
    assert "文書を確認" in response.text


def test_setup_hides_documents_link_until_management_decisions_are_complete():
    response = client.get("/setup")

    assert "/documents" not in response.text
    assert "STEP5の管理策判断を完了すると、運用画面へ進めるようになります。" in response.text


# --- 9. 既存機能を壊さない ---


def test_existing_pages_still_return_200():
    assert client.get("/").status_code == 200
    assert client.get("/setup").status_code == 200
    assert client.get("/education").status_code == 200
    assert client.get("/vendors").status_code == 200
