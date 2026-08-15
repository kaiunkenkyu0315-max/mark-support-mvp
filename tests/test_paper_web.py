import pytest
from fastapi.testclient import TestClient

from app import paper_demo_state
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_paper_state():
    paper_demo_state.reset_state()
    yield
    paper_demo_state.reset_state()


def test_paper_page_returns_200():
    response = client.get("/paper")

    assert response.status_code == 200


def test_initial_state_is_needs_action():
    response = client.get("/paper")

    assert "要対応" in response.text


def test_initial_state_shows_expected_issue_rules():
    response = client.get("/paper")

    for rule_id in ("PAP-001", "PAP-002", "PAP-003", "PAP-004"):
        assert rule_id in response.text


def test_todo_items_include_their_action_buttons():
    response = client.get("/paper")

    assert "施錠管理を確認する" in response.text
    assert "持出しルールを設定する" in response.text
    assert "廃棄確認を実施する" in response.text
    assert "実施結果を承認する" in response.text


def test_resolving_all_issues_results_in_compliant():
    client.post("/paper/actions/confirm-storage-lock")
    client.post("/paper/actions/define-take-out-rule")
    client.post("/paper/actions/confirm-disposal")
    response = client.post("/paper/actions/approve")

    assert response.status_code == 200
    assert "適合" in response.text
    assert "要対応" not in response.text
    assert "PAP-001" not in response.text


def test_reset_restores_initial_state():
    client.post("/paper/actions/confirm-storage-lock")
    client.post("/paper/actions/define-take-out-rule")
    client.post("/paper/actions/confirm-disposal")
    client.post("/paper/actions/approve")

    response = client.post("/paper/reset")

    assert response.status_code == 200
    assert "要対応" in response.text
    assert "PAP-001" in response.text
