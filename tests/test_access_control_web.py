import pytest
from fastapi.testclient import TestClient

from app import access_control_demo_state, intake_demo_state
from app.intake_schemas import ControlDecisionStatus, ControlSuggestion
from app.main import app

client = TestClient(app)


def _adopt_access_control() -> None:
    intake_demo_state.get_state().control_suggestions.append(
        ControlSuggestion(
            control_id="access_control",
            name="アクセス権限管理",
            reason="テスト用",
            status=ControlDecisionStatus.ADOPTED,
            link_url="/access-control",
        )
    )


@pytest.fixture(autouse=True)
def reset_access_control_state():
    intake_demo_state.reset_state()
    _adopt_access_control()
    access_control_demo_state.reset_state()
    yield
    intake_demo_state.reset_state()
    access_control_demo_state.reset_state()


def test_access_control_page_returns_200():
    response = client.get("/access-control")

    assert response.status_code == 200


def test_initial_state_is_needs_action():
    response = client.get("/access-control")

    assert "要対応" in response.text


def test_initial_state_shows_expected_issue_rules():
    response = client.get("/access-control")

    for rule_id in ("ACC-001", "ACC-002", "ACC-003", "ACC-004"):
        assert rule_id in response.text


def test_access_overview_shows_all_steps_but_only_current_record_form():
    response = client.get("/access-control")

    assert "アクセス権限管理の全体工程" in response.text
    assert "全体進捗：0 / 4 工程 完了" in response.text
    assert "アカウント棚卸し" in response.text
    assert "不要アカウント削除" in response.text
    assert "権限レビュー" in response.text
    assert "実施結果の承認" in response.text
    assert "48 / 50名 確認済み" in response.text
    assert "0 / 1件 削除済み" in response.text
    assert "現在地：1. アカウント棚卸し" in response.text
    assert "今やること" in response.text
    assert "1件" in response.text

    # 50名全員ではなく、未確認の2名だけを現在工程で判断する。
    assert 'name="decision_49"' in response.text
    assert 'name="decision_50"' in response.text
    assert 'name="decision_48"' not in response.text
    assert 'name="reviewed_on"' in response.text
    assert 'name="removal_date"' not in response.text
    assert 'name="review_date"' not in response.text
    assert 'name="approved_by"' not in response.text

    # 旧デモのワンクリック操作は通常画面に出さない。
    assert "アカウント確認を完了する" not in response.text
    assert "不要アカウントを削除する" not in response.text
    assert "権限レビューを完了する" not in response.text
    assert "実施結果を承認する" not in response.text


def test_structured_access_records_advance_one_step_at_a_time():
    response = client.post(
        "/access-control/actions/complete-account-reviews",
        data={
            "decision_49": "necessary",
            "decision_50": "unnecessary",
            "reviewed_on": "2026-06-20",
            "reviewed_by": "Pマーク担当 山田",
            "review_method": "アカウント一覧と人事情報の照合",
        },
    )
    assert "全体進捗：1 / 4 工程 完了" in response.text
    assert "現在地：2. 不要アカウント削除" in response.text
    assert 'name="removal_date"' in response.text
    assert 'name="review_date"' not in response.text

    state = access_control_demo_state.get_state()
    account49 = next(item for item in state.accounts if item.id == 49)
    account50 = next(item for item in state.accounts if item.id == 50)
    assert account49.necessary is True
    assert account50.necessary is False
    assert account49.reviewed_on == "2026-06-20"
    assert account50.reviewed_by == "Pマーク担当 山田"
    assert account50.review_method == "アカウント一覧と人事情報の照合"

    response = client.post(
        "/access-control/actions/remove-unnecessary-accounts",
        data={
            "removal_date": "2026-06-21",
            "removed_by": "システム管理 佐藤",
            "removal_evidence": "アカウント削除チケット AC-2026-001",
        },
    )
    assert "全体進捗：2 / 4 工程 完了" in response.text
    assert "現在地：3. 権限レビュー" in response.text
    assert 'name="review_date"' in response.text
    assert 'name="approved_by"' not in response.text

    account50 = next(item for item in access_control_demo_state.get_state().accounts if item.id == 50)
    assert account50.removed is True
    assert account50.removal_date == "2026-06-21"
    assert account50.removed_by == "システム管理 佐藤"
    assert account50.removal_evidence == "アカウント削除チケット AC-2026-001"

    response = client.post(
        "/access-control/actions/complete-review-cycle",
        data={
            "review_date": "2026-06-22",
            "reviewer_name": "Pマーク担当 山田",
            "review_method": "所属・職務との照合",
            "review_evidence": "2026年度 アクセス権限レビュー記録",
        },
    )
    assert "全体進捗：3 / 4 工程 完了" in response.text
    assert "現在地：4. 実施結果の承認" in response.text
    assert 'name="approved_by"' in response.text

    response = client.post(
        "/access-control/actions/approve-review-cycle",
        data={
            "approved_by": "個人情報保護管理者 鈴木",
            "approved_at": "2026-06-23",
        },
    )
    assert "全体進捗：4 / 4 工程 完了" in response.text
    assert "現在地：全工程完了" in response.text
    assert "必要なアクセス権限管理記録は登録済みです" in response.text
    assert "適合" in response.text

    cycle = access_control_demo_state.get_state().cycle
    assert cycle.review_date == "2026-06-22"
    assert cycle.reviewer_name == "Pマーク担当 山田"
    assert cycle.review_method == "所属・職務との照合"
    assert cycle.review_evidence == "2026年度 アクセス権限レビュー記録"
    assert cycle.approved_by == "個人情報保護管理者 鈴木"
    assert cycle.approved_at == "2026-06-23"


def test_resolving_all_issues_results_in_compliant():
    client.post("/access-control/actions/complete-account-reviews")
    client.post("/access-control/actions/remove-unnecessary-accounts")
    client.post("/access-control/actions/complete-review-cycle")
    response = client.post("/access-control/actions/approve-review-cycle")

    assert response.status_code == 200
    assert "適合" in response.text
    assert "要対応" not in response.text
    assert "ACC-001" not in response.text


def test_reset_restores_initial_state():
    client.post("/access-control/actions/complete-account-reviews")
    client.post("/access-control/actions/remove-unnecessary-accounts")
    client.post("/access-control/actions/complete-review-cycle")
    client.post("/access-control/actions/approve-review-cycle")

    response = client.post("/access-control/reset")

    assert response.status_code == 200
    assert "要対応" in response.text
    assert "ACC-001" in response.text
