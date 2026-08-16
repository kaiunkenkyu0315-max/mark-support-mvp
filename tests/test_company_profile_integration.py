import pytest
from fastapi.testclient import TestClient

from app import company_profile, demo_state, intake_demo_state
from app.intake_schemas import ControlDecisionStatus, ControlSuggestion
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


def _adopt_education_control() -> None:
    intake_demo_state.get_state().control_suggestions.append(
        ControlSuggestion(
            control_id="education",
            name="個人情報保護教育",
            reason="会社情報連携テスト用",
            status=ControlDecisionStatus.ADOPTED,
            link_url="/education",
        )
    )


def test_setup_starts_with_shared_company_information_step():
    response = client.get("/setup")

    assert response.status_code == 200
    assert 'id="step0"' in response.text
    assert 'href="#step0"' in response.text
    assert "STEP 0　会社・PMS基本情報" in response.text
    assert 'action="/setup/company"' in response.text
    assert "株式会社サンプル" in response.text
    assert 'value="50"' in response.text
    assert 'value="2026"' in response.text
    assert "個人情報保護管理者 氏名" in response.text
    assert "個人情報保護監査責任者 氏名" in response.text
    assert "Pマーク申請担当者 氏名" in response.text


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

    _adopt_education_control()
    education = client.get("/education")
    assert education.status_code == 200
    assert "教育管理：株式会社テスト共通" in education.text
    assert "会社名：株式会社テスト共通" in education.text
    assert "従業者数：12名" in education.text
    assert "対象年度：2027年度" in education.text
    assert "2027年度 個人情報保護教育" in education.text
    assert "対象者：12名" in education.text


def test_pms_and_application_profile_fields_are_saved_as_shared_data():
    response = client.post(
        "/setup/company",
        data={
            "name": "株式会社申請テスト",
            "name_kana": "カブシキガイシャシンセイテスト",
            "corporate_number": "1234567890123",
            "registered_address": "東京都港区六本木1-2-3",
            "representative_title": "代表取締役",
            "representative_name": "山田 太郎",
            "employee_count": "20",
            "fiscal_year": "2026",
            "privacy_manager_name": "山田 花子",
            "privacy_manager_department_role": "管理部 部長",
            "audit_manager_name": "佐藤 次郎",
            "audit_manager_department_role": "取締役",
            "application_contact_name": "鈴木 美咲",
            "application_contact_department_role": "総務部 主任",
            "application_contact_email": "privacy@example.jp",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    profile = company_profile.get_state()
    assert profile.name == "株式会社申請テスト"
    assert profile.name_kana == "カブシキガイシャシンセイテスト"
    assert profile.corporate_number == "1234567890123"
    assert profile.registered_address == "東京都港区六本木1-2-3"
    assert profile.representative_title == "代表取締役"
    assert profile.representative_name == "山田 太郎"
    assert profile.privacy_manager_name == "山田 花子"
    assert profile.audit_manager_name == "佐藤 次郎"
    assert profile.application_contact_email == "privacy@example.jp"

    setup = client.get("/setup")
    assert "山田 花子" in setup.text
    assert "佐藤 次郎" in setup.text
    assert "privacy@example.jp" in setup.text


def test_default_company_profile_keeps_existing_education_demo_shape():
    _adopt_education_control()
    education = client.get("/education")

    assert "株式会社サンプル" in education.text
    assert "従業者数：50名" in education.text
    assert "対象者：50名" in education.text
    assert "一般従業員49" in education.text
    assert "一般従業員50" in education.text
