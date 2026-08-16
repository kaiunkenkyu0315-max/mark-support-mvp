import pytest
from fastapi.testclient import TestClient

from app import intake_demo_state, vendor_demo_state
from app.intake_schemas import ControlDecisionStatus, ControlSuggestion
from app.main import app
from app.vendor_schemas import AssessmentResult

client = TestClient(app)


def _adopt_vendor_control() -> None:
    intake_demo_state.get_state().control_suggestions.append(
        ControlSuggestion(
            control_id="vendor_management",
            name="委託先管理",
            reason="テスト用",
            status=ControlDecisionStatus.ADOPTED,
            link_url="/vendors",
        )
    )


@pytest.fixture(autouse=True)
def reset_vendor_state():
    """各テストを、委託先管理策が採用済みの運用状態から開始する。"""

    intake_demo_state.reset_state()
    _adopt_vendor_control()
    vendor_demo_state.reset_state()
    yield
    intake_demo_state.reset_state()
    vendor_demo_state.reset_state()


def test_vendors_page_returns_200():
    response = client.get("/vendors")

    assert response.status_code == 200


def test_vendors_page_shows_all_three_vendors():
    response = client.get("/vendors")

    assert "給与計算会社" in response.text
    assert "採用管理クラウド" in response.text
    assert "機密文書廃棄会社" in response.text


def test_initial_state_is_needs_action():
    response = client.get("/vendors")

    assert "要対応" in response.text


def test_initial_state_shows_expected_issue_rules():
    response = client.get("/vendors")

    for rule_id in ("VEN-001", "VEN-002", "VEN-004"):
        assert rule_id in response.text


def test_vendor_overview_shows_all_steps_but_only_current_record_form():
    response = client.get("/vendors")

    assert "委託先管理の全体工程" in response.text
    assert "全体進捗：0 / 3 工程 完了" in response.text
    assert "<strong>初回評価</strong>" in response.text
    assert "<strong>契約確認</strong>" in response.text
    assert "<strong>定期評価</strong>" in response.text
    assert "2 / 3社 適格確認済み" in response.text
    assert "2 / 3社 確認済み" in response.text
    assert "2 / 3社 有効" in response.text
    assert "現在地：1. 初回評価" in response.text
    assert "今やること" in response.text
    assert "1件" in response.text

    # <ol>側の番号と工程名の番号を二重表示しない。
    assert "1. 1. 初回評価" not in response.text
    assert "2. 2. 契約確認" not in response.text
    assert "3. 3. 定期評価" not in response.text

    # 上部サマリーは「何の評価か」を明示する。
    assert "初回評価済み：2社" in response.text
    assert "初回評価未実施：1社" in response.text

    # 現在工程の初回評価フォームだけを表示する。
    assert 'name="assessment_date"' in response.text
    assert 'name="assessor_name"' in response.text
    assert 'name="assessment_method"' in response.text
    assert 'name="assessment_result"' in response.text
    assert 'value="委託先初回評価票"' in response.text
    assert 'name="confirmed_on"' not in response.text
    assert "委託先定期評価票" not in response.text

    # 旧デモのワンクリック操作は通常画面に出さない。
    assert "評価済みにする" not in response.text
    assert "契約確認を完了する" not in response.text
    assert "定期評価を完了する" not in response.text


def test_vendor_records_advance_one_step_at_a_time_and_save_facts():
    response = client.post(
        "/vendors/actions/complete-initial-assessments",
        data={
            "assessment_date": "2026-06-10",
            "assessor_name": "Pマーク担当 山田",
            "assessment_method": "資料確認",
            "assessment_result": "passed",
            "evidence_name": "2026年度 委託先初回評価票",
        },
    )
    assert "全体進捗：1 / 3 工程 完了" in response.text
    assert "現在地：2. 契約確認" in response.text
    assert 'name="confirmed_on"' in response.text
    assert 'name="assessment_result"' not in response.text

    response = client.post(
        "/vendors/actions/confirm-contracts",
        data={
            "confirmed_on": "2026-06-11",
            "confirmed_by": "Pマーク担当 山田",
            "contract_reference": "機密保持・個人情報取扱条項付き業務委託契約書",
        },
    )
    assert "全体進捗：2 / 3 工程 完了" in response.text
    assert "現在地：3. 定期評価" in response.text
    assert 'name="assessment_result"' in response.text
    assert "委託先定期評価票" in response.text
    assert 'name="confirmed_on"' not in response.text

    response = client.post(
        "/vendors/actions/complete-periodic-assessments",
        data={
            "assessment_date": "2026-06-12",
            "assessor_name": "Pマーク担当 山田",
            "assessment_method": "ヒアリング",
            "assessment_result": "passed",
            "evidence_name": "2026年度 委託先定期評価票",
        },
    )
    assert "全体進捗：3 / 3 工程 完了" in response.text
    assert "現在地：全工程完了" in response.text
    assert "必要な委託先管理記録は登録済みです" in response.text
    assert "適合" in response.text

    state = vendor_demo_state.get_state()
    disposal = next(
        item for item in state.assessments if item.vendor_id == vendor_demo_state.VENDOR_DISPOSAL
    )
    recruiting_contract = next(
        item for item in state.contracts if item.vendor_id == vendor_demo_state.VENDOR_RECRUITING
    )

    assert disposal.initial_assessment_date.isoformat() == "2026-06-10"
    assert disposal.initial_assessment_result == AssessmentResult.PASSED
    assert disposal.initial_assessment_by == "Pマーク担当 山田"
    assert disposal.initial_assessment_method == "資料確認"
    assert disposal.initial_assessment_evidence == "2026年度 委託先初回評価票"
    assert recruiting_contract.confirmed_on.isoformat() == "2026-06-11"
    assert recruiting_contract.confirmed_by == "Pマーク担当 山田"
    assert recruiting_contract.contract_reference == "機密保持・個人情報取扱条項付き業務委託契約書"
    assert disposal.latest_assessment_date.isoformat() == "2026-06-12"
    assert disposal.assessment_result == AssessmentResult.PASSED
    assert disposal.periodic_assessment_by == "Pマーク担当 山田"
    assert disposal.periodic_assessment_method == "ヒアリング"
    assert disposal.periodic_assessment_evidence == "2026年度 委託先定期評価票"


def test_resolving_all_issues_results_in_compliant():
    client.post("/vendors/actions/complete-initial-assessments")
    client.post("/vendors/actions/confirm-contracts")
    response = client.post("/vendors/actions/complete-periodic-assessments")

    assert response.status_code == 200
    assert "適合" in response.text
    assert "要対応" not in response.text
    assert "VEN-001" not in response.text


def test_reset_restores_initial_state():
    client.post("/vendors/actions/complete-initial-assessments")
    client.post("/vendors/actions/confirm-contracts")
    client.post("/vendors/actions/complete-periodic-assessments")

    response = client.post("/vendors/reset")

    assert response.status_code == 200
    assert "要対応" in response.text
    assert "VEN-001" in response.text
