"""初期設定の中間状態で、ダッシュボードが次の1工程を案内することを確認する。"""

import pytest
from fastapi.testclient import TestClient

from app import (
    access_control_demo_state,
    demo_state,
    intake_demo_state,
    paper_demo_state,
    vendor_demo_state,
)
from app.main import app

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


def _submit_all_yes():
    client.post(
        "/setup/answers",
        data={
            "has_employees": "yes",
            "recruits_people": "yes",
            "manages_customer_contacts": "yes",
            "receives_inquiries": "yes",
            "outsources_personal_data_processing": "yes",
            "uses_external_cloud_services": "yes",
            "stores_personal_data_on_paper": "yes",
            "allows_remote_access": "yes",
        },
    )


def test_dashboard_guides_to_personal_information_confirmation_after_answers():
    _submit_all_yes()

    response = client.get("/")

    assert response.status_code == 200
    assert "個人情報候補を確認してください" in response.text
    assert "個人情報・リスク・管理策の確認や台帳項目の入力が完了していません" not in response.text


def test_document_card_waits_for_personal_information_confirmation():
    _submit_all_yes()

    response = client.get("/")

    assert "個人情報確認待ち" in response.text
    assert "文書：個人情報管理台帳の入力が不足しています" not in response.text


def test_untriggered_control_note_mentions_progressing_confirmation_flow():
    _submit_all_yes()

    response = client.get("/")

    assert "個人情報・リスクの確認を進める" in response.text
    assert "業務回答を変更すると候補になる場合があります" not in response.text
