"""intakeフロー（業務ヒアリング〜管理策候補提示）のHTML描画。

ここでは業務判定（候補生成・管理策提示・回答変更時の再計算ルール）を
一切行わない。app.intake_demo_state が保持する事実・候補・確定状態を
そのまま表示するだけとする。UI側に「従業員あり→教育管理」のような
判定を書かない。
"""

from __future__ import annotations

from app.intake_demo_state import QUESTIONS, IntakeDemoState, is_setup_complete
from app.intake_schemas import (
    ControlDecisionStatus,
    ControlSuggestion,
    PersonalInformationCandidate,
    PersonalInformationCandidateStatus,
)

QUESTION_LABELS = dict(QUESTIONS)

CANDIDATE_STATUS_LABELS = {
    PersonalInformationCandidateStatus.CANDIDATE: "未確認（候補）",
    PersonalInformationCandidateStatus.CONFIRMED: "確認済み（取り扱っている）",
    PersonalInformationCandidateStatus.EXCLUDED: "除外（該当しない）",
}

CONTROL_STATUS_LABELS = {
    ControlDecisionStatus.SUGGESTED: "未採用（候補）",
    ControlDecisionStatus.ADOPTED: "採用済み",
    ControlDecisionStatus.NOT_APPLICABLE: "非適用",
}

# 採用済み管理策から、既存MVPへの導線ボタン文言。
CONTROL_LINK_LABELS = {
    "education": "教育管理へ進む",
    "vendor_management": "委託先管理へ進む",
}

STEPPER = [
    "STEP1 業務情報",
    "STEP2 個人情報候補",
    "STEP3 個人情報確認",
    "STEP4 管理策確認",
    "STEP5 運用開始",
]

NEEDS_REVIEW_NOTE = "回答内容が変更されたため、再確認をおすすめします。"


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _render_stepper() -> str:
    items = "".join(f"<li>{_escape(step)}</li>" for step in STEPPER)
    return f'<ol class="stepper">{items}</ol>'


# ---------------------------------------------------------------------------
# STEP 1: 業務情報
# ---------------------------------------------------------------------------


def _radio(field: str, value: str, label: str, current: bool | None) -> str:
    checked = " checked" if (current is True and value == "yes") or (current is False and value == "no") else ""
    return (
        f'<label><input type="radio" name="{field}" value="{value}" required{checked}> {label}</label>'
    )


def _render_step1_answers(state: IntakeDemoState) -> str:
    questions_html = "".join(
        f"""
        <div class="question">
          <p>{_escape(question_text)}</p>
          {_radio(field, "yes", "はい", getattr(state.answers, field))}
          {_radio(field, "no", "いいえ", getattr(state.answers, field))}
        </div>
        """
        for field, question_text in QUESTIONS
    )

    intro = (
        "まだ回答が保存されていません。以下の質問に回答して保存してください。"
        if not state.answers_submitted
        else "回答を変更すると、個人情報候補・管理策候補が自動的に再計算されます。"
    )

    return f"""
    <section class="step">
      <h2>STEP 1　業務情報</h2>
      <p>{intro}</p>
      <form method="post" action="/setup/answers">
        {questions_html}
        <button type="submit">回答を保存する</button>
      </form>
    </section>
    """


# ---------------------------------------------------------------------------
# STEP 2: 個人情報候補（一覧・読み取り専用）
# ---------------------------------------------------------------------------


def _render_step2_candidates(state: IntakeDemoState) -> str:
    if not state.answers_submitted:
        body = "<p>STEP1に回答すると、ここに個人情報の候補が表示されます。</p>"
    elif not state.candidates:
        body = "<p>現在の回答からは、該当する個人情報の候補はありません。</p>"
    else:
        rows = "".join(
            f"""
            <li class="candidate-item">
              <p class="candidate-name">{_escape(candidate.name)}（{CANDIDATE_STATUS_LABELS[candidate.status]}）</p>
              <p class="candidate-reason">候補となった理由：{_escape(candidate.reason)}</p>
              {'<p class="needs-review">⚠ ' + NEEDS_REVIEW_NOTE + '</p>' if candidate.needs_review else ""}
            </li>
            """
            for candidate in state.candidates
        )
        body = f'<ul class="candidate-list">{rows}</ul>'

    return f"""
    <section class="step">
      <h2>STEP 2　個人情報候補</h2>
      <p>回答内容から、取り扱っている可能性のある個人情報の候補を機械的に一覧化したものです（まだ確定していません）。</p>
      {body}
    </section>
    """


# ---------------------------------------------------------------------------
# STEP 3: 個人情報確認（要対応のみ・操作あり）＋確認済み台帳
# ---------------------------------------------------------------------------


