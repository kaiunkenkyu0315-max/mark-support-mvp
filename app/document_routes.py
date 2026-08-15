"""文書一覧・文書プレビュー画面のFastAPIルーティング。

HTTP処理（リクエスト受付・404判定）のみを担当する。文書の組み立ては
app.documents に、事実データの取得は既存の各デモ状態モジュール
（app.demo_state / app.intake_demo_state / app.vendor_demo_state）に委譲し、
ここでは業務判定を行わない。

文書はリクエストのたびに最新の事実データから組み立て直す（スナップショットの
保存は行わない）ため、元データを変更した後に再度アクセスすると、変更内容が
そのままプレビューに反映される。
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from app import demo_state, intake_demo_state, vendor_demo_state
from app.document_schemas import Document
from app.document_view import render_document_detail_page, render_document_list_page
from app.documents import build_all_documents

router = APIRouter(prefix="/documents", tags=["documents"])


def get_current_documents() -> list[Document]:
    """既存の各デモ状態から、現時点の文書一覧を組み立てる。"""

    intake_state = intake_demo_state.get_state()
    education_state = demo_state.get_state()
    vendor_state = vendor_demo_state.get_state()

    return build_all_documents(
        company=education_state.company,
        candidates=intake_state.candidates,
        control_suggestions=intake_state.control_suggestions,
        education_control=education_state.control,
        education_plan=education_state.plan,
        vendor_control=vendor_state.control,
    )


@router.get("", response_class=HTMLResponse)
def documents_page() -> str:
    return render_document_list_page(get_current_documents())


@router.get("/{document_id}", response_class=HTMLResponse)
def document_detail_page(document_id: str) -> str:
    document = next(
        (doc for doc in get_current_documents() if doc.document_id == document_id), None
    )
    if document is None:
        raise HTTPException(status_code=404, detail="文書が見つかりません")
    return render_document_detail_page(document)
