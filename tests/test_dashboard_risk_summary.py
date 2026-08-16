import pytest
from fastapi.testclient import TestClient

from app import company_profile, intake_demo_state
from app.main import app
from app.risk_schemas import RiskCandidate, RiskCandidateStatus

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_states():
    company_profile.reset_state()
    intake_demo_state.reset_state()
    yield
    company_profile.reset_state()
    intake_demo_state.reset_state()


def test_dashboard_shows_confirmed_high_risk_from_setup_state():
    """確定済み高リスクが、トップのリスク集計へそのまま反映される。"""

    state = intake_demo_state.get_state()
    state.risks = [
        RiskCandidate(
            id=1,
            risk_id="RISK-TEST",
            name="誤送信・誤提供",
            description="テスト用",
            reason="テスト用",
            status=RiskCandidateStatus.CONFIRMED,
            suggested_impact=3,
            suggested_likelihood=3,
            impact=3,
            likelihood=3,
            evaluation_reviewed=True,
        )
    ]

    response = client.get("/")

    assert response.status_code == 200
    assert "確認済み：1件" in response.text
    assert "高：1件／中：0件／低：0件" in response.text
