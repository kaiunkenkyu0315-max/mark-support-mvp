from fastapi.testclient import TestClient

from app import (
    access_control_demo_state,
    company_profile,
    demo_state,
    intake_demo_state,
    paper_demo_state,
    vendor_demo_state,
)
from app.main import app

client = TestClient(app)


def _reset_all() -> None:
    company_profile.reset_state()
    intake_demo_state.reset_state()
    demo_state.reset_state()
    vendor_demo_state.reset_state()
    access_control_demo_state.reset_state()
    paper_demo_state.reset_state()


def test_main_operational_areas_share_overview_current_task_and_record_pattern():
    _reset_all()
    client.post("/dev/preset/operations")

    expectations = (
        ("/education", "教育の全体工程", "教育実施記録"),
        ("/vendors", "委託先管理の全体工程", "初回評価記録"),
        ("/access-control", "アクセス権限管理の全体工程", "アカウント棚卸し記録"),
        ("/paper", "紙媒体管理の全体工程", "保管・施錠確認記録"),
    )

    for path, overview, current_record in expectations:
        response = client.get(path)
        assert response.status_code == 200
        assert overview in response.text
        assert "今やること" in response.text
        assert "1件" in response.text
        assert current_record in response.text
        assert "現在地：" in response.text

    _reset_all()
