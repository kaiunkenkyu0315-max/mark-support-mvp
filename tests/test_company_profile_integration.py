import pytest
from fastapi.testclient import TestClient

from app import company_profile, demo_state, intake_demo_state
from app.main import app

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


def test_setup_starts_with_shared_company_information_step():
    response = client.get("/setup")

    assert response.status_code == 200
    assert 'id="step0"' in response.text
    assert 'href="#step0"' in response.text
    assert "STEP 0　会社情報" in response.text
    assert 'action="/setup/company"' in response.text
    assert "株式会社サンプル" in response.text
    assert 'value="50"' in response.text
    assert 'value="2026"' in response.text


def test_company_information_flows_into_education_management():
    response = client.post(
        "/setup/company",
        data={
            "name": "株式会社テスト共通",
            "employee_count": "12",
            "fiscal_year": "2027",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/setup#step1"

    education = client.get("/education")
    assert education.status_code == 200
    assert "教育管理：株式会社テスト共通" in education.text
    assert "会社名：株式会社テスト共通" in education.text
    assert "従業者数：12名" in education.text
    assert "対象年度：2027年度" in education.text
    assert "2027年度 個人情報保護教育" in education.text
    assert "対象者：12名" in education.text


def test_default_company_profile_keeps_existing_education_demo_shape():
    education = client.get("/education")

    assert "株式会社サンプル" in education.text
    assert "従業者数：50名" in education.text
    assert "対象者：50名" in education.text
    assert "一般従業員49" in education.text
    assert "一般従業員50" in education.text
