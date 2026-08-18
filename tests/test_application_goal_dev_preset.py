from fastapi.testclient import TestClient

from app import (
    access_control_demo_state,
    application_prep_demo_state,
    company_profile,
    demo_state,
    intake_demo_state,
    paper_demo_state,
    pms_review_demo_state,
    vendor_demo_state,
)
from app.application_prep import evaluate_application_prep
from app.application_prep_context import build_application_prerequisites
from app.main import app


client = TestClient(app)


def _reset_all() -> None:
    company_profile.reset_state()
    intake_demo_state.reset_state()
    demo_state.reset_state()
    vendor_demo_state.reset_state()
    access_control_demo_state.reset_state()
    paper_demo_state.reset_state()
    pms_review_demo_state.reset_state()
    application_prep_demo_state.reset_state()


def test_application_goal_preset_opens_completed_goal_screen():
    _reset_all()
    try:
        response = client.post("/dev/preset/application-goal", follow_redirects=True)

        assert response.status_code == 200
        assert evaluate_application_prep(
            application_prep_demo_state.get_state(),
            build_application_prerequisites(),
        ).complete is True
        assert "申請提出前の準備が整いました" in response.text
        assert "JIPDEC" in response.text
        assert "山田 花子" in response.text
        assert "次は、審査機関への実際の申請・審査です" in response.text
    finally:
        _reset_all()
