import pytest
from fastapi.testclient import TestClient

from app import intake_demo_state
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_intake_state():
    intake_demo_state.reset_state()
    yield
    intake_demo_state.reset_state()


def _all_yes_answers():
    return {
        "has_employees": "yes",
        "recruits_people": "yes",
        "manages_customer_contacts": "yes",
        "receives_inquiries": "yes",
        "outsources_personal_data_processing": "yes",
        "uses_external_cloud_services": "yes",
        "stores_personal_data_on_paper": "yes",
        "allows_remote_access": "yes",
    }


def test_step3_includes_progressive_disclosure_assets():
    client.post("/setup/answers", data=_all_yes_answers())
    candidates = list(intake_demo_state.get_state().candidates)
    form = {f"candidate_{candidate.id}": "yes" for candidate in candidates}
    response = client.post("/setup/candidates/decide", data=form)

    assert response.status_code == 200
    assert "ledger-entry-toggle" in response.text
    assert "ledger-entry-body" in response.text
    assert "firstIncomplete" in response.text
    assert "入力済み" in response.text
    assert "未入力" in response.text


def test_step3_keeps_all_confirmed_ledger_forms_available():
    client.post("/setup/answers", data=_all_yes_answers())
    candidates = list(intake_demo_state.get_state().candidates)
    form = {f"candidate_{candidate.id}": "yes" for candidate in candidates}
    response = client.post("/setup/candidates/decide", data=form)

    for candidate in candidates:
        assert f'action="/setup/candidates/{candidate.id}/ledger"' in response.text
