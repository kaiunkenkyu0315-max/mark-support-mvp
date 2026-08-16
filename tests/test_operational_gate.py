from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from app import (
    access_control_demo_state,
    demo_state,
    intake_demo_state,
    paper_demo_state,
    vendor_demo_state,
)
from app.main import app

client = TestClient(app)


CASES = [
    (
        "/education",
        "/education/actions/complete-trainings",
        "未受講者を受講済みにする",
        demo_state,
    ),
    (
        "/vendors",
        "/vendors/actions/complete-initial-assessments",
        "評価済みにする",
        vendor_demo_state,
    ),
    (
        "/access-control",
        "/access-control/actions/complete-account-reviews",
        "アカウント確認を完了する",
        access_control_demo_state,
    ),
    (
        "/paper",
        "/paper/actions/confirm-storage-lock",
        "施錠管理を確認する",
        paper_demo_state,
    ),
]


@pytest.fixture(autouse=True)
def reset_all_states():
    intake_demo_state.reset_state()
    demo_state.reset_state()
    vendor_demo_state.reset_state()
    access_control_demo_state.reset_state()
    paper_demo_state.reset_state()
    yield
    intake_demo_state.reset_state()
    demo_state.reset_state()
    vendor_demo_state.reset_state()
    access_control_demo_state.reset_state()
    paper_demo_state.reset_state()


@pytest.mark.parametrize("page_path,action_path,action_label,state_module", CASES)
def test_unadopted_operational_page_hides_evaluation_and_actions(
    page_path, action_path, action_label, state_module
):
    response = client.get(page_path)

    assert response.status_code == 200
    assert "現在、この管理策は運用対象ではありません。" in response.text
    assert "現在の状態：要対応" not in response.text
    assert action_label not in response.text
    assert "初期設定の管理策確認へ" in response.text


@pytest.mark.parametrize("page_path,action_path,action_label,state_module", CASES)
def test_unadopted_operational_action_does_not_mutate_demo_state(
    page_path, action_path, action_label, state_module
):
    before = deepcopy(state_module.get_state())

    response = client.post(action_path)

    assert response.status_code == 200
    assert state_module.get_state() == before
    assert "現在、この管理策は運用対象ではありません。" in response.text
