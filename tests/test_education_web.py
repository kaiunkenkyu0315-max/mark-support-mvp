import pytest
from fastapi.testclient import TestClient

from app import demo_state, intake_demo_state
from app.intake_schemas import ControlDecisionStatus, ControlSuggestion
from app.main import app

client = TestClient(app)


def _adopt_education_control() -> None:
    intake_demo_state.get_state().control_suggestions.append(
        ControlSuggestion(
            control_id="education",
            name="個人情報保護教育",
            reason="テスト用",
            status=ControlDecisionStatus.ADOPTED,
            link_url="/education",
        )
    )


@pytest.fixture(autouse=True)
def reset_demo_state():
    """各テストを、教育管理策が採用済みの運用状態から開始する。"""

    intake_demo_state.reset_state()
    _adopt_education_control()
    demo_state.reset_state()
    yield
    intake_demo_state.reset_state()
    demo_state.reset_state()


def test_top_page_returns_200():
    response = client.get("/")

    assert response.status_code == 200


def test_top_page_links_to_education_demo():
    response = client.get("/")

    assert '/education' in response.text


def test_education_page_returns_200_and_shows_company():
    response = client.get("/education")

    assert response.status_code == 200
    assert "株式会社サンプル" in response.text


def test_initial_state_is_needs_action():
    response = client.get("/education")

    assert "要対応" in response.text


def test_initial_state_has_two_not_completed_employees():
    response = client.get("/education")

    assert "EDU-003" in response.text
    assert "未受講者が2名います" in response.text


def test_initial_state_shows_all_four_issue_rules():
    response = client.get("/education")

    for rule_id in ("EDU-003", "EDU-006", "EDU-008", "EDU-009"):
        assert rule_id in response.text


def test_initial_state_shows_issue_count_and_todo_list():
    response = client.get("/education")

    assert "対応が必要な項目：4件" in response.text
    assert "今やること" in response.text
    assert "未受講者がいます" in response.text
    assert "一般従業員49" in response.text
    assert "一般従業員50" in response.text


def test_todo_uses_record_entry_forms_instead_of_magic_completion_buttons():
    response = client.get("/education")

    assert "教育実施記録" in response.text
    assert 'name="execution_date"' in response.text
    assert 'name="delivery_method"' in response.text
    assert 'name="material_name"' in response.text
    assert 'name="instructor_name"' in response.text
    assert 'name="completed_on"' in response.text
    assert 'name="comprehension_method"' in response.text
    assert 'name="approved_by"' in response.text
    assert 'name="approved_at"' in response.text
    assert "未受講者を受講済みにする" not in response.text


def test_structured_record_fields_are_saved():
    client.post(
        "/education/actions/register-material-evidence",
        data={
            "execution_date": "2026-06-10",
            "delivery_method": "オンライン研修",
            "material_name": "2026年度 個人情報保護教育資料 v1.0",
            "instructor_name": "Pマーク担当者",
        },
    )
    client.post(
        "/education/actions/complete-trainings",
        data={"completed_on": "2026-06-10"},
    )
    client.post(
        "/education/actions/register-comprehension",
        data={"comprehension_method": "理解度確認テスト", "result": "passed"},
    )
    client.post(
        "/education/actions/approve",
        data={"approved_by": "個人情報保護管理者 山田", "approved_at": "2026-06-11"},
    )

    state = demo_state.get_state()
    assert state.plan.execution_date == "2026-06-10"
    assert state.plan.delivery_method == "オンライン研修"
    assert state.plan.material_name == "2026年度 個人情報保護教育資料 v1.0"
    assert state.plan.instructor_name == "Pマーク担当者"
    assert state.plan.comprehension_method == "理解度確認テスト"
    assert state.plan.approved_by == "個人情報保護管理者 山田"
    assert state.plan.approved_at == "2026-06-11"
    assert all(record.completed_on for record in state.records if record.completed)

    response = client.get("/education")
    assert "2026-06-10" in response.text
    assert "2026年度 個人情報保護教育資料 v1.0" in response.text
    assert "個人情報保護管理者 山田" in response.text
    assert "適合" in response.text


def test_resolving_all_issues_results_in_compliant():
    client.post("/education/actions/complete-trainings")
    client.post("/education/actions/register-comprehension")
    client.post("/education/actions/register-material-evidence")
    response = client.post("/education/actions/approve")

    assert response.status_code == 200
    assert "適合" in response.text
    assert "要対応" not in response.text
    assert "EDU-003" not in response.text


def test_reset_restores_initial_state():
    client.post("/education/actions/complete-trainings")
    client.post("/education/actions/register-comprehension")
    client.post("/education/actions/register-material-evidence")
    client.post("/education/actions/approve")

    response = client.post("/education/reset")

    assert response.status_code == 200
    assert "要対応" in response.text
    assert "未受講者が2名います" in response.text
