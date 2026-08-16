"""利用者向け管理策ステータスの意味を固定する小規模テスト。"""

from app.control_status import operational_status
from app.intake_schemas import ControlDecisionStatus, ControlSuggestion


def test_control_without_suggestion_is_shown_as_not_suggested():
    label, css_class, note = operational_status(None, has_issues=True)

    assert label == "未提示"
    assert css_class == "not-started"
    assert "候補として提示されていません" in note
    assert "未採用" not in note


def test_suggested_control_remains_pending_decision():
    suggestion = ControlSuggestion(
        control_id="education",
        name="個人情報保護教育",
        reason="従業者が個人情報を取り扱うため",
        status=ControlDecisionStatus.SUGGESTED,
    )

    label, _, _ = operational_status(suggestion, has_issues=True)

    assert label == "採用判断待ち"
