from io import BytesIO
from zipfile import ZipFile

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
from app.dev_preset import load_operational_review_preset, load_pms_review_preset
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_states():
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


def _document_xml(response) -> str:
    assert response.content.startswith(b"PK")
    with ZipFile(BytesIO(response.content)) as archive:
        assert "[Content_Types].xml" in archive.namelist()
        assert "word/document.xml" in archive.namelist()
        return archive.read("word/document.xml").decode("utf-8")


def test_documents_page_exposes_three_representative_word_exports():
    load_operational_review_preset()

    response = client.get("/documents")

    assert response.status_code == 200
    assert "実ファイル出力" in response.text
    assert '/documents/export/personal-information-ledger.docx' in response.text
    assert "教育の4工程完了後に出力できます" in response.text
    assert '/documents/export/pms-document-list.docx' in response.text


def test_personal_information_ledger_exports_as_valid_docx_when_ready():
    load_operational_review_preset()

    response = client.get("/documents/export/personal-information-ledger.docx")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    xml = _document_xml(response)
    assert "個人情報管理台帳" in xml
    assert "株式会社サンプル" in xml


def test_education_record_is_blocked_until_education_is_complete_then_exports_docx():
    load_operational_review_preset()

    blocked = client.get("/documents/export/education-record.docx")
    assert blocked.status_code == 409

    load_pms_review_preset()
    response = client.get("/documents/export/education-record.docx")

    assert response.status_code == 200
    xml = _document_xml(response)
    assert "個人情報保護教育 実施記録" in xml
    assert "教育実施概要" in xml
    assert "受講・理解度確認記録" in xml
    assert "山田 花子" in xml


def test_pms_document_list_exports_current_document_statuses_as_docx():
    load_operational_review_preset()

    response = client.get("/documents/export/pms-document-list.docx")

    assert response.status_code == 200
    xml = _document_xml(response)
    assert "PMS文書一覧" in xml
    assert "個人情報管理台帳" in xml
    assert "個人情報保護教育手順" in xml
    assert "委託先管理手順" in xml
