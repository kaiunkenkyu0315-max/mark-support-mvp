import pytest
from fastapi.testclient import TestClient

from app import intake_demo_state, vendor_demo_state
from app.intake_schemas import ControlDecisionStatus, ControlSuggestion
from app.main import app

client = TestClient(app)


def _adopt_vendor_control() -> None:
    intake_demo_state.get_state().control_suggestions.append(
        ControlSuggestion(
            control_id="vendor_management",
            name="委託先管理",
            reason="テスト用",
            status=ControlDecisionStatus.ADOPTED,
            link_url="/vendors",
        )
    )


@pytest.fixture(autouse=True)
def reset_vendor_state():
    """各テストを、委託先管理策が採用済みの運用状態から開始する。"""

    intake_demo_state.reset_state()
    _adopt_vendor_control()
    vendor_demo_state.reset_state()
    yield
    intake_demo_state.reset_state()
    vendor_demo_state.reset_state()


def test_vendors_page_returns_200():
    response = client.get("/vendors")

    assert response.status_code == 200


def test_vendors_page_shows_all_three_vendors():
    response = client.get("/vendors")

    assert "給与計算会社" in response.text
    assert "採用管理クラウド" in response.text
    assert "機密文書廃棄会社" in response.text


def test_initial_state_is_needs_action():
    response = client.get("/vendors")

    assert "要対応" in response.text


def test_initial_state_shows_expected_issue_rules():
    response = client.get("/vendors")

    for rule_id in ("VEN-001", "VEN-002", "VEN-004"):
        assert rule_id in response.text


def test_todo_items_include_their_action_buttons():
    response = client.get("/vendors")

    assert "評価済みにする" in response.text
    assert "契約確認を完了する" in response.text
    assert "定期評価を完了する" in response.text


def test_resolving_all_issues_results_in_compliant():
    client.post("/vendors/actions/complete-initial-assessments")
    client.post("/vendors/actions/confirm-contracts")
    response = client.post("/vendors/actions/complete-periodic-assessments")

    assert response.status_code == 200
    assert "適合" in response.text
    assert "要対応" not in response.text
    assert "VEN-001" not in response.text


def test_reset_restores_initial_state():
    client.post("/vendors/actions/complete-initial-assessments")
    client.post("/vendors/actions/confirm-contracts")
    client.post("/vendors/actions/complete-periodic-assessments")

    response = client.post("/vendors/reset")

    assert response.status_code == 200
    assert "要対応" in response.text
    assert "VEN-001" in response.text
