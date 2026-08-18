"""各業務画面へ共通の証跡ファイル添付パネルを追加する表示部品。"""

from __future__ import annotations

from html import escape

from app.evidence_store import EvidenceFile


AREA_LABELS = {
    "education": "教育管理",
    "vendor_management": "委託先管理",
    "internal_audit": "内部監査",
    "management_review": "マネジメントレビュー",
}


def _format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


def render_evidence_panel(
    *,
    area: str,
    files: list[EvidenceFile],
    description: str,
    canonical_record_text: str,
    heading: str = "証跡ファイル",
    completion_scope: str = "この業務工程",
) -> str:
    area_label = AREA_LABELS.get(area, area)
    if files:
        rows = "".join(
            f"""
            <tr>
              <td style="padding:6px;border-bottom:1px solid #ddd;">{escape(area_label)}</td>
              <td style="padding:6px;border-bottom:1px solid #ddd;">{escape(str(item.fiscal_year) + '年度' if item.fiscal_year is not None else '未設定')}</td>
              <td style="padding:6px;border-bottom:1px solid #ddd;">{escape(item.registered_on)}</td>
              <td style="padding:6px;border-bottom:1px solid #ddd;">
                <a href="/evidence/{escape(area)}/{escape(item.id)}">{escape(item.original_name)}</a>
                <span style="color:#666;">（{_format_size(item.size_bytes)}）</span>
              </td>
            </tr>
            """
            for item in files
        )
        existing = f"""
        <div style="overflow-x:auto;">
          <table style="border-collapse:collapse;width:100%;min-width:680px;">
            <thead><tr>
              <th style="text-align:left;padding:6px;border-bottom:2px solid #bbb;">対象領域</th>
              <th style="text-align:left;padding:6px;border-bottom:2px solid #bbb;">年度</th>
              <th style="text-align:left;padding:6px;border-bottom:2px solid #bbb;">登録日</th>
              <th style="text-align:left;padding:6px;border-bottom:2px solid #bbb;">ファイル名</th>
            </tr></thead>
            <tbody>{rows}</tbody>
          </table>
        </div>
        """
    else:
        existing = '<p style="color:#666;">添付済みの証跡ファイルはありません。</p>'

    return f"""
    <section class="evidence-panel" style="border:1px solid #ddd; padding:14px; margin:22px 0;">
      <h2 style="margin-top:0;">{escape(heading)}</h2>
      <p>{escape(description)}</p>
      <p style="background:#fff8ef; padding:.7rem 1rem;">
        <strong>ファイルを添付しただけでは、{escape(completion_scope)}の完了・適合にはなりません。</strong>
        {escape(canonical_record_text)}
      </p>
      {existing}
      <form method="post" action="/evidence/{escape(area)}/upload" enctype="multipart/form-data">
        <label>証跡ファイル
          <input type="file" name="file" required
                 accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.csv,.png,.jpg,.jpeg">
        </label>
        <button type="submit">証跡ファイルを添付</button>
      </form>
      <p style="color:#666;font-size:.9em;">1ファイル10MBまで。Office文書、PDF、画像、CSV・テキストに対応しています。</p>
    </section>
    """


def append_evidence_panel(html: str, panel: str) -> str:
    return html.replace("</body>", panel + "</body>", 1)
