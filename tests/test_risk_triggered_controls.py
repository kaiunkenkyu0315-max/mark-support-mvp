"""RISK-001/RISK-002の確認から、アクセス権限管理・紙媒体管理の管理策候補提示〜
採用〜運用〜文書生成までがつながっていることを検証するテスト。

管理策の採用可否（adopted/not_applicable）の正本は、既存どおりsetup側の
ControlSuggestion.statusのみであることも合わせて確認する。
"""

import pytest
from fastapi.testclient import TestClient

from app import (
    access_control_demo_state,
    demo_state,
    intake_demo_state,
    paper_demo_state,
    vendor_demo_state,
)
from app.intake_schemas import ControlDecisionStatus
from app.main import app
from app.risk_schemas import RiskCandidateStatus

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_all_state():
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


def _submit_answers(**overrides):
    form = {
        "has_employees": "no",
        "recruits_people": "no",
        "manages_customer_contacts": "no",
        "receives_inquiries": "no",
        "outsources_personal_data_processing": "no",
        "uses_external_cloud_services": "no",
        "stores_personal_data_on_paper": "no",
        "allows_remote_access": "no",
    }
    for field, value in overrides.items():
        form[field] = "yes" if value else "no"
    client.post("/setup/answers", data=form)


def _confirm_risk(risk_id: str) -> None:
    risk = next(r for r in intake_demo_state.get_state().risks if r.risk_id == risk_id)
    client.post(f"/setup/risks/{risk.id}/confirm")


# --- 1. RISK-001 confirmed → アクセス権限管理をsuggest ---


def test_risk001_confirmed_suggests_access_control():
    _submit_answers(uses_external_cloud_services=True)

    suggestions_before = intake_demo_state.get_state().control_suggestions
    assert not any(s.control_id == "access_control" for s in suggestions_before)

    _confirm_risk("RISK-001")

    suggestions_after = intake_demo_state.get_state().control_suggestions
    access_control = next(s for s in suggestions_after if s.control_id == "access_control")
    assert access_control.status == ControlDecisionStatus.SUGGESTED


def test_risk001_candidate_alone_does_not_suggest_access_control():
    _submit_answers(uses_external_cloud_services=True)

    suggestions = intake_demo_state.get_state().control_suggestions
    risk = next(r for r in intake_demo_state.get_state().risks if r.risk_id == "RISK-001")
    assert risk.status == RiskCandidateStatus.CANDIDATE
    assert not any(s.control_id == "access_control" for s in suggestions)


# --- 2. RISK-002 confirmed → 紙媒体管理をsuggest ---


def test_risk002_confirmed_suggests_paper_management():
    _submit_answers(stores_personal_data_on_paper=True)

    suggestions_before = intake_demo_state.get_state().control_suggestions
    assert not any(s.control_id == "paper_management" for s in suggestions_before)

    _confirm_risk("RISK-002")

    suggestions_after = intake_demo_state.get_state().control_suggestions
    paper_management = next(s for s in suggestions_after if s.control_id == "paper_management")
    assert paper_management.status == ControlDecisionStatus.SUGGESTED


# --- 3. suggestionだけではadoptedにならない ---


def test_confirming_risk_alone_does_not_adopt_control():
    _submit_answers(uses_external_cloud_services=True, stores_personal_data_on_paper=True)

    _confirm_risk("RISK-001")
    _confirm_risk("RISK-002")

    suggestions = intake_demo_state.get_state().control_suggestions
    access_control = next(s for s in suggestions if s.control_id == "access_control")
    paper_management = next(s for s in suggestions if s.control_id == "paper_management")
    assert access_control.status == ControlDecisionStatus.SUGGESTED
    assert paper_management.status == ControlDecisionStatus.SUGGESTED


# --- 4. setupでadoptすると運用・文書へ反映 ---


def test_adopting_access_control_reflects_in_operation_page_and_document():
    _submit_answers(uses_external_cloud_services=True)
    _confirm_risk("RISK-001")
    client.post("/setup/controls/access_control/adopt")

    operation_response = client.get("/access-control")
    assert "採用済み" in operation_response.text

    document_response = client.get("/documents/access_control_procedure")
    assert "準備完了" in document_response.text
    assert "未生成" not in document_response.text


