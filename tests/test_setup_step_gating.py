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


def _prepare_employee_and_remote_access_case():
    intake_demo_state.submit_answers(
        QuestionnaireAnswers(has_employees=True, allows_remote_access=True)
    )
    candidate = intake_demo_state.get_state().candidates[0]
    intake_demo_state.confirm_candidate(candidate.id)
    return candidate


def _complete_ledger(candidate_id: int) -> None:
    intake_demo_state.update_ledger_entry(
        candidate_id,
        acquisition_method="本人から直接取得",
        storage_method="電子データ",
        storage_location="社内サーバ",
        outsourced=False,
        third_party_provided=False,
        retention_period="退職後5年",
        disposal_method="システムから削除",
        responsible_role="個人情報保護管理者",
    )


def test_step4_is_locked_while_ledger_is_incomplete():
    _prepare_employee_and_remote_access_case()

    response = client.get("/setup")

    assert response.status_code == 200
    assert "STEP3の個人情報台帳を完了すると、リスク候補を確認できるようになります。" in response.text
    assert 'action="/setup/risks/' not in response.text
    assert "STEP4のリスク確認を完了すると、管理策候補を確認できるようになります。" in response.text


def test_step4_unlocks_after_ledger_completion_but_step5_stays_locked():
    candidate = _prepare_employee_and_remote_access_case()
    _complete_ledger(candidate.id)

    response = client.get("/setup")

    assert "STEP3の個人情報台帳を完了すると、リスク候補を確認できるようになります。" not in response.text
    assert "不正アクセス" in response.text
    assert 'action="/setup/risks/' in response.text
    assert "STEP4のリスク確認を完了すると、管理策候補を確認できるようになります。" in response.text


def test_step5_unlocks_after_all_risk_decisions_and_step6_stays_locked():
    candidate = _prepare_employee_and_remote_access_case()
    _complete_ledger(candidate.id)

    for risk in list(intake_demo_state.get_state().risks):
        intake_demo_state.confirm_risk(risk.id)

    response = client.get("/setup")

    assert "STEP4のリスク確認を完了すると、管理策候補を確認できるようになります。" not in response.text
    assert "採用する" in response.text
    assert "STEP5の管理策判断を完了すると、運用画面へ進めるようになります。" in response.text


def test_step6_unlocks_after_all_control_decisions():
    candidate = _prepare_employee_and_remote_access_case()
    _complete_ledger(candidate.id)

    for risk in list(intake_demo_state.get_state().risks):
        intake_demo_state.confirm_risk(risk.id)
    for suggestion in list(intake_demo_state.get_state().control_suggestions):
        intake_demo_state.adopt_control(suggestion.control_id)

    response = client.get("/setup")

    assert "STEP5の管理策判断を完了すると、運用画面へ進めるようになります。" not in response.text
    assert "採用した管理策の運用画面に進めます。" in response.text
