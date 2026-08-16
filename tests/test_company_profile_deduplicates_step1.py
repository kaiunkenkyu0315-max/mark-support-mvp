import pytest
from fastapi.testclient import TestClient

from app import company_profile, intake_demo_state
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_states():
    company_profile.reset_state()
    intake_demo_state.reset_state()
    yield
    company_profile.reset_state()
    intake_demo_state.reset_state()


def _save_company(employee_count: int = 12):
    return client.post(
        "/setup/company",
        data={
            "name": "株式会社共通情報テスト",
            "employee_count": str(employee_count),
            "fiscal_year": "2027",
        },
    )


def test_step1_does_not_ask_employee_presence_again_after_company_profile_is_saved():
    _save_company(12)

    response = client.get("/setup")

    assert response.status_code == 200
    assert "従業者数：12名" in response.text
    assert "STEP0の会社情報から自動反映しています" in response.text
    assert "従業員がいますか？" not in response.text
    assert 'name="has_employees"' not in response.text


def test_employee_presence_is_derived_from_saved_company_profile_when_step1_is_submitted():
    _save_company(12)

    response = client.post(
        "/setup/answers",
        data={
            "recruits_people": "no",
            "manages_customer_contacts": "no",
            "receives_inquiries": "no",
            "outsources_personal_data_processing": "no",
            "uses_external_cloud_services": "no",
            "stores_personal_data_on_paper": "no",
            "allows_remote_access": "no",
        },
    )

    assert response.status_code == 200
    state = intake_demo_state.get_state()
    assert state.answers.has_employees is True
    assert any(candidate.source_key == "has_employees" for candidate in state.candidates)
    assert "従業員情報" in response.text
