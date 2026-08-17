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


def test_application_prep_starts_with_destination_only():
    load_application_prep_preset()

    response = client.get("/application-prep")

    assert response.status_code == 200
    assert "申請準備の全体工程" in response.text
    assert "全体進捗：0 / 4 工程 完了" in response.text
    assert "現在地：1. 申請先・方法" in response.text
    assert 'action="/application-prep/destination"' in response.text
    assert 'action="/application-prep/forms"' not in response.text
    assert 'action="/application-prep/submission-data"' not in response.text
    assert 'action="/application-prep/final-review"' not in response.text


def test_jipdec_online_flow_progresses_through_all_four_steps():
    load_application_prep_preset()

    response = client.post(
        "/application-prep/destination",
        data={
            "examining_body_name": "JIPDEC",
            "application_method": "online",
            "uses_jipdec_forms": "yes",
        },
        follow_redirects=True,
    )
    assert "現在地：2. 申請書類・前提確認" in response.text
    assert "申請様式4：個人情報を取扱う業務の概要" in response.text
    assert "申請様式8：内部監査・マネジメントレビュー実施サマリー" in response.text
    assert "会社・PMS基本情報：<strong>準備完了" in response.text
    assert "内部監査・是正・マネジメントレビュー：<strong>準備完了" in response.text

    response = client.post(
        "/application-prep/forms",
        data={
            "business_overview_prepared": "yes",
            "office_list_prepared": "yes",
            "pms_document_list_prepared": "yes",
            "education_summary_prepared": "yes",
            "audit_mr_summary_prepared": "yes",
        },
        follow_redirects=True,
    )
    assert "現在地：3. 提出データ・アカウント" in response.text
    assert "オンライン申請に使用するアカウントを準備した" in response.text

    response = client.post(
        "/application-prep/submission-data",
        data={
            "pms_document_bundle_prepared": "yes",
            "online_account_ready": "yes",
        },
        follow_redirects=True,
    )
    assert "現在地：4. 最終確認" in response.text
    assert "山田 花子" in response.text

    response = client.post(
        "/application-prep/final-review",
        data={
            "final_reviewed_by": "山田 花子",
            "final_reviewed_at": "2026-08-10",
            "submission_ready_confirmed": "yes",
        },
        follow_redirects=True,
    )
    assert "全体進捗：4 / 4 工程 完了" in response.text
    assert "現在地：全工程完了" in response.text
    assert "申請提出前の準備確認が完了しました" in response.text
    assert "付与適格性を保証するものではありません" in response.text


def test_non_jipdec_mail_flow_uses_examining_body_form_set_and_no_online_account():
    load_application_prep_preset()
    client.post(
        "/application-prep/destination",
        data={
            "examining_body_name": "指定審査機関A",
            "application_method": "mail",
            "uses_jipdec_forms": "no",
        },
    )

    response = client.get("/application-prep")
    assert "申請先が指定する新規申請様式一式" in response.text
    assert "申請様式4：" not in response.text

    response = client.post(
        "/application-prep/forms",
        data={"other_form_set_prepared": "yes"},
        follow_redirects=True,
    )
    assert "現在地：3. 提出データ・アカウント" in response.text
    assert "オンライン申請に使用するアカウント" not in response.text

    response = client.post(
        "/application-prep/submission-data",
        data={"pms_document_bundle_prepared": "yes"},
        follow_redirects=True,
    )
    assert "現在地：4. 最終確認" in response.text


def test_later_application_steps_cannot_be_posted_before_prerequisites():
    load_application_prep_preset()

    response = client.post(
        "/application-prep/submission-data",
        data={"pms_document_bundle_prepared": "yes", "online_account_ready": "yes"},
        follow_redirects=True,
    )
    assert "先に申請先と申請様式の準備を完了してください" in response.text
    assert application_prep_demo_state.get_state().pms_document_bundle_prepared is False

    response = client.post(
        "/application-prep/final-review",
        data={
            "final_reviewed_by": "山田 花子",
            "final_reviewed_at": "2026-08-10",
            "submission_ready_confirmed": "yes",
        },
        follow_redirects=True,
    )
    assert "先行する準備を完了してください" in response.text
    assert application_prep_demo_state.get_state().submission_ready_confirmed is False
