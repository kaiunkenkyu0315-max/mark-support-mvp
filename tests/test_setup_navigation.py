from fastapi.testclient import TestClient

from app import intake_demo_state
from app.main import app

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


def setup_function():
    intake_demo_state.reset_state()


def teardown_function():
    intake_demo_state.reset_state()


def test_setup_stepper_links_to_all_six_steps_and_each_step_has_anchor():
    response = client.get("/setup")

    assert response.status_code == 200
    for step in range(1, 7):
        assert f'href="#step{step}"' in response.text
        assert f'id="step{step}"' in response.text


def test_personal_information_candidates_and_decision_actions_are_same_step():
    response = client.post("/setup/answers", data=ALL_YES_FORM)

    assert "STEP 2　個人情報確認" in response.text
    assert "STEP 2　個人情報候補" not in response.text
    assert 'action="/setup/candidates/decide"' in response.text
    assert "取り扱っていますか？" in response.text

    step2_pos = response.text.index('id="step2"')
    decide_pos = response.text.index('action="/setup/candidates/decide"')
    step3_pos = response.text.index('id="step3"')
    assert step2_pos < decide_pos < step3_pos


def test_each_setup_step_has_back_to_top_link():
    response = client.get("/setup")

    assert response.text.count('href="#setup-top"') >= 6
    assert "↑ 初期設定の先頭へ戻る" in response.text


def test_dashboard_setup_todo_links_directly_to_current_step():
    client.post("/setup/answers", data=ALL_YES_FORM)

    response = client.get("/")

    assert response.status_code == 200
    assert 'href="/setup#step2"' in response.text
