"""教育管理画面へ共通証跡パネルを追加する薄い表示層。"""

from __future__ import annotations

from app.evidence_panel_view import append_evidence_panel, render_evidence_panel
from app.evidence_store import EvidenceFile


def render_education_evidence_panel(files: list[EvidenceFile]) -> str:
    return render_evidence_panel(
        area="education",
        files=files,
        description="教育資料、受講記録、理解度確認結果、承認記録などの実ファイルを補足証跡として添付できます。",
        canonical_record_text="画面上の実施記録・受講記録・理解度確認・承認記録が正本です。",
    )


def enhance_education_with_evidence(html: str, files: list[EvidenceFile]) -> str:
    return append_evidence_panel(html, render_education_evidence_panel(files))