def _render_candidate_action_item(candidate: PersonalInformationCandidate) -> str:
    review_note = f'<p class="needs-review">⚠ {NEEDS_REVIEW_NOTE}</p>' if candidate.needs_review else ""
    return f"""
    <li class="candidate-item">
      <p class="candidate-name">{_escape(candidate.name)}（現在：{CANDIDATE_STATUS_LABELS[candidate.status]}）</p>
      <p class="candidate-reason">候補となった理由：{_escape(candidate.reason)}</p>
      {review_note}
      <form method="post" action="/setup/candidates/{candidate.id}/confirm">
        <button type="submit">取り扱っている</button>
      </form>
      <form method="post" action="/setup/candidates/{candidate.id}/exclude">
        <button type="submit">該当しない</button>
      </form>
    </li>
    """


def _render_step3_confirmation(state: IntakeDemoState) -> str:
    actionable = [
        candidate
        for candidate in state.candidates
        if candidate.status == PersonalInformationCandidateStatus.CANDIDATE or candidate.needs_review
    ]

    if not state.answers_submitted:
        body = "<p>STEP1に回答すると、ここで個人情報候補を確認できるようになります。</p>"
    elif not actionable:
        body = "<p>確認が必要な個人情報候補はありません。</p>"
    else:
        rows = "".join(_render_candidate_action_item(candidate) for candidate in actionable)
        body = f'<ul class="candidate-list">{rows}</ul>'

    return f"""
    <section class="step">
      <h2>STEP 3　個人情報確認</h2>
      <p>候補ごとに、実際に取り扱っているかどうかを確認してください。</p>
      {body}
    </section>
    """


def _render_ledger_section(state: IntakeDemoState) -> str:
    confirmed = [
        candidate
        for candidate in state.candidates
        if candidate.status == PersonalInformationCandidateStatus.CONFIRMED
    ]

    if not confirmed:
        return """
        <section class="ledger">
          <h2>確認済み個人情報（簡易台帳）</h2>
          <p>候補一覧とは区別して、利用者が「取り扱っている」と確認したものだけを表示します。まだ確認済みの個人情報はありません。</p>
        </section>
        """

    rows = "".join(
        "<tr>"
        f"<td>{_escape(candidate.name)}</td>"
        f"<td>{_escape(candidate.subject_type)}</td>"
        f"<td>{_escape(candidate.purpose)}</td>"
        f"<td>{_escape(QUESTION_LABELS.get(candidate.source_key, candidate.source_key))}</td>"
        f"<td>{'あり' if candidate.outsourced else 'なし'}</td>"
        "</tr>"
        for candidate in confirmed
    )
    return f"""
    <section class="ledger">
      <h2>確認済み個人情報（簡易台帳）</h2>
      <p>候補一覧とは区別して、利用者が「取り扱っている」と確認したものだけを表示します。</p>
      <table class="records-table">
        <thead>
          <tr><th>個人情報名称</th><th>対象本人の区分</th><th>主な利用目的</th><th>候補となった業務</th><th>外部委託の有無</th></tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
    </section>
    """


# ---------------------------------------------------------------------------
# STEP 4: 管理策確認
# ---------------------------------------------------------------------------


def _related_candidates(state: IntakeDemoState, suggestion: ControlSuggestion) -> list[PersonalInformationCandidate]:
    confirmed = [
        candidate
        for candidate in state.candidates
        if candidate.status == PersonalInformationCandidateStatus.CONFIRMED
    ]
    if suggestion.control_id == "education":
        return [candidate for candidate in confirmed if candidate.subject_type == "従業員"]
    if suggestion.control_id == "vendor_management":
        return [candidate for candidate in confirmed if candidate.outsourced]
    return []


def _render_control_item(state: IntakeDemoState, suggestion: ControlSuggestion) -> str:
    status_label = CONTROL_STATUS_LABELS[suggestion.status]
    related = _related_candidates(state, suggestion)
    related_html = (
        f"<p class=\"control-related\">関連：{'、'.join(_escape(c.name) for c in related)}</p>"
        if related
        else '<p class="control-related">関連：（個人情報を確認すると表示されます）</p>'
    )
    review_note = f'<p class="needs-review">⚠ {NEEDS_REVIEW_NOTE}</p>' if suggestion.needs_review else ""

    if suggestion.status == ControlDecisionStatus.SUGGESTED:
        actions_html = f"""
        <form method="post" action="/setup/controls/{suggestion.control_id}/adopt">
          <button type="submit">採用する</button>
        </form>
        <form method="post" action="/setup/controls/{suggestion.control_id}/not-applicable" class="not-applicable-form">
          <input type="text" name="reason" placeholder="非適用の理由（必須）" required>
          <button type="submit">非適用にする</button>
        </form>
        """
    elif suggestion.status == ControlDecisionStatus.ADOPTED:
        link_label = CONTROL_LINK_LABELS.get(suggestion.control_id, "確認する")
        actions_html = (
            f'<p><a href="{suggestion.link_url}">{_escape(link_label)}</a></p>' if suggestion.link_url else ""
        )
    else:
        reason = suggestion.non_applicable_reason or "理由の記載なし"
        actions_html = f'<p class="non-applicable-reason">非適用理由：{_escape(reason)}</p>'

    return f"""
    <li class="control-item">
      <p class="control-name">{_escape(suggestion.name)}（{status_label}）</p>
      <p class="control-reason">提示理由：{_escape(suggestion.reason)}</p>
      {related_html}
      {review_note}
      {actions_html}
    </li>
    """


