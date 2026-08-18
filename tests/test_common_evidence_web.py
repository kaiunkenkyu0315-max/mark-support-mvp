import pytest
from fastapi.testclient import TestClient

from app import (
    access_control_demo_state,
    application_prep_demo_state,
    company_profile,
    demo_state,
    intake_demo_state,
    paper_demo_state,
    pms_review_demo_state,
    vendor_demo_state,
)
from app.main import app
from app.pms_review import evaluate_pms_review
from app.vendors import evaluate_vendors

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_states(tmp_path, monkeypatch):
    monkeypatch.setenv("MARK_SUPPORT_EVIDENCE_DIR", str(tmp_path / "evidence"))
    modules = (
        company_profile,
        intake_demo_state,
        demo_state,
        vendor_demo_state,
        access_control_demo_state,
        paper_demo_state,
        pms_review_demo_state,
        application_prep_demo_state,
    )
    for module in modules:
        module.reset_state()
    yield
    for module in modules:
        module.reset_state()


def _vendor_issue_count() -> int:
    state = vendor_demo_state.get_state()
    return len(
        evaluate_vendors(
            state.vendors,
            state.control,
            state.assessments,
            state.contracts,
        ).issues
    )


def test_vendor_evidence_uses_shared_metadata_and_does_not_change_evaluation():
    client.post("/dev/preset/operations")
    before = _vendor_issue_count()
    assert before > 0

    response = client.post(
        "/evidence/vendor_management/upload",
        files={"file": ("委託先評価票.pdf", b"vendor-evidence", "application/pdf")},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "委託先管理の証跡ファイルを添付しました" in response.text
    assert "対象領域" in response.text
    assert "年度" in response.text
    assert "登録日" in response.text
    assert "ファイル名" in response.text
    assert "委託先管理" in response.text
    assert "2026年度" in response.text
    assert "委託先評価票.pdf" in response.text
    assert _vendor_issue_count() == before


def test_internal_audit_and_management_review_have_separate_evidence_areas():
    client.post("/dev/preset/pms-review")
    before = evaluate_pms_review(pms_review_demo_state.get_state())
    assert before.complete is False

    audit = client.post(
        "/evidence/internal_audit/upload",
        files={"file": ("内部監査報告書.pdf", b"audit", "application/pdf")},
        follow_redirects=True,
    )
    assert audit.status_code == 200
    assert "内部監査の証跡ファイル" in audit.text
    assert "マネジメントレビューの証跡ファイル" in audit.text
    assert "内部監査報告書.pdf" in audit.text
    assert "2026年度" in audit.text

    management = client.post(
        "/evidence/management_review/upload",
        files={"file": ("マネジメントレビュー議事録.pdf", b"mr", "application/pdf")},
        follow_redirects=True,
    )
    assert management.status_code == 200
    assert "内部監査報告書.pdf" in management.text
    assert "マネジメントレビュー議事録.pdf" in management.text

    after = evaluate_pms_review(pms_review_demo_state.get_state())
    assert after.audit_complete == before.audit_complete
    assert after.management_review_complete == before.management_review_complete
    assert after.complete == before.complete
