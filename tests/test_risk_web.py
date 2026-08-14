import pytest
from fastapi.testclient import TestClient

from app import intake_demo_state
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_intake_state():
    """各テストの前後でデモ状態を初期化し、テスト間の状態汚染を防ぐ。"""

    intake_demo_state.reset_state()
    yield
    intake_demo_state.reset_state()


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


def confirm_all_candidates():
    for candidate in intake_demo_state.get_state().candidates:
        client.post(f"/setup/candidates/{candidate.id}/confirm")


def test_case11_setup_page_shows_risk_step_and_summary():
    response = client.post("/setup/answers", data=ALL_YES_FORM)

    assert response.status_code == 200
    assert "STEP4" in response.text
    assert "リスク確認" in response.text
    assert "リスク候補：" in response.text


def test_full_demo_scenario_yields_all_five_risk_candidates():
    client.post("/setup/answers", data=ALL_YES_FORM)
    confirm_all_candidates()

    response = client.get("/setup")

    for risk_name in ["不正アクセス", "紙媒体の紛失・盗難", "委託先での漏えい・不適切な取扱い", "誤送信・誤提供", "内部者による不適切な取扱い"]:
        assert risk_name in response.text


def test_confirming_and_excluding_risks_via_web():
    client.post("/setup/answers", data=ALL_YES_FORM)
    confirm_all_candidates()
    risks = intake_demo_state.get_state().risks
    to_confirm, to_exclude = risks[0], risks[1]

    client.post(f"/setup/risks/{to_confirm.id}/confirm")
    response = client.post(f"/setup/risks/{to_exclude.id}/exclude")

    state = intake_demo_state.get_state()
    confirmed = next(r for r in state.risks if r.id == to_confirm.id)
    excluded = next(r for r in state.risks if r.id == to_exclude.id)
    assert confirmed.status.value == "confirmed"
    assert excluded.status.value == "excluded"
    assert response.status_code == 200


def test_updating_risk_evaluation_via_web_changes_displayed_level():
    client.post("/setup/answers", data=ALL_YES_FORM)
    confirm_all_candidates()
    risk = intake_demo_state.get_state().risks[0]
    client.post(f"/setup/risks/{risk.id}/confirm")

    response = client.post(
        f"/setup/risks/{risk.id}/evaluate", data={"impact": "3", "likelihood": "3"}
    )

    assert response.status_code == 200
    updated = next(r for r in intake_demo_state.get_state().risks if r.id == risk.id)
    assert updated.impact == 3
    assert updated.likelihood == 3
    assert "（高）" in response.text


def test_confirmed_vendor_risk_reason_appears_in_control_step():
    client.post("/setup/answers", data=ALL_YES_FORM)
    confirm_all_candidates()
    vendor_risk = next(
        r for r in intake_demo_state.get_state().risks if r.risk_id == "RISK-003"
    )

    response = client.post(f"/setup/risks/{vendor_risk.id}/confirm")

    assert "委託先での漏えい" in response.text
    assert "委託先での漏えい・不適切な取扱いリスクが確認されています。" in response.text


def test_case15_reset_clears_risk_state_via_web():
    client.post("/setup/answers", data=ALL_YES_FORM)
    confirm_all_candidates()
    risk = intake_demo_state.get_state().risks[0]
    client.post(f"/setup/risks/{risk.id}/confirm")

    response = client.post("/setup/reset")

    assert response.status_code == 200
    assert intake_demo_state.get_state().risks == []


def test_case16_existing_education_and_vendors_pages_still_work():
    response_education = client.get("/education")
    response_vendors = client.get("/vendors")

    assert response_education.status_code == 200
    assert response_vendors.status_code == 200
