import pytest
from fastapi.testclient import TestClient

from app import company_profile, demo_state, intake_demo_state
from app.intake_schemas import SetupStatus
from app.main import app
from app.setup_progress import get_effective_setup_status

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_states():
    company_profile.reset_state()
    intake_demo_state.reset_state()
    demo_state.reset_state()
    yield
    company_profile.reset_state()
    intake_demo_state.reset_state()
    demo_state.reset_state()


def _save_company():
    return client.post(
        "/setup/company",
        data={
            "name": "株式会社進捗テスト",
            "employee_count": "4",
            "fiscal_year": "2026",
        },
        follow_redirects=False,
    )


def test_company_profile_save_starts_setup_progress():
    assert get_effective_setup_status(intake_demo_state.get_state()) == SetupStatus.NOT_STARTED

    _save_company()

    assert get_effective_setup_status(intake_demo_state.get_state()) == SetupStatus.IN_PROGRESS


def test_dashboard_shows_in_progress_and_guides_to_business_step_after_company_save():
    _save_company()

    response = client.get("/")

    assert response.status_code == 200
    assert "設定中" in response.text
    assert "会社・PMS基本情報は保存済みです。次に業務情報へ回答してください。" in response.text
    assert 'href="/setup#step1"' in response.text


def test_setup_page_contains_status_sync_for_saved_company_profile():
    _save_company()

    response = client.get("/setup")

    assert response.status_code == 200
    assert "会社・PMS基本情報の状態：保存済み" in response.text
    assert 'badge.textContent = "設定中"' in response.text
