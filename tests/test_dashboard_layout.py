"""管理者ダッシュボードの主要セクション順を固定するテスト。"""

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
from app.main import app

client = TestClient(app)


def _reset_all_state() -> None:
    company_profile.reset_state()
    intake_demo_state.reset_state()
    demo_state.reset_state()
    vendor_demo_state.reset_state()
    access_control_demo_state.reset_state()
    paper_demo_state.reset_state()
    pms_review_demo_state.reset_state()


def test_todo_section_appears_before_preparation_and_operations():
    _reset_all_state()
    response = client.get("/")
    _reset_all_state()

    assert response.status_code == 200

    # 計画表の説明文にも「運用状況」等の語が現れるため、一般文字列ではなく
    # 実際のセクション見出しを対象にして画面構造の順番を確認する。
    plan_index = response.text.index("<h2 style=\"margin-top:0;\">Pマーク取得の全体計画</h2>")
    todo_index = response.text.index("<h2>今やること")
    preparation_index = response.text.index("<h2>Pマーク準備状況</h2>")
    operations_index = response.text.index("<h2>運用状況</h2>")

    assert plan_index < todo_index < preparation_index < operations_index
