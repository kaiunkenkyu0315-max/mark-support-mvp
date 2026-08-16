import pytest
from fastapi.testclient import TestClient

from app import company_profile, intake_demo_state
from app.main import app
from app.risk_schemas import RiskCandidateStatus

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_states():
    company_profile.reset_state()
    intake_demo_state.reset_state()
    yield
    company_profile.reset_state()
    intake_demo_state.reset_state()


def test_dashboard_shows_confirmed_high_risk_from_setup_state():
    """STEP4で確定した高リスクが、トップのリスク集計へそのまま反映される。"""

    # 誤送信・誤提供リスクが候補になる最小ケース。
    intake_demo_state.submit_answers(
        intake_demo_state.QuestionnaireAnswers(has_employees=True)
        if hasattr(intake_demo_state, "QuestionnaireAnswers")
        else None
    )
