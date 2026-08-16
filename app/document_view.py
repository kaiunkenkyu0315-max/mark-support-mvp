"""文書一覧・文書プレビュー画面のHTML描画。

ここでは文書の組み立て（テンプレートへの事実データの当てはめ・状態判定）を
一切行わない。app.documents が組み立てた Document をそのまま表示するだけとする。
"""

from __future__ import annotations

from app.document_schemas import Document, DocumentSection, DocumentStatus, DocumentTable
from app.documents import CONTROL_NAME_LABELS

DOCUMENT_STATUS_LABELS = {
    DocumentStatus.DRAFT: "下書き（情報不足）",
    DocumentStatus.READY: "準備完了",
    DocumentStatus.NOT_APPLICABLE: "未生成（管理策未採用）",
}

DOCUMENT_STATUS_CSS_CLASS = {
    DocumentStatus.DRAFT: "needs-action",
    DocumentStatus.READY: "compliant",
    DocumentStatus.NOT_APPLICABLE: "not-started",
}


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _related_control_names(document: Document) -> str:
    if not document.related_control_ids:
        return "（特定の管理策には紐づきません）"
    return "、".join(
        _escape(CONTROL_NAME_LABELS.get(control_id, control_id))
        for control_id in document.related_control_ids
    )


def _render_missing_fields(document: Document) -> str:
    if not document.missing_fields:
        return ""
    items = "".join(f"<li>{_escape(text)}</li>" for text in document.missing_fields)
    return f"""
    <div class="missing-fields">
      <p class="missing-fields-title">⚠ 以下の情報が不足しています：</p>
      <ul>{items}</ul>
    </div>
    """


def _render_table(table: DocumentTable) -> str:
    header_html = "".join(f"<th>{_escape(header)}</th>" for header in table.headers)
    rows_html = "".join(
        "<tr>" + "".join(f"<td>{_escape(cell)}</td>" for cell in row) + "</tr>"
        for row in table.rows
    )
    return f"""
    <table class="records-table">
      <thead><tr>{header_html}</tr></thead>
      <tbody>{rows_html}</tbody>
    </table>
    """


def _render_section(section: DocumentSection) -> str:
    paragraphs_html = "".join(f"<p>{_escape(text)}</p>" for text in section.paragraphs)
    table_html = _render_table(section.table) if section.table else ""
    return f"""
    <div class="document-section">
      <h3>{_escape(section.heading)}</h3>
      {paragraphs_html}
      {table_html}
    </div>
    """


def _render_body(document: Document) -> str:
    if not document.sections:
        return '<p class="document-empty">本文はまだ生成されていません。</p>'
    return "".join(_render_section(section) for section in document.sections)


# ---------------------------------------------------------------------------
# 文書一覧
# ---------------------------------------------------------------------------


def _render_document_list_item(document: Document) -> str:
    status_label = DOCUMENT_STATUS_LABELS[document.status]
    status_class = DOCUMENT_STATUS_CSS_CLASS[document.status]
    return f"""
    <li class="document-item">
      <p class="document-name">{_escape(document.title)}</p>
      <p class="document-related">関連する管理策：{_related_control_names(document)}</p>
      <p>状態：<span class="status-badge {status_class}">{status_label}</span></p>
      <p><a href="/documents/{document.document_id}">確認する</a></p>
    </li>
    """


