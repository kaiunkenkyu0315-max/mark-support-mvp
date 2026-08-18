import pytest
from fastapi.testclient import TestClient

from app import (
    access_control_demo_state,
    annual_cycle_demo_state,
    application_prep_demo_state,
    company_profile,
    demo_state,
    intake_demo_state,
    paper_demo_state,
    pms_review_demo_state,
    vendor_demo_state,
)
from app.main import app


client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_prototype_state():
    modules = (
        company_profile,
        intake_demo_state,
        demo_state,
        vendor_demo_state,
        access_control_demo_state,
        paper_demo_state,
        pms_review_demo_state,
        application_prep_demo_state,
        annual_cycle_demo_state,
    )
    for module in modules:
        module.reset_state()
    yield
    for module in modules:
        module.reset_state()


def test_dashboard_orders_overview_then_next_action_then_details():
    response = client.get("/")

    assert response.status_code == 200
    html = response.text

    plan_heading = '<h2 style="margin-top:0;">Pマーク取得の全体計画</h2>'
    next_action_heading = "<h2>次にやること</h2>"
    preparation_summary = "Pマーク準備状況を詳しく見る"

    assert plan_heading in html
    assert next_action_heading in html
    assert "この作業を進める" in html
    assert preparation_summary in html
    assert "運用状況を詳しく見る" in html

    assert html.index(plan_heading) < html.index(next_action_heading)
    assert html.index(next_action_heading) < html.index(preparation_summary)
    assert html.count('class="primary-action"') == 1


def test_dashboard_keeps_one_primary_action_when_multiple_areas_need_attention():
    preset = client.post("/dev/preset/operations", follow_redirects=True)
    assert preset.status_code == 200

    response = client.get("/")
    assert response.status_code == 200

    html = response.text
    assert html.count('class="primary-action"') == 1
    assert "そのほかの対応予定" in html
    assert "完了すると、次に必要な作業が更新されます" in html
