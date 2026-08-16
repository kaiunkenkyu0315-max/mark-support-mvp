"""管理者ダッシュボードの主要セクション順を固定するテスト。"""

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


def _reset_all_state() -> None:
    intake_demo_state.reset_state()
    demo_state.reset_state()
    vendor_demo_state.reset_state()
    access_control_demo_state.reset_state()
    paper_demo_state.reset_state()


def test_todo_section_appears_before_preparation_and_operations():
    _reset_all_state()
    response = client.get("/")
    _reset_all_state()

    assert response.status_code == 200

    todo_index = response.text.index("今やること")
    preparation_index = response.text.index("Pマーク準備状況")
    operations_index = response.text.index("運用状況")

    assert todo_index < preparation_index < operations_index