def render_document_list_page(documents: list[Document]) -> str:
    items = "".join(_render_document_list_item(document) for document in documents)

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <title>文書管理 - Pマーク取得・運用支援ツール MVP</title>
  <style>
    body {{ font-family: sans-serif; margin: 2rem; line-height: 1.6; max-width: 900px; }}
    h1 {{ margin-bottom: 0.5rem; }}
    .preview-disclaimer {{
      padding: 0.6rem 1rem; margin-bottom: 1.5rem; border-radius: 4px;
      background: #eef5fc; border-left: 4px solid #0a4a8a; color: #333; font-size: 0.9rem;
    }}
    .document-list {{ list-style: none; margin: 0; padding: 0; }}
    .document-item {{
      padding: 0.75rem 1rem; margin-bottom: 0.75rem; border-radius: 4px;
      background: #f5f5f5; border-left: 4px solid #888;
    }}
    .document-name {{ font-weight: bold; margin: 0 0 0.3rem; font-size: 1.1rem; }}
    .document-related {{ margin: 0 0 0.5rem; color: #555; }}
    .status-badge {{ display: inline-block; padding: 0.2rem 0.6rem; border-radius: 4px; color: #fff; }}
    .status-badge.not-started {{ background: #666; }}
    .status-badge.needs-action {{ background: #b30000; }}
    .status-badge.compliant {{ background: #0a7a0a; }}
  </style>
</head>
<body>
  <p><a href="/">&laquo; トップへ戻る</a></p>
  <h1>文書管理（PMS文書）</h1>
  <p>個人情報管理台帳・教育手順・委託先管理手順など、管理策に対応するPMS文書の一覧です。
  企業情報・確認済み個人情報・採用済み管理策から、標準テンプレートに基づいて構成しています。
  AIによる自由作文は行っていません。</p>
  <div class="preview-disclaimer">
    現在の登録情報から生成した文書プレビューです。正式なWord／PDFファイルの保存や、
    承認・版管理の機能は今後対応予定です。
  </div>
  <ul class="document-list">{items}</ul>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# 文書プレビュー
# ---------------------------------------------------------------------------


def render_document_detail_page(document: Document) -> str:
    status_label = DOCUMENT_STATUS_LABELS[document.status]
    status_class = DOCUMENT_STATUS_CSS_CLASS[document.status]

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <title>{_escape(document.title)} - Pマーク取得・運用支援ツール MVP</title>
  <style>
    body {{ font-family: sans-serif; margin: 2rem; line-height: 1.6; max-width: 900px; }}
    h1 {{ margin-bottom: 0.5rem; }}
    .preview-disclaimer {{
      padding: 0.6rem 1rem; margin-bottom: 1rem; border-radius: 4px;
      background: #eef5fc; border-left: 4px solid #0a4a8a; color: #333; font-size: 0.9rem;
    }}
    .document-meta {{ padding: 1rem; border: 1px solid #ccc; border-radius: 4px; margin-bottom: 1.5rem; }}
    .status-badge {{ display: inline-block; padding: 0.2rem 0.6rem; border-radius: 4px; color: #fff; }}
    .status-badge.not-started {{ background: #666; }}
    .status-badge.needs-action {{ background: #b30000; }}
    .status-badge.compliant {{ background: #0a7a0a; }}
    .missing-fields {{
      padding: 0.75rem 1rem; margin-bottom: 1.5rem; border-radius: 4px;
      background: #fff8ef; border-left: 4px solid #d9822b;
    }}
    .missing-fields-title {{ font-weight: bold; margin: 0 0 0.3rem; }}
    .document-body {{ border-top: 1px solid #ccc; padding-top: 1rem; }}
    .document-section {{ margin-bottom: 1.5rem; }}
    .document-section h3 {{ margin-bottom: 0.3rem; }}
    .document-empty {{ color: #777; }}
    .records-table {{ border-collapse: collapse; }}
    .records-table th, .records-table td {{ text-align: left; border: 1px solid #ccc; padding: 4px 8px; }}
  </style>
</head>
<body>
  <p><a href="/documents">&laquo; 文書管理へ戻る</a></p>
  <h1>{_escape(document.title)}</h1>
  <div class="preview-disclaimer">
    現在の登録情報から生成した文書プレビューです。正式版の保存・承認・版管理は今後対応予定です。
  </div>

  <div class="document-meta">
    <p>状態：<span class="status-badge {status_class}">{status_label}</span></p>
    <p>関連する管理策：{_related_control_names(document)}</p>
  </div>

  {_render_missing_fields(document)}

  <div class="document-body">
    {_render_body(document)}
  </div>
</body>
</html>
"""
