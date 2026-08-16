import pytest
from fastapi.testclient import TestClient

from app import company_profile, intake_demo_state
from app.intake_schemas import SetupStatus
from app.main import app
from app.setup_step_gating import step5_unlocked

client = TestClient(app)

ALL_YES_FORM = {
    "has_employees": "yes",
    "recruits_people": "yes",
    "manages_customer_contacts": "yes",
    "receives_inquiries": "yes",
    "outsources_personal_data_processing": "yes",
    "uses_external_cloud_services": "yes",
    "stores_personal_data_on_paper": "yes",
    "allows_remote_access": "yes",
}

FULL_LEDGER_FORM = {
    "acquisition_method": "本人から直接取得",
    "storage_method": "電子データ",
    "storage_location": "社内サーバ",
    "outsourced": "no",
    "third_party_provided": "no",
    "retention_period": "利用目的終了後5年",
    "disposal_method": "システムから削除",
    "responsible_role": "個人情報保護管理者",
}


@pytest.fixture(autouse=True)
def reset_state():
    company_profile.reset_state()
    intake_demo_state.reset_state()
    yield
    company_profile.reset_state()
    intake_demo_state.reset_state()


def _unlock_step4():
    client.post("/setup/answers", data=ALL_YES_FORM)
    for candidate in list(intake_demo_state.get_state().candidates):
        client.post(f"/setup/candidates/{candidate.id}/confirm")
        form = dict(FULL_LEDGER_FORM)
        if candidate.outsourced is True:
            form["outsourced"] = "yes"
        client.post(f"/setup/candidates/{candidate.id}/ledger", data=form)


def test_step4_uses_one_batch_decision_form_after_ledger_completion():
    _unlock_step4()

    response = client.get("/setup")

    assert response.status_code == 200
    assert 'action="/setup/risks/decide"' in response.text
    assert "回答を保存して評価へ" in response.text
    assert "該当する" in response.text
    assert "該当しない" in response.text


def test_batch_decision_moves_only_confirmed_risks_to_evaluation_phase():
    _unlock_step4()
    risks = list(intake_demo_state.get_state().risks)
    data = {
        f"risk_{risk.id}": "yes" if index < 2 else "no"
        for index, risk in enumerate(risks)
    }

    response = client.post("/setup/risks/decide", data=data)

    state = intake_demo_state.get_state()
    assert response.status_code == 200
    assert sum(r.status.value == "confirmed" for r in state.risks) == 2
    assert all(not r.evaluation_reviewed for r in state.risks if r.status.value == "confirmed")
    assert "STEP 4　リスク評価" in response.text
    assert 'action="/setup/risks/evaluate-batch"' in response.text
    assert "評価をまとめて確定して次へ" in response.text
    assert step5_unlocked(state) is False
    assert intake_demo_state.get_setup_status(state) == SetupStatus.IN_PROGRESS


def test_batch_evaluation_unlocks_step5_after_one_submit():
    _unlock_step4()
    risks = list(intake_demo_state.get_state().risks)
    client.post(
        "/setup/risks/decide",
        data={f"risk_{risk.id}": "yes" for risk in risks},
    )
    confirmed = list(intake_demo_state.get_state().risks)
    evaluation_data = {}
    for risk in confirmed:
        evaluation_data[f"impact_{risk.id}"] = "2"
        evaluation_data[f"likelihood_{risk.id}"] = "2"

    response = client.post("/setup/risks/evaluate-batch", data=evaluation_data)

    state = intake_demo_state.get_state()
    assert response.status_code == 200
    assert all(r.evaluation_reviewed for r in state.risks)
    assert all(r.impact == 2 and r.likelihood == 2 for r in state.risks)
    assert step5_unlocked(state) is True
    assert "STEP 5　管理策確認" in response.text
    assert "STEP4のリスク判断と評価確認を完了すると" not in response.text


def test_dashboard_points_to_risk_evaluation_before_controls():
    _unlock_step4()
    risks = list(intake_demo_state.get_state().risks)
    client.post(
        "/setup/risks/decide",
        data={f"risk_{risk.id}": "yes" for risk in risks},
    )

    response = client.get("/")

    assert "リスク評価" in response.text
    assert "影響度・発生可能性を確認してください" in response.text
