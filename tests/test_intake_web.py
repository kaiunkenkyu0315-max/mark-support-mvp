import pytest
from fastapi.testclient import TestClient

from app import intake_demo_state
from app.intake_schemas import ControlDecisionStatus
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_intake_state():
    """各テストの前後でデモ状態を初期化し、テスト間の状態汚染を防ぐ。"""

    intake_demo_state.reset_state()
    yield
    intake_demo_state.reset_state()


ALL_NO_FORM = {
    "has_employees": "no",
    "recruits_people": "no",
    "manages_customer_contacts": "no",
    "receives_inquiries": "no",
    "outsources_personal_data_processing": "no",
    "uses_external_cloud_services": "no",
    "stores_personal_data_on_paper": "no",
    "allows_remote_access": "no",
}


def answers_form(*yes_fields):
    """全問「いいえ」を基本に、指定したフィールドだけ「はい」にしたフォームデータを作る。"""

    form = dict(ALL_NO_FORM)
    for field in yes_fields:
        form[field] = "yes"
    return form


def test_case1_setup_page_returns_200_in_unanswered_state():
    response = client.get("/setup")

    assert response.status_code == 200
    assert "まだ回答が保存されていません" in response.text


def test_case2_submitting_answers_generates_candidates_and_suggestions():
    response = client.post(
        "/setup/answers",
        data=answers_form("has_employees", "outsources_personal_data_processing"),
    )

    assert response.status_code == 200
    assert "従業員情報" in response.text
    assert "個人情報保護教育" in response.text
    assert "委託先管理" in response.text


def test_answers_are_reflected_when_changed():
    client.post("/setup/answers", data=answers_form("recruits_people"))
    response = client.post("/setup/answers", data=answers_form("has_employees"))

    assert "従業員情報" in response.text
    # 採用活動=いいえに変わったため、未確認のままだった採用応募者情報候補は残らない。
    assert "採用応募者情報" not in response.text


def test_case13_only_adopted_control_shows_link_to_its_operations_page():
    client.post("/setup/answers", data=answers_form("has_employees"))

    response = client.post("/setup/controls/education/adopt")

    assert response.status_code == 200
    assert "/education" in response.text
    assert "教育管理へ進む" in response.text


def test_non_applicable_control_does_not_show_operations_link():
    client.post(
        "/setup/answers",
        data=answers_form("has_employees", "outsources_personal_data_processing"),
    )

    response = client.post(
        "/setup/controls/vendor_management/not-applicable",
        data={"reason": "対象業務がないため"},
    )

    assert response.status_code == 200
    assert "対象業務がないため" in response.text
    assert "委託先管理へ進む" not in response.text


def test_confirming_candidate_moves_it_into_ledger():
    client.post("/setup/answers", data=answers_form("has_employees"))
    target = intake_demo_state.get_state().candidates[0]

    response = client.post(f"/setup/candidates/{target.id}/confirm")

    assert response.status_code == 200
    assert "確認済み個人情報" in response.text


def test_case14_reset_restores_unanswered_state():
    client.post("/setup/answers", data=answers_form("has_employees"))
    client.post("/setup/controls/education/adopt")

    response = client.post("/setup/reset")

    assert response.status_code == 200
    assert "まだ回答が保存されていません" in response.text
    state = intake_demo_state.get_state()
    assert state.answers_submitted is False
    assert state.control_suggestions == []


def test_case15_existing_education_page_still_works():
    response = client.get("/education")

    assert response.status_code == 200


def test_case15_existing_vendors_page_still_works():
    response = client.get("/vendors")

    assert response.status_code == 200
