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


def test_next_action_section_appears_after_plan_before_detail_sections():
    _reset_all_state()
    response = client.get("/")
    _reset_all_state()

    assert response.status_code == 200

    # 計画表や説明文にも同じ語が現れ得るため、実際の見出し・details summaryを対象に
    # 「森 → 今やる1件 → 詳細」の画面構造を確認する。
    plan_index = response.text.index('<h2 style="margin-top:0;">Pマーク取得の全体計画</h2>')
    next_action_index = response.text.index("<h2>次にやること</h2>")
    preparation_index = response.text.index("Pマーク準備状況を詳しく見る")
    operations_index = response.text.index("運用状況を詳しく見る")

    assert plan_index < next_action_index < preparation_index < operations_index
