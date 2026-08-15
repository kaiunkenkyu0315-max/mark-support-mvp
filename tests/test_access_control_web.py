import pytest
from fastapi.testclient import TestClient

from app import access_control_demo_state
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_access_control_state():
    access_control_demo_state.reset_state()
    yield
    access_control_demo_state.reset_state()


def test_access_control_page_returns_200():
    response = client.get("/access-control")

    assert response.status_code == 200


def test_initial_state_is_needs_action():
    response = client.get("/access-control")

    assert "要対応" in response.text


def test_initial_state_shows_expected_issue_rules():
    response = client.get("/access-control")

    for rule_id in ("ACC-001", "ACC-002", "ACC-003", "ACC-004"):
        assert rule_id in response.text


def test_todo_items_include_their_action_buttons():
    response = client.get("/access-control")

    assert "アカウント確認を完了する" in response.text
    assert "不要アカウントを削除する" in response.text
    assert "権限レビューを完了する" in response.text
    assert "実施結果を承認する" in response.text


def test_resolving_all_issues_results_in_compliant():
    client.post("/access-control/actions/complete-account-reviews")
    client.post("/access-control/actions/remove-unnecessary-accounts")
    client.post("/access-control/actions/complete-review-cycle")
    response = client.post("/access-control/actions/approve-review-cycle")

    assert response.status_code == 200
    assert "適合" in response.text
    assert "要対応" not in response.text
    assert "ACC-001" not in response.text


def test_reset_restores_initial_state():
    client.post("/access-control/actions/complete-account-reviews")
    client.post("/access-control/actions/remove-unnecessary-accounts")
    client.post("/access-control/actions/complete-review-cycle")
    client.post("/access-control/actions/approve-review-cycle")

    response = client.post("/access-control/reset")

    assert response.status_code == 200
    assert "要対応" in response.text
    assert "ACC-001" in response.text
