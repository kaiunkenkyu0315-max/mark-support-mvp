import pytest
from fastapi.testclient import TestClient

from app import (
    access_control_demo_state,
    company_profile,
    demo_state,
    intake_demo_state,
    paper_demo_state,
    vendor_demo_state,
)
from app.intake_schemas import ControlDecisionStatus, SetupStatus
from app.main import app
from app.setup_progress import get_effective_setup_status

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_all_demo_states():
    company_profile.reset_state()
    intake_demo_state.reset_state()
    demo_state.reset_state()
    vendor_demo_state.reset_state()
    access_control_demo_state.reset_state()
    paper_demo_state.reset_state()
    yield
    company_profile.reset_state()
    intake_demo_state.reset_state()
    demo_state.reset_state()
    vendor_demo_state.reset_state()
    access_control_demo_state.reset_state()
    paper_demo_state.reset_state()


def test_dashboard_shows_development_preset_shortcut():
    response = client.get("/")

    assert response.status_code == 200
    assert "開発用ショートカット" in response.text
    assert "運用検証用プリセットをセット" in response.text
    assert 'action="/dev/preset/operations"' in response.text


def test_operational_review_preset_completes_setup_and_adopts_main_controls():
    response = client.post("/dev/preset/operations")

    assert response.status_code == 200
    assert get_effective_setup_status(intake_demo_state.get_state()) == SetupStatus.COMPLETE
    assert company_profile.get_state().configured is True

    statuses = {
        suggestion.control_id: suggestion.status
        for suggestion in intake_demo_state.get_state().control_suggestions
    }
    for control_id in (
        "education",
        "vendor_management",
        "access_control",
        "paper_management",
    ):
        assert statuses[control_id] == ControlDecisionStatus.ADOPTED

    # プリセット後は運用側を意図的な要対応初期状態で確認できる。
    for path, expected_heading in (
        ("/education", "教育管理"),
        ("/vendors", "委託先管理"),
        ("/access-control", "アクセス権限管理"),
        ("/paper", "紙媒体管理"),
    ):
        page = client.get(path)
        assert page.status_code == 200
        assert expected_heading in page.text
        assert "現在、この管理策は運用対象ではありません" not in page.text
        assert "要対応" in page.text
