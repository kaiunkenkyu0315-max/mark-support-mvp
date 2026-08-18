"""教育管理画面へ証跡ファイル添付パネルを追加する薄い表示層。"""

from __future__ import annotations

from html import escape

from app.evidence_store import EvidenceFile


def _format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


def render_education_evidence_panel(files: list[EvidenceFile]) -> str:
    if files:
        rows = "".join(
            f"""
            <li style="margin:.45rem 0;">
              <a href="/evidence/education/{escape(item.id)}">{escape(item.original_name)}</a>
              <span style="color:#666;">（{_format_size(item.size_bytes)}）</span>
            </li>
            """
            for item in files
        )
        existing = f"<ul>{rows}</ul>"
    else:
        existing = '<p style="color:#666;">添付済みの証跡ファイルはありません。</p>'

    return f"""
    <section id="education-evidence" style="border:1px solid #ddd; padding:14px; margin:22px 0;">
      <h2 style="margin-top:0;">証跡ファイル</h2>
      <p>教育資料、受講記録、理解度確認結果、承認記録などの実ファイルを補足証跡として添付できます。</p>
      <p style="background:#fff8ef; padding:.7rem 1rem;">
        <strong>ファイルを添付しただけでは、教育工程の完了・適合にはなりません。</strong>
        画面上の実施記録・受講記録・理解度確認・承認記録が正本です。
      </p>
      {existing}
      <form method="post" action="/evidence/education/upload" enctype="multipart/form-data">
        <label>証跡ファイル
          <input type="file" name="file" required
                 accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.csv,.png,.jpg,.jpeg">
        </label>
        <button type="submit">証跡ファイルを添付</button>
      </form>
      <p style="color:#666;font-size:.9em;">1ファイル10MBまで。Office文書、PDF、画像、CSV・テキストに対応しています。</p>
    </section>
    """


def enhance_education_with_evidence(html: str, files: list[EvidenceFile]) -> str:
    panel = render_education_evidence_panel(files)
    return html.replace("</body>", panel + "</body>", 1)
