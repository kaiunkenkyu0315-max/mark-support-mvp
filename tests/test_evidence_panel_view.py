from app.evidence_panel_view import render_evidence_panel


def test_empty_evidence_panel_still_shows_common_metadata_columns():
    html = render_evidence_panel(
        area="vendor_management",
        files=[],
        description="委託先管理の証跡です。",
        canonical_record_text="画面上の評価記録が正本です。",
    )

    assert "対象領域" in html
    assert "年度" in html
    assert "登録日" in html
    assert "ファイル名" in html
    assert "添付済みの証跡ファイルはありません" in html
