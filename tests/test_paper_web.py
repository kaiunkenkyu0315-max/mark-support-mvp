import pytest
from fastapi.testclient import TestClient

from app import intake_demo_state, paper_demo_state
from app.intake_schemas import ControlDecisionStatus, ControlSuggestion
from app.main import app

client = TestClient(app)


def _adopt_paper_control() -> None:
    intake_demo_state.get_state().control_suggestions.append(
        ControlSuggestion(
            control_id="paper_management",
            name="紙媒体の保管・持出し・廃棄管理",
            reason="テスト用",
            status=ControlDecisionStatus.ADOPTED,
            link_url="/paper",
        )
    )


@pytest.fixture(autouse=True)
def reset_paper_state():
    intake_demo_state.reset_state()
    _adopt_paper_control()
    paper_demo_state.reset_state()
    yield
    intake_demo_state.reset_state()
    paper_demo_state.reset_state()


def test_paper_page_returns_200():
    response = client.get("/paper")
    assert response.status_code == 200


def test_initial_state_is_needs_action():
    response = client.get("/paper")
    assert "要対応" in response.text


def test_initial_state_shows_expected_issue_rules():
    response = client.get("/paper")
    for rule_id in ("PAP-001", "PAP-002", "PAP-003", "PAP-004"):
        assert rule_id in response.text


def test_paper_overview_shows_all_steps_but_only_current_record_form():
    response = client.get("/paper")

    assert "紙媒体管理の全体工程" in response.text
    assert "全体進捗：0 / 4 工程 完了" in response.text
    assert "保管・施錠確認" in response.text
    assert "持出しルール" in response.text
    assert "廃棄確認" in response.text
    assert "実施結果の承認" in response.text
    assert "現在地：1. 保管・施錠確認" in response.text
    assert "今やること" in response.text
    assert "1件" in response.text

    # 現在工程だけ入力でき、確認結果は自動選択しない。
    assert 'name="storage_location"' in response.text
    assert 'name="locked"' in response.text
    assert '<option value="" selected disabled>選択してください</option>' in response.text
    assert 'name="checked_on"' in response.text
    assert 'name="rule"' not in response.text
    assert 'name="confirmed_on"' not in response.text
    assert 'name="approved_by"' not in response.text

    # 旧デモのワンクリック操作は通常画面に出さない。
    assert "施錠管理を確認する" not in response.text
    assert "持出しルールを設定する" not in response.text
    assert "廃棄確認を実施する" not in response.text
    assert "実施結果を承認する" not in response.text


def test_negative_lock_check_does_not_advance_to_next_step():
    response = client.post(
        "/paper/actions/confirm-storage-lock",
        data={
            "storage_location": "総務部キャビネット",
            "locked": "no",
            "checked_on": "2026-06-30",
            "checked_by": "Pマーク担当 山田",
            "check_method": "現地確認",
            "evidence": "保管場所確認記録",
        },
    )

    assert "全体進捗：0 / 4 工程 完了" in response.text
    assert "現在地：1. 保管・施錠確認" in response.text
    assert paper_demo_state.get_state().status.storage_locked is False
    assert paper_demo_state.get_state().status.storage_lock_checked_on == "2026-06-30"


def test_structured_paper_records_advance_one_step_at_a_time():
    response = client.post(
        "/paper/actions/confirm-storage-lock",
        data={
            "storage_location": "総務部 鍵付きキャビネット",
            "locked": "yes",
            "checked_on": "2026-07-01",
            "checked_by": "Pマーク担当 山田",
            "check_method": "現地確認",
            "evidence": "2026年度 保管場所施錠確認記録",
        },
    )
    assert "全体進捗：1 / 4 工程 完了" in response.text
    assert "現在地：2. 持出しルール" in response.text
    assert 'name="rule"' in response.text
    assert 'name="confirmed_on"' not in response.text

    response = client.post(
        "/paper/actions/define-take-out-rule",
        data={
            "rule": "持出し台帳へ記録し、個人情報保護管理者の許可を得る。",
            "defined_on": "2026-07-02",
            "defined_by": "Pマーク担当 山田",
        },
    )
    assert "全体進捗：2 / 4 工程 完了" in response.text
    assert "現在地：3. 廃棄確認" in response.text
    assert 'name="confirmed_on"' in response.text
    assert 'name="approved_by"' not in response.text

    response = client.post(
        "/paper/actions/confirm-disposal",
        data={
            "disposal_method": "溶解処理業者による溶解処理",
            "confirmed": "yes",
            "confirmed_on": "2026-07-03",
            "confirmed_by": "Pマーク担当 山田",
            "evidence": "2026年度 溶解処理証明書",
        },
    )
    assert "全体進捗：3 / 4 工程 完了" in response.text
    assert "現在地：4. 実施結果の承認" in response.text
    assert 'name="approved_by"' in response.text

    response = client.post(
        "/paper/actions/approve",
        data={
            "approved_by": "個人情報保護管理者 鈴木",
            "approved_at": "2026-07-04",
        },
    )
    assert "全体進捗：4 / 4 工程 完了" in response.text
    assert "現在地：全工程完了" in response.text
    assert "必要な紙媒体管理記録は登録済みです" in response.text
    assert "適合" in response.text

    status = paper_demo_state.get_state().status
    assert status.storage_location == "総務部 鍵付きキャビネット"
    assert status.storage_lock_checked_on == "2026-07-01"
    assert status.storage_lock_checked_by == "Pマーク担当 山田"
    assert status.storage_lock_check_method == "現地確認"
    assert status.storage_lock_evidence == "2026年度 保管場所施錠確認記録"
    assert status.take_out_rule == "持出し台帳へ記録し、個人情報保護管理者の許可を得る。"
    assert status.take_out_rule_defined_on == "2026-07-02"
    assert status.disposal_confirmed_on == "2026-07-03"
    assert status.disposal_evidence == "2026年度 溶解処理証明書"
    assert status.approved_by == "個人情報保護管理者 鈴木"
    assert status.approved_at == "2026-07-04"


def test_resolving_all_issues_results_in_compliant():
    client.post("/paper/actions/confirm-storage-lock")
    client.post("/paper/actions/define-take-out-rule")
    client.post("/paper/actions/confirm-disposal")
    response = client.post("/paper/actions/approve")

    assert response.status_code == 200
    assert "適合" in response.text
    assert "要対応" not in response.text
    assert "PAP-001" not in response.text


def test_reset_restores_initial_state():
    client.post("/paper/actions/confirm-storage-lock")
    client.post("/paper/actions/define-take-out-rule")
    client.post("/paper/actions/confirm-disposal")
    client.post("/paper/actions/approve")

    response = client.post("/paper/reset")

    assert response.status_code == 200
    assert "要対応" in response.text
    assert "PAP-001" in response.text
