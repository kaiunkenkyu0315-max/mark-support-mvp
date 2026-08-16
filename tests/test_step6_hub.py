import pytest
from fastapi.testclient import TestClient

from app import company_profile, intake_demo_state
from app.intake_schemas import QuestionnaireAnswers
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_states():
    company_profile.reset_state()
    intake_demo_state.reset_state()
    yield
    company_profile.reset_state()
    intake_demo_state.reset_state()


def _complete_employee_case() -> None:
    intake_demo_state.submit_answers(QuestionnaireAnswers(has_employees=True))
    candidate = intake_demo_state.get_state().candidates[0]
    intake_demo_state.confirm_candidate(candidate.id)
    intake_demo_state.update_ledger_entry(
        candidate.id,
        acquisition_method="本人から直接取得",
        storage_method="電子データ",
        storage_location="社内サーバ",
        outsourced=False,
        third_party_provided=False,
        retention_period="退職後5年",
        disposal_method="システムから削除",
        responsible_role="個人情報保護管理者",
    )
    for risk in list(intake_demo_state.get_state().risks):
        intake_demo_state.exclude_risk(risk.id)
    intake_demo_state.adopt_control("education")


def test_step6_becomes_operations_launch_hub_after_setup_completion():
    _complete_employee_case()

    response = client.get("/setup")

    assert response.status_code == 200
    assert "初期設定が完了しました。" in response.text
    assert "採用：1件" in response.text
    assert "個人情報保護教育" in response.text
    assert 'href="/education"' in response.text
    assert "教育管理を開始する" in response.text
    assert "PMS文書を確認する" in response.text
    assert "トップで準備・運用状況を確認する" in response.text
