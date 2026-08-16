import pytest
from fastapi.testclient import TestClient

from app import (
    access_control_demo_state,
    company_profile,
    demo_state,
    intake_demo_state,
    paper_demo_state,
    pms_review_demo_state,
    vendor_demo_state,
)
from app.access_control import evaluate_access_control
from app.education import evaluate_training
from app.intake_schemas import ControlDecisionStatus, SetupStatus
from app.main import app
from app.paper import evaluate_paper_management
from app.setup_progress import get_effective_setup_status
from app.vendors import evaluate_vendors

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_all_demo_states():
    company_profile.reset_state()
    intake_demo_state.reset_state()
    demo_state.reset_state()
    vendor_demo_state.reset_state()
    access_control_demo_state.reset_state()
    paper_demo_state.reset_state()
    pms_review_demo_state.reset_state()
    yield
    company_profile.reset_state()
    intake_demo_state.reset_state()
    demo_state.reset_state()
    vendor_demo_state.reset_state()
    access_control_demo_state.reset_state()
    paper_demo_state.reset_state()
    pms_review_demo_state.reset_state()


def test_dashboard_shows_development_preset_shortcuts():
    response = client.get("/")

    assert response.status_code == 200
    assert "開発用ショートカット" in response.text
    assert "運用検証用プリセットをセット" in response.text
    assert 'action="/dev/preset/operations"' in response.text
    assert "PMSレビュー検証用プリセットをセット" in response.text
    assert 'action="/dev/preset/pms-review"' in response.text


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


def test_pms_review_preset_completes_four_operations_and_opens_internal_audit():
    response = client.post("/dev/preset/pms-review", follow_redirects=True)

    assert response.status_code == 200
    assert "PMS評価・改善" in response.text
    assert "現在地：1. 内部監査" in response.text

    education_state = demo_state.get_state()
    assert not evaluate_training(
        education_state.employees,
        education_state.control,
        education_state.plan,
        education_state.records,
    ).issues

    vendor_state = vendor_demo_state.get_state()
    assert not evaluate_vendors(
        vendor_state.vendors,
        vendor_state.control,
        vendor_state.assessments,
        vendor_state.contracts,
    ).issues

    access_state = access_control_demo_state.get_state()
    assert not evaluate_access_control(
        access_state.accounts, access_state.control, access_state.cycle
    ).issues

    paper_state = paper_demo_state.get_state()
    assert not evaluate_paper_management(paper_state.control, paper_state.status).issues
