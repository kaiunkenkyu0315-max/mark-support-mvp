"""文書一覧・文書プレビュー画面のHTML描画。

ここでは文書の組み立て（テンプレートへの事実データの当てはめ・状態判定）を
一切行わない。app.documents が組み立てた Document をそのまま表示するだけとする。
"""

from __future__ import annotations

from app.document_schemas import (
    Document,
    DocumentSection,
    DocumentStatus,
    DocumentTable,
    DocumentType,
)
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


def _render_export_panel(
    documents: list[Document],
    *,
    education_record_ready: bool,
) -> str:
    ledger = next(
        (
            document
            for document in documents
            if document.document_type == DocumentType.PERSONAL_INFORMATION_LEDGER
        ),
        None,
    )
    ledger_ready = ledger is not None and ledger.status == DocumentStatus.READY

    ledger_action = (
        '<a class="export-button" href="/documents/export/personal-information-ledger.docx">Word出力</a>'
        if ledger_ready
        else '<span class="export-pending">台帳情報の準備完了後に出力できます</span>'
    )
    education_action = (
        '<a class="export-button" href="/documents/export/education-record.docx">Word出力</a>'
        if education_record_ready
        else '<span class="export-pending">教育の4工程完了後に出力できます</span>'
    )

    return f"""
    <section class="export-panel">
      <h2>実ファイル出力</h2>
      <p>登録した内容から、申請準備や社内確認に使えるWordファイルを生成します。</p>
      <div class="export-grid">
        <div class="export-card">
          <h3>個人情報管理台帳</h3>
          <p>確認済みの個人情報と管理方法を台帳として出力します。</p>
          {ledger_action}
        </div>
        <div class="export-card">
          <h3>教育実施記録</h3>
          <p>教育概要、受講状況、理解度確認、承認記録をまとめて出力します。</p>
          {education_action}
        </div>
        <div class="export-card">
          <h3>PMS文書一覧</h3>
          <p>現在生成されているPMS文書と準備状態を一覧として出力します。</p>
          <a class="export-button" href="/documents/export/pms-document-list.docx">Word出力</a>
        </div>
      </div>
      <p class="export-note">出力ファイルは現在の登録内容から生成されます。正式版として使用する際の承認・版管理は今後の製品化対象です。</p>
    </section>
    """


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


def render_document_list_page(
    documents: list[Document],
    *,
    education_record_ready: bool = False,
) -> str:
    items = "".join(_render_document_list_item(document) for document in documents)
    export_panel = _render_export_panel(
        documents,
        education_record_ready=education_record_ready,
    )

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <title>文書管理 - Pマーク取得・運用支援</title>
  <style>
    body {{ font-family: sans-serif; margin: 2rem; line-height: 1.6; max-width: 900px; }}
    h1 {{ margin-bottom: 0.5rem; }}
    .preview-disclaimer {{
      padding: 0.6rem 1rem; margin-bottom: 1.5rem; border-radius: 4px;
      background: #eef5fc; border-left: 4px solid #0a4a8a; color: #333; font-size: 0.9rem;
    }}
    .export-panel {{ border:1px solid #bbb; border-radius:6px; padding:1rem; margin:1.5rem 0; }}
    .export-panel h2 {{ margin-top:0; }}
    .export-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:1rem; }}
    .export-card {{ border:1px solid #ddd; border-radius:5px; padding:1rem; }}
    .export-card h3 {{ margin-top:0; }}
    .export-button {{ display:inline-block; padding:.45rem .8rem; border-radius:4px; background:#0a4a8a; color:#fff; text-decoration:none; font-weight:bold; }}
    .export-pending {{ color:#666; font-size:.9rem; }}
    .export-note {{ color:#666; font-size:.9rem; margin-bottom:0; }}
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
    画面上では現在の登録情報から生成した内容を確認できます。代表的な文書・記録はWordファイルとして出力できます。
    承認・版管理・改訂履歴は今後の製品化対象です。
  </div>
  {export_panel}
  <h2>文書プレビュー</h2>
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
    ledger_export = ""
    if (
        document.document_type == DocumentType.PERSONAL_INFORMATION_LEDGER
        and document.status == DocumentStatus.READY
    ):
        ledger_export = (
            '<p><a href="/documents/export/personal-information-ledger.docx">'
            'この台帳をWord出力</a></p>'
        )

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <title>{_escape(document.title)} - Pマーク取得・運用支援</title>
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
    現在の登録情報から生成した文書プレビューです。準備完了した代表文書はWord出力できます。承認・版管理は今後の製品化対象です。
  </div>

  <div class="document-meta">
    <p>状態：<span class="status-badge {status_class}">{status_label}</span></p>
    <p>関連する管理策：{_related_control_names(document)}</p>
    {ledger_export}
  </div>

  {_render_missing_fields(document)}

  <div class="document-body">
    {_render_body(document)}
  </div>
</body>
</html>
"""
