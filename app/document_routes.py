"""文書一覧・文書プレビュー・Word出力のFastAPIルーティング。

文書の組み立ては app.documents に、Wordバイナリ生成は app.docx_export に委譲する。
出力可否は既存の文書状態・教育評価をそのまま利用し、別の業務判定基準は持たない。
"""

from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, Response

from app import access_control_demo_state, demo_state, intake_demo_state, paper_demo_state, vendor_demo_state
from app.document_schemas import Document, DocumentStatus, DocumentType
from app.document_view import render_document_detail_page, render_document_list_page
from app.documents import build_all_documents
from app.docx_export import (
    build_document_docx,
    build_education_record_docx,
    build_pms_document_list_docx,
)
from app.education import evaluate_training

router = APIRouter(prefix="/documents", tags=["documents"])

DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def get_current_documents() -> list[Document]:
    """既存の各デモ状態から、現時点の文書一覧を組み立てる。"""

    intake_state = intake_demo_state.get_state()
    education_state = demo_state.get_state()
    vendor_state = vendor_demo_state.get_state()
    access_control_state = access_control_demo_state.get_state()
    paper_state = paper_demo_state.get_state()

    return build_all_documents(
        company=education_state.company,
        candidates=intake_state.candidates,
        control_suggestions=intake_state.control_suggestions,
        education_control=education_state.control,
        education_plan=education_state.plan,
        vendor_control=vendor_state.control,
        access_control=access_control_state.control,
        access_review_cycle=access_control_state.cycle,
        paper_control=paper_state.control,
        paper_status=paper_state.status,
    )


def _education_record_ready() -> bool:
    state = demo_state.get_state()
    return not evaluate_training(
        state.employees,
        state.control,
        state.plan,
        state.records,
    ).issues


def _docx_download(content: bytes, filename: str) -> Response:
    encoded = quote(filename)
    return Response(
        content=content,
        media_type=DOCX_MEDIA_TYPE,
        headers={
            "Content-Disposition": (
                f'attachment; filename="pmark-document.docx"; filename*=UTF-8\'\'{encoded}'
            )
        },
    )


@router.get("", response_class=HTMLResponse)
def documents_page() -> str:
    return render_document_list_page(
        get_current_documents(),
        education_record_ready=_education_record_ready(),
    )


@router.get("/export/personal-information-ledger.docx")
def export_personal_information_ledger() -> Response:
    document = next(
        (
            doc
            for doc in get_current_documents()
            if doc.document_type == DocumentType.PERSONAL_INFORMATION_LEDGER
        ),
        None,
    )
    if document is None or document.status != DocumentStatus.READY:
        raise HTTPException(
            status_code=409,
            detail="個人情報管理台帳の必須情報を整えてからWord出力してください。",
        )
    return _docx_download(build_document_docx(document), "個人情報管理台帳.docx")


@router.get("/export/education-record.docx")
def export_education_record() -> Response:
    if not _education_record_ready():
        raise HTTPException(
            status_code=409,
            detail="教育実施・受講・理解度確認・承認の記録を完了してからWord出力してください。",
        )
    state = demo_state.get_state()
    return _docx_download(
        build_education_record_docx(state),
        f"{state.plan.fiscal_year}年度_個人情報保護教育実施記録.docx",
    )


@router.get("/export/pms-document-list.docx")
def export_pms_document_list() -> Response:
    return _docx_download(
        build_pms_document_list_docx(get_current_documents()),
        "PMS文書一覧.docx",
    )


@router.get("/{document_id}", response_class=HTMLResponse)
def document_detail_page(document_id: str) -> str:
    document = next(
        (doc for doc in get_current_documents() if doc.document_id == document_id), None
    )
    if document is None:
        raise HTTPException(status_code=404, detail="文書が見つかりません")
    return render_document_detail_page(document)
