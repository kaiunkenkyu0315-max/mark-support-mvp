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


def test_initial_state_shows_overall_issue_count_but_only_one_current_todo():
    response = client.get("/education")

    # 森：全体の不足数は残す。
    assert "対応が必要な項目：4件" in response.text

    # 木：現在対応する作業は1件だけに絞る。
    assert response.text.count("今やること") == 1
    assert "今やること <span" in response.text
    assert "1件" in response.text
    assert "教育実施・教材記録を登録してください" in response.text


def test_education_overview_shows_all_steps_and_current_position():
    response = client.get("/education")

    assert "教育の全体工程" in response.text
    assert "全体進捗：0 / 4 工程 完了" in response.text
    assert "1. 教育実施・教材記録" in response.text
    assert "2. 受講記録" in response.text
    assert "3. 理解度確認" in response.text
    assert "4. 実施結果の承認" in response.text
    assert "対応中 ← 現在" in response.text
    assert "現在地：1. 教育実施・教材記録" in response.text


def test_record_entry_shows_only_current_step_and_prefills_known_values():
    response = client.get("/education")

    assert "1. 教育実施・教材記録" in response.text
    assert 'name="execution_date"' in response.text
    assert 'name="delivery_method"' in response.text
    assert 'name="material_name"' in response.text
    assert 'value="2026年度 個人情報保護教育資料"' in response.text
    assert 'name="instructor_name"' in response.text
    assert 'value="Pマーク担当者"' in response.text

    # 後工程の入力欄は最初から同時表示しない。全体工程の見出しだけは表示する。
    assert 'name="completed_on"' not in response.text
    assert 'name="comprehension_method"' not in response.text
    assert 'name="approved_by"' not in response.text
    assert "未受講者を受講済みにする" not in response.text


def test_record_entry_advances_one_step_at_a_time_with_overall_progress():
    response = client.post(
        "/education/actions/register-material-evidence",
        data={
            "execution_date": "2026-06-10",
            "delivery_method": "オンライン研修",
            "material_name": "2026年度 個人情報保護教育資料 v1.0",
            "instructor_name": "Pマーク担当者",
        },
    )
    assert "全体進捗：1 / 4 工程 完了" in response.text
    assert "現在地：2. 受講記録" in response.text
    assert "未受講者2名の受講記録を登録してください" in response.text
    assert 'name="completed_on"' in response.text
    assert 'value="2026-06-10"' in response.text
    assert 'name="comprehension_method"' not in response.text
    assert 'name="approved_by"' not in response.text

    response = client.post(
        "/education/actions/complete-trainings",
        data={"completed_on": "2026-06-10"},
    )
    assert "全体進捗：2 / 4 工程 完了" in response.text
    assert "現在地：3. 理解度確認" in response.text
    # 既存の理解度未登録3名に、今回受講した2名が加わる。
    assert "理解度確認が未登録の5名について結果を登録してください" in response.text
    assert 'name="comprehension_method"' in response.text
    assert 'name="approved_by"' not in response.text

    response = client.post(
        "/education/actions/register-comprehension",
        data={"comprehension_method": "理解度確認テスト", "result": "passed"},
    )
    assert "全体進捗：3 / 4 工程 完了" in response.text
    assert "現在地：4. 実施結果の承認" in response.text
    assert "教育実施結果の承認記録を登録してください" in response.text
    assert 'name="approved_by"' in response.text

    response = client.post(
        "/education/actions/approve",
        data={"approved_by": "個人情報保護管理者 山田", "approved_at": "2026-06-11"},
    )
    assert "全体進捗：4 / 4 工程 完了" in response.text
    assert "現在地：全工程完了" in response.text
    assert "必要な教育実施記録は登録済みです" in response.text
    assert "適合" in response.text


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