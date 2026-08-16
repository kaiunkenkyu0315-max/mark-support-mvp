import pytest
from fastapi.testclient import TestClient

from app import intake_demo_state
from app.intake_schemas import PersonalInformationCandidateStatus
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


def test_step2_uses_yes_no_radios_and_one_batch_submit():
    response = client.post("/setup/answers", data=_all_yes_answers())

    assert response.status_code == 200
    assert 'action="/setup/candidates/decide"' in response.text
    assert "回答を保存して次へ" in response.text
    assert "取り扱っていますか？" in response.text
    assert 'value="yes"' in response.text
    assert 'value="no"' in response.text
    # STEP2では候補ごとの個別送信を使わない。ページ内のリスク確認URL等は対象外。
    assert 'action="/setup/candidates/1/confirm"' not in response.text
    assert 'action="/setup/candidates/1/exclude"' not in response.text


def test_step2_batch_save_updates_all_candidates_at_once():
    client.post("/setup/answers", data=_all_yes_answers())
    candidates = list(intake_demo_state.get_state().candidates)
    assert len(candidates) >= 2

    form = {
        f"candidate_{candidate.id}": "yes" if index % 2 == 0 else "no"
        for index, candidate in enumerate(candidates)
    }
    response = client.post("/setup/candidates/decide", data=form, follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/setup#step3"

    updated = intake_demo_state.get_state().candidates
    for index, candidate in enumerate(updated):
        expected = (
            PersonalInformationCandidateStatus.CONFIRMED
            if index % 2 == 0
            else PersonalInformationCandidateStatus.EXCLUDED
        )
        assert candidate.status == expected
        assert candidate.needs_review is False


def test_existing_decisions_are_preselected_when_revisiting_step2():
    client.post("/setup/answers", data=_all_yes_answers())
    candidates = list(intake_demo_state.get_state().candidates)
    form = {f"candidate_{candidate.id}": "yes" for candidate in candidates}
    client.post("/setup/candidates/decide", data=form)

    response = client.get("/setup")

    assert response.status_code == 200
    assert response.text.count('value="yes" required checked') >= len(candidates)
