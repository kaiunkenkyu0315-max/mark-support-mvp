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
from app.dev_preset import load_application_prep_preset
from app.main import app


client = TestClient(app)


def _reset_all() -> None:
    company_profile.reset_state()
    intake_demo_state.reset_state()
    demo_state.reset_state()
    vendor_demo_state.reset_state()
    access_control_demo_state.reset_state()
    paper_demo_state.reset_state()
    pms_review_demo_state.reset_state()
    application_prep_demo_state.reset_state()


def setup_function():
    _reset_all()


def teardown_function():
    _reset_all()


def _complete_application_prep() -> None:
    load_application_prep_preset()
    application_prep_demo_state.record_destination(
        eligibility_confirmed=True,
        examining_body_name="JIPDEC",
        application_method="online",
        uses_jipdec_forms=True,
    )
    application_prep_demo_state.record_forms(
        business_overview_prepared=True,
        office_list_prepared=True,
        pms_document_list_prepared=True,
        education_summary_prepared=True,
        audit_mr_summary_prepared=True,
    )
    application_prep_demo_state.record_submission_data(
        pms_document_bundle_prepared=True,
        online_account_ready=True,
    )
    application_prep_demo_state.record_final_review(
        final_reviewed_by="山田 花子",
        final_reviewed_at="2026-08-10",
        submission_ready_confirmed=True,
    )


def test_goal_summary_is_hidden_until_application_prep_is_complete():
    load_application_prep_preset()

    response = client.get("/application-prep")

    assert response.status_code == 200
    assert "申請提出前の準備が整いました" not in response.text
    assert "申請準備サマリー" not in response.text


def test_completed_application_prep_shows_goal_summary_and_external_next_step():
    _complete_application_prep()

    response = client.get("/application-prep")

    assert response.status_code == 200
    assert "申請提出前の準備が整いました" in response.text
    assert "申請準備 4 / 4 工程 完了" in response.text
    assert "申請準備サマリー" in response.text
    assert "JIPDEC" in response.text
    assert "オンライン" in response.text
    assert "JIPDEC 新規申請様式（オンライン）" in response.text
    assert "4 / 4 項目 確認済み" in response.text
    assert "山田 花子" in response.text
    assert "2026-08-10" in response.text
    assert "次は、審査機関への実際の申請・審査です" in response.text
    assert "Pマークの付与適格性・認定・取得を保証するものではありません" in response.text
    assert "Pマーク取得完了" not in response.text
