"""管理策の採用状態（adopted / not_applicable）の正本一元化を検証するテスト。

「管理策を採用したかどうか」の正式な判断は setup 側の ControlSuggestion を
正とする。education・vendors・documentsのいずれも、この正本を参照するだけで、
独自の採用判断を別途持たないことを確認する。
"""

import pytest
from fastapi.testclient import TestClient

from app import demo_state, intake_demo_state, vendor_demo_state
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_all_state():
    intake_demo_state.reset_state()
    demo_state.reset_state()
    vendor_demo_state.reset_state()
    yield
    intake_demo_state.reset_state()
    demo_state.reset_state()
    vendor_demo_state.reset_state()


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


# --- 1. education adopted → 教育文書生成 ---


def test_education_adopted_generates_education_document():
    _submit_answers(has_employees=True)
    client.post("/setup/controls/education/adopt")

    response = client.get("/documents/education_procedure")

    assert response.status_code == 200
    assert "準備完了" in response.text
    assert "未生成" not in response.text


# --- 2. education not_applicable → 教育文書を正式生成しない ---


def test_education_not_applicable_does_not_generate_education_document():
    _submit_answers(has_employees=True)
    client.post(
        "/setup/controls/education/not-applicable",
        data={"reason": "対象業務がないため"},
    )

    response = client.get("/documents/education_procedure")

    assert "未生成" in response.text
    assert "対象業務がないため" in response.text
    assert "準備完了" not in response.text


# --- 3. vendor adopted → 委託先管理文書生成 ---


def test_vendor_adopted_generates_vendor_document():
    _submit_answers(outsources_personal_data_processing=True)
    client.post("/setup/controls/vendor_management/adopt")

    response = client.get("/documents/vendor_management_procedure")

    assert response.status_code == 200
    assert "準備完了" in response.text
    assert "未生成" not in response.text


# --- 4. vendor not_applicable → 委託先管理文書を正式生成しない ---


def test_vendor_not_applicable_does_not_generate_vendor_document():
    _submit_answers(outsources_personal_data_processing=True)
    client.post(
        "/setup/controls/vendor_management/not-applicable",
        data={"reason": "委託を廃止したため"},
    )

    response = client.get("/documents/vendor_management_procedure")

    assert "未生成" in response.text
    assert "委託を廃止したため" in response.text
    assert "準備完了" not in response.text


# --- 5. setupの採用判断変更後、documentsへ即反映 ---


def test_documents_reflect_setup_adoption_change_immediately():
    _submit_answers(has_employees=True, outsources_personal_data_processing=True)
    client.post("/setup/controls/education/adopt")
    client.post("/setup/controls/vendor_management/adopt")

    ready_response = client.get("/documents")
    assert ready_response.text.count("準備完了") >= 2

    # setupで教育管理を非適用へ変更する。
    client.post(
        "/setup/controls/education/not-applicable",
        data={"reason": "方針変更のため"},
    )

    updated_response = client.get("/documents/education_procedure")
    assert "未生成" in updated_response.text
    assert "方針変更のため" in updated_response.text

    # 委託先管理は採用済みのまま、影響を受けない。
    vendor_response = client.get("/documents/vendor_management_procedure")
    assert "準備完了" in vendor_response.text


# --- 6. education/vendors側に古い状態があっても正式判断と矛盾した表示にならない ---


def test_education_page_does_not_contradict_setup_not_applicable_decision():
    _submit_answers(has_employees=True)
    client.post(
        "/setup/controls/education/not-applicable",
        data={"reason": "対象業務がないため"},
    )

    response = client.get("/education")

    assert "非適用" in response.text
    assert "採用済み" not in response.text
    assert "現在、この管理策は運用対象ではありません。" in response.text


def test_education_page_shows_adopted_when_setup_says_adopted():
    _submit_answers(has_employees=True)
    client.post("/setup/controls/education/adopt")

    response = client.get("/education")

    assert "採用済み" in response.text
    assert "非適用" not in response.text


def test_vendor_page_does_not_contradict_setup_not_applicable_decision():
    _submit_answers(outsources_personal_data_processing=True)
    client.post(
        "/setup/controls/vendor_management/not-applicable",
        data={"reason": "委託を廃止したため"},
    )

    response = client.get("/vendors")

    assert "非適用" in response.text
    assert "採用済み" not in response.text
    assert "現在、この管理策は運用対象ではありません。" in response.text


def test_vendor_page_shows_adopted_when_setup_says_adopted():
    _submit_answers(outsources_personal_data_processing=True)
    client.post("/setup/controls/vendor_management/adopt")

    response = client.get("/vendors")

    assert "採用済み" in response.text
    assert "非適用" not in response.text


def test_education_and_documents_pages_agree_when_never_answered_in_setup():
    """初期設定で未提示の管理策は、運用対象にせず文書も未生成とする。"""

    education_response = client.get("/education")
    assert "未提示" in education_response.text
    assert "現在、この管理策は運用対象ではありません。" in education_response.text

    document_response = client.get("/documents/education_procedure")
    assert "未生成" in document_response.text
    assert "候補として提示されていません" in document_response.text