def _render_step4_controls(state: IntakeDemoState) -> str:
    if not state.answers_submitted:
        body = "<p>STEP1に回答すると、ここで管理策候補を確認できるようになります。</p>"
    elif not state.control_suggestions:
        body = "<p>現在の回答からは、提示できる管理策候補がありません。</p>"
    else:
        rows = "".join(
            _render_control_item(state, suggestion) for suggestion in state.control_suggestions
        )
        body = f'<ul class="control-list">{rows}</ul>'

    return f"""
    <section class="step">
      <h2>STEP 4　管理策確認</h2>
      <p>確認した業務・個人情報の内容から、必要になり得る管理策候補です。採用するか、非適用にするかを判断してください。</p>
      {body}
    </section>
    """


# ---------------------------------------------------------------------------
# STEP 5: 運用開始
# ---------------------------------------------------------------------------


def _render_step5_summary(state: IntakeDemoState) -> str:
    adopted = [
        suggestion
        for suggestion in state.control_suggestions
        if suggestion.status == ControlDecisionStatus.ADOPTED
    ]

    if not adopted:
        body = "<p>採用した管理策はまだありません。STEP4で管理策を採用すると、ここに運用画面への導線が表示されます。</p>"
    else:
        links = "".join(
            f'<li><a href="{suggestion.link_url}">{_escape(CONTROL_LINK_LABELS.get(suggestion.control_id, suggestion.name))}</a></li>'
            for suggestion in adopted
            if suggestion.link_url
        )
        body = f'<p>採用した管理策の運用画面に進めます。</p><ul class="next-links">{links}</ul>'

    return f"""
    <section class="step">
      <h2>STEP 5　運用開始</h2>
      {body}
    </section>
    """


def _render_reset_section() -> str:
    return """
    <section class="reset">
      <form method="post" action="/setup/reset">
        <button type="submit">デモを未回答の初期状態に戻す</button>
      </form>
    </section>
    """


# ---------------------------------------------------------------------------
# ページ全体
# ---------------------------------------------------------------------------


def render_setup_page(state: IntakeDemoState) -> str:
    status_label = "完了" if is_setup_complete(state) else "設定中"

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <title>Pマーク準備 - Pマーク取得・運用支援ツール MVP</title>
  <style>
    body {{ font-family: sans-serif; margin: 2rem; line-height: 1.6; max-width: 900px; }}
    h1 {{ margin-bottom: 0.5rem; }}
    section {{ margin-bottom: 2rem; padding-bottom: 1rem; border-bottom: 1px solid #ccc; }}
    .stepper {{ display: flex; flex-wrap: wrap; gap: 0.5rem; padding: 0; margin: 1rem 0; list-style: none; }}
    .stepper li {{
      background: #eef5fc; border: 1px solid #0a4a8a; border-radius: 4px;
      padding: 0.2rem 0.6rem; font-size: 0.9rem;
    }}
    .setup-status {{ font-weight: bold; }}
    .question {{ margin-bottom: 0.75rem; }}
    .question p {{ margin: 0 0 0.3rem; font-weight: bold; }}
    .question label {{ margin-right: 1rem; }}
    .candidate-list, .control-list {{ list-style: none; margin: 0; padding: 0; }}
    .candidate-item, .control-item {{
      padding: 0.75rem 1rem; margin-bottom: 0.75rem; border-radius: 4px;
      background: #f5f5f5; border-left: 4px solid #888;
    }}
    .candidate-name, .control-name {{ font-weight: bold; margin: 0 0 0.3rem; }}
    .candidate-reason, .control-reason, .control-related {{ margin: 0 0 0.5rem; color: #555; }}
    .non-applicable-reason {{ margin: 0; color: #555; }}
    .needs-review {{ margin: 0 0 0.5rem; color: #a15c00; font-weight: bold; }}
    form {{ display: inline-block; margin: 0 0.5rem 0.5rem 0; }}
    .not-applicable-form input[type="text"] {{ margin-right: 0.3rem; }}
    .records-table {{ border-collapse: collapse; }}
    .records-table th, .records-table td {{ text-align: left; border: 1px solid #ccc; padding: 4px 8px; }}
    .next-links {{ padding-left: 1.2rem; font-size: 1.1rem; }}
  </style>
</head>
<body>
  <p><a href="/">&laquo; トップへ戻る</a></p>
  <h1>Pマーク準備</h1>
  <p>会社・業務について回答すると、取り扱っている可能性のある個人情報や、必要になり得る管理策の候補が提示されます。内容を確認・採用しながら準備を進めます。</p>
  <p class="setup-status">初期設定の状態：{status_label}</p>
  {_render_stepper()}

  {_render_step1_answers(state)}
  {_render_step2_candidates(state)}
  {_render_step3_confirmation(state)}
  {_render_ledger_section(state)}
  {_render_step4_controls(state)}
  {_render_step5_summary(state)}
  {_render_reset_section()}
</body>
</html>
"""
