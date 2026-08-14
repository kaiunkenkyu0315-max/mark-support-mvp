import pytest
from fastapi.testclient import TestClient

from app import demo_state
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_demo_state():
    """各テストの前後でデモ状態を初期化し、テスト間の状態汚染を防ぐ。"""

    demo_state.reset_state()
    yield
    demo_state.reset_state()


def test_top_page_returns_200():
    response = client.get("/")

    assert response.status_code == 200


def test_top_page_links_to_education_demo():
    response = client.get("/")

    assert '/education' in response.text


def test_education_page_returns_200_and_shows_company():
    response = client.get("/education")

    assert response.status_code == 200
    assert "株式会社サンプル" in response.text


def test_initial_state_is_needs_action():
    response = client.get("/education")

    assert "要対応" in response.text


def test_initial_state_has_two_not_completed_employees():
    response = client.get("/education")

    assert "EDU-003" in response.text
    assert "未受講者が2名います" in response.text


def test_initial_state_shows_all_four_issue_rules():
    response = client.get("/education")

    for rule_id in ("EDU-003", "EDU-006", "EDU-008", "EDU-009"):
        assert rule_id in response.text


def test_initial_state_shows_issue_count_and_todo_list():
    response = client.get("/education")

    assert "対応が必要な項目：4件" in response.text
    assert "今やること" in response.text
    assert "未受講者がいます" in response.text
    assert "一般従業員49" in response.text
    assert "一般従業員50" in response.text


def test_todo_items_include_their_action_buttons():
    response = client.get("/education")

    assert "未受講者を受講済みにする" in response.text
    assert "理解度確認結果を登録する（合格）" in response.text
    assert "教材記録を登録する" in response.text
    assert "承認する" in response.text


def test_resolving_all_issues_results_in_compliant():
    client.post("/education/actions/complete-trainings")
    client.post("/education/actions/register-comprehension")
    client.post("/education/actions/register-material-evidence")
    response = client.post("/education/actions/approve")

    assert response.status_code == 200
    assert "適合" in response.text
    assert "要対応" not in response.text
    assert "EDU-003" not in response.text


def test_reset_restores_initial_state():
    client.post("/education/actions/complete-trainings")
    client.post("/education/actions/register-comprehension")
    client.post("/education/actions/register-material-evidence")
    client.post("/education/actions/approve")

    response = client.post("/education/reset")

    assert response.status_code == 200
    assert "要対応" in response.text
    assert "未受講者が2名います" in response.text