def test_adopting_paper_management_reflects_in_operation_page_and_document():
    _submit_answers(stores_personal_data_on_paper=True)
    _confirm_risk("RISK-002")
    client.post("/setup/controls/paper_management/adopt")

    operation_response = client.get("/paper")
    assert "採用済み" in operation_response.text

    document_response = client.get("/documents/paper_management_procedure")
    assert "準備完了" in document_response.text
    assert "未生成" not in document_response.text


# --- 5. not_applicableなら正式文書生成対象外 ---


def test_access_control_not_applicable_does_not_generate_document():
    _submit_answers(uses_external_cloud_services=True)
    _confirm_risk("RISK-001")
    client.post(
        "/setup/controls/access_control/not-applicable",
        data={"reason": "対象システムがないため"},
    )

    response = client.get("/documents/access_control_procedure")

    assert "未生成" in response.text
    assert "対象システムがないため" in response.text
    assert "準備完了" not in response.text


def test_paper_management_not_applicable_does_not_generate_document():
    _submit_answers(stores_personal_data_on_paper=True)
    _confirm_risk("RISK-002")
    client.post(
        "/setup/controls/paper_management/not-applicable",
        data={"reason": "紙媒体を廃止したため"},
    )

    response = client.get("/documents/paper_management_procedure")

    assert "未生成" in response.text
    assert "紙媒体を廃止したため" in response.text
    assert "準備完了" not in response.text


# --- 6・7. アクセス管理の不足検出・解消後の適合 ---


def test_access_control_page_shows_initial_shortage():
    response = client.get("/access-control")

    for rule_id in ("ACC-001", "ACC-002", "ACC-003", "ACC-004"):
        assert rule_id in response.text


def test_access_control_becomes_compliant_after_resolving_shortage():
    client.post("/access-control/actions/complete-account-reviews")
    client.post("/access-control/actions/remove-unnecessary-accounts")
    client.post("/access-control/actions/complete-review-cycle")
    response = client.post("/access-control/actions/approve-review-cycle")

    assert "適合" in response.text
    assert "要対応" not in response.text


# --- 8・9. 紙媒体管理の不足検出・解消後の適合 ---


def test_paper_page_shows_initial_shortage():
    response = client.get("/paper")

    for rule_id in ("PAP-001", "PAP-002", "PAP-003", "PAP-004"):
        assert rule_id in response.text


def test_paper_becomes_compliant_after_resolving_shortage():
    client.post("/paper/actions/confirm-storage-lock")
    client.post("/paper/actions/define-take-out-rule")
    client.post("/paper/actions/confirm-disposal")
    response = client.post("/paper/actions/approve")

    assert "適合" in response.text
    assert "要対応" not in response.text


# --- 10. 管理策採否のsource of truthがsetupに一本化されている ---


def test_access_control_page_does_not_contradict_setup_not_applicable_decision():
    _submit_answers(uses_external_cloud_services=True)
    _confirm_risk("RISK-001")
    client.post(
        "/setup/controls/access_control/not-applicable",
        data={"reason": "対象システムがないため"},
    )

    response = client.get("/access-control")

    assert "非適用" in response.text
    assert "採用済み" not in response.text


def test_paper_page_does_not_contradict_setup_not_applicable_decision():
    _submit_answers(stores_personal_data_on_paper=True)
    _confirm_risk("RISK-002")
    client.post(
        "/setup/controls/paper_management/not-applicable",
        data={"reason": "紙媒体を廃止したため"},
    )

    response = client.get("/paper")

    assert "非適用" in response.text
    assert "採用済み" not in response.text


def test_top_page_does_not_show_operating_status_for_unadopted_controls():
    """setupで未採用（未提示含む）の間は、トップページで「適合／要対応」のような
    運用中のステータスを表示せず、「未採用」であることが分かるようにする。"""

    response = client.get("/")

    assert "アクセス権限管理" in response.text
    assert "紙媒体管理" in response.text
    assert "未採用" in response.text


def test_top_page_shows_operating_status_once_adopted():
    _submit_answers(uses_external_cloud_services=True)
    _confirm_risk("RISK-001")
    client.post("/setup/controls/access_control/adopt")

    response = client.get("/")

    assert "要対応" in response.text
