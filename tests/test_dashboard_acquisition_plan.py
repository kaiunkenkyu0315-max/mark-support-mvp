from fastapi.testclient import TestClient

from app import (
    access_control_demo_state,
    company_profile,
    demo_state,
    intake_demo_state,
    paper_demo_state,
    vendor_demo_state,
)
from app.dev_preset import load_operational_review_preset
from app.main import app

client = TestClient(app)


def _reset_all() -> None:
    company_profile.reset_state()
    intake_demo_state.reset_state()
    demo_state.reset_state()
    vendor_demo_state.reset_state()
    access_control_demo_state.reset_state()
    paper_demo_state.reset_state()


def test_acquisition_plan_is_the_top_level_forest_before_todo_details():
    _reset_all()
    response = client.get("/")
    _reset_all()

    assert response.status_code == 200
    assert "Pマーク取得の全体計画" in response.text
    assert "実装範囲進捗：0 / 3 工程 完了" in response.text
    assert "現在地：1. 初期設定" in response.text
    assert "内部監査" in response.text
    assert "マネジメントレビュー" in response.text
    assert "申請準備" in response.text
    assert "後続工程" in response.text

    plan_index = response.text.index("Pマーク取得の全体計画")
    todo_index = response.text.index("今やること")
    preparation_index = response.text.index("Pマーク準備状況")
    assert plan_index < todo_index < preparation_index


def test_operational_review_preset_places_current_location_at_operations_and_groups_todos():
    _reset_all()
    load_operational_review_preset()
    response = client.get("/")
    _reset_all()

    assert response.status_code == 200
    assert "実装範囲進捗：2 / 3 工程 完了" in response.text
    assert "現在地：3. 採用管理策の運用" in response.text
    assert "今やること　4件" in response.text
    assert response.text.count("教育管理：") == 1
    assert response.text.count("委託先管理：") == 1
    assert response.text.count("アクセス権限管理：") == 1
    assert response.text.count("紙媒体管理：") == 1


def test_acquisition_plan_marks_mvp_scope_complete_after_all_operations_are_resolved():
    _reset_all()
    load_operational_review_preset()

    demo_state.register_material_evidence()
    demo_state.complete_all_trainings()
    demo_state.register_missing_comprehension()
    demo_state.approve_plan()

    vendor_demo_state.complete_missing_initial_assessments()
    vendor_demo_state.confirm_missing_contracts()
    vendor_demo_state.complete_missing_periodic_assessments()

    access_control_demo_state.complete_missing_account_reviews()
    access_control_demo_state.remove_unnecessary_accounts()
    access_control_demo_state.complete_review_cycle()
    access_control_demo_state.approve_review_cycle()

    paper_demo_state.confirm_storage_lock()
    paper_demo_state.define_take_out_rule()
    paper_demo_state.confirm_disposal()
    paper_demo_state.approve_status()

    response = client.get("/")
    _reset_all()

    assert response.status_code == 200
    assert "実装範囲進捗：3 / 3 工程 完了" in response.text
    assert "現在地：MVP実装範囲完了（次の後続工程：4. 内部監査）" in response.text
