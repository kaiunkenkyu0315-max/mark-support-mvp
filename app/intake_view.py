"""intakeフロー（業務ヒアリング〜個人情報確認〜リスクアセスメント〜管理策候補提示）
のHTML描画。

ここでは業務判定（候補生成・管理策提示・リスク評価・回答変更時の再計算ルール）を
一切行わない。app.intake_demo_state が保持する事実・候補・確定状態を
そのまま表示するだけとする。UI側に「従業員あり→教育管理」「紙保管あり→紙媒体リスク」
のような判定を書かない。
"""

from __future__ import annotations

from app.intake import (
    LEDGER_FIELD_LABELS,
    is_ledger_complete,
    is_ledger_entry_complete,
    missing_ledger_fields,
)
from app.intake_demo_state import QUESTIONS, IntakeDemoState, get_setup_status
from app.intake_schemas import (
    ControlDecisionStatus,
    ControlSuggestion,
    PersonalInformationCandidate,
    PersonalInformationCandidateStatus,
    SetupStatus,
)
from app.risk import CONTROL_RELATED_RISK_IDS, confirmed_risk_reasons_for_control, evaluate_risk
from app.risk_schemas import RiskCandidate, RiskCandidateStatus, RiskLevel

SETUP_STATUS_LABELS = {
    SetupStatus.NOT_STARTED: "未着手",
    SetupStatus.IN_PROGRESS: "設定中",
    SetupStatus.COMPLETE: "完了",
}

SETUP_STATUS_CSS_CLASS = {
    SetupStatus.NOT_STARTED: "not-started",
    SetupStatus.IN_PROGRESS: "needs-action",
    SetupStatus.COMPLETE: "compliant",
}

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

RISK_STATUS_LABELS = {
    RiskCandidateStatus.CANDIDATE: "未確認（候補）",
    RiskCandidateStatus.CONFIRMED: "確認済み",
    RiskCandidateStatus.EXCLUDED: "除外（該当しない）",
}

RISK_LEVEL_CSS_CLASS = {
    RiskLevel.LOW: "risk-low",
    RiskLevel.MEDIUM: "risk-medium",
    RiskLevel.HIGH: "risk-high",
}

EVALUATION_SCALE_LABELS = {1: "1（低）", 2: "2（中）", 3: "3（高）"}

# 採用済み管理策から、既存MVPへの導線ボタン文言。
CONTROL_LINK_LABELS = {
    "education": "教育管理へ進む",
    "vendor_management": "委託先管理へ進む",
}

STEPPER = [
    "STEP1 業務情報",
    "STEP2 個人情報候補",
    "STEP3 個人情報確認",
    "STEP4 リスク確認",
    "STEP5 管理策確認",
    "STEP6 運用開始",
]

NEEDS_REVIEW_NOTE = "回答内容が変更されたため、再確認をおすすめします。"

RISK_LEVEL_DISCLAIMER = (
    "リスクレベルは、事故の発生・法令違反・Pマーク取得可否を意味するものではありません。"
    "あくまで優先的に対策を検討する目安です。"
)


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


def _tristate_radio_group(field: str, current: bool | None) -> str:
    """台帳項目のうち、あり／なし／未回答の3値を取り得る項目用のラジオボタン群。

    未入力（None）を「いいえ」で代用せず、明示的に「未回答」として選べるようにする。
    """

    options = (("yes", "あり", current is True), ("no", "なし", current is False), ("unknown", "未回答", current is None))
    return "".join(
        f'<label><input type="radio" name="{field}" value="{value}"{" checked" if checked else ""}> {label}</label>'
        for value, label, checked in options
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


def _render_ledger_entry(candidate: PersonalInformationCandidate) -> str:
    review_note = f'<p class="needs-review">⚠ {NEEDS_REVIEW_NOTE}</p>' if candidate.needs_review else ""
    entry_complete = is_ledger_entry_complete(candidate)
    if entry_complete:
        entry_status_note = '<p class="ledger-entry-complete">台帳項目：入力済み</p>'
    else:
        missing_labels = "、".join(
            LEDGER_FIELD_LABELS.get(field, field) for field in missing_ledger_fields(candidate)
        )
        entry_status_note = (
            f'<p class="ledger-entry-incomplete">⚠ 台帳必須項目が未入力です（{_escape(missing_labels)}）。</p>'
        )

    return f"""
    <li class="candidate-item">
      <p class="candidate-name">{_escape(candidate.name)}</p>
      <p class="candidate-reason">
        対象本人の区分：{_escape(candidate.subject_type)}／
        主な利用目的：{_escape(candidate.purpose)}／
        候補となった業務：{_escape(QUESTION_LABELS.get(candidate.source_key, candidate.source_key))}
      </p>
      {review_note}
      {entry_status_note}
      <form method="post" action="/setup/candidates/{candidate.id}/ledger" class="ledger-form">
        <label>取得方法
          <input type="text" name="acquisition_method" value="{_escape(candidate.acquisition_method or '')}">
        </label>
        <label>保管方法
          <input type="text" name="storage_method" value="{_escape(candidate.storage_method or '')}">
        </label>
        <label>保管場所
          <input type="text" name="storage_location" value="{_escape(candidate.storage_location or '')}">
        </label>
        <div class="ledger-form-row">
          <span class="ledger-form-row-label">外部委託の有無</span>
          {_tristate_radio_group('outsourced', candidate.outsourced)}
        </div>
        <div class="ledger-form-row">
          <span class="ledger-form-row-label">第三者提供の有無</span>
          {_tristate_radio_group('third_party_provided', candidate.third_party_provided)}
        </div>
        <label>保管期間
          <input type="text" name="retention_period" value="{_escape(candidate.retention_period or '')}">
        </label>
        <label>廃棄方法
          <input type="text" name="disposal_method" value="{_escape(candidate.disposal_method or '')}">
        </label>
        <label>管理担当者（役割）
          <input type="text" name="responsible_role" value="{_escape(candidate.responsible_role or '')}">
        </label>
        <button type="submit">台帳項目を保存する</button>
      </form>
    </li>
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

    ledger_complete = is_ledger_complete(state.candidates)
    ledger_status_label = "完了" if ledger_complete else "未完了"
    ledger_status_class = "compliant" if ledger_complete else "needs-action"
    rows = "".join(_render_ledger_entry(candidate) for candidate in confirmed)

    return f"""
    <section class="ledger">
      <h2>確認済み個人情報（簡易台帳）</h2>
      <p>候補一覧とは区別して、利用者が「取り扱っている」と確認したものだけを表示します。
      台帳必須項目をすべて入力すると、台帳項目が完了します。</p>
      <p class="ledger-status">台帳の状態：<span class="status-badge {ledger_status_class}">{ledger_status_label}</span></p>
      <ul class="candidate-list">{rows}</ul>
    </section>
    """


# ---------------------------------------------------------------------------
# STEP 4: リスク確認
# ---------------------------------------------------------------------------


def _related_personal_information_names(state: IntakeDemoState, risk: RiskCandidate) -> list[str]:
    candidates_by_key = {candidate.source_key: candidate for candidate in state.candidates}
    return [
        candidates_by_key[key].name
        for key in risk.related_personal_information_keys
        if key in candidates_by_key
    ]


def _render_risk_evaluation_block(risk: RiskCandidate) -> str:
    evaluation = evaluate_risk(risk)
    level_class = RISK_LEVEL_CSS_CLASS[evaluation.level]

    impact_options = "".join(
        f'<option value="{value}"{" selected" if value == risk.impact else ""}>{label}</option>'
        for value, label in EVALUATION_SCALE_LABELS.items()
    )
    likelihood_options = "".join(
        f'<option value="{value}"{" selected" if value == risk.likelihood else ""}>{label}</option>'
        for value, label in EVALUATION_SCALE_LABELS.items()
    )

    return f"""
    <div class="risk-evaluation">
      <p>システム初期案：影響度 {EVALUATION_SCALE_LABELS[risk.suggested_impact]}／発生可能性 {EVALUATION_SCALE_LABELS[risk.suggested_likelihood]}</p>
      <p class="risk-badge {level_class}">最終評価：影響度{risk.impact}×発生可能性{risk.likelihood}＝{evaluation.score}（{evaluation.level.value}）</p>
      <form method="post" action="/setup/risks/{risk.id}/evaluate">
        <label>影響度
          <select name="impact">{impact_options}</select>
        </label>
        <label>発生可能性
          <select name="likelihood">{likelihood_options}</select>
        </label>
        <button type="submit">評価を更新する</button>
      </form>
    </div>
    """


def _render_risk_item(state: IntakeDemoState, risk: RiskCandidate) -> str:
    status_label = RISK_STATUS_LABELS[risk.status]
    related_names = _related_personal_information_names(state, risk)
    related_html = (
        f"<p class=\"risk-related\">関連する個人情報：{'、'.join(_escape(name) for name in related_names)}</p>"
        if related_names
        else ""
    )
    review_note = f'<p class="needs-review">⚠ {NEEDS_REVIEW_NOTE}</p>' if risk.needs_review else ""

    if risk.status == RiskCandidateStatus.CANDIDATE or risk.needs_review:
        actions_html = f"""
        <form method="post" action="/setup/risks/{risk.id}/confirm">
          <button type="submit">このリスクを確認する</button>
        </form>
        <form method="post" action="/setup/risks/{risk.id}/exclude">
          <button type="submit">該当しない</button>
        </form>
        """
    elif risk.status == RiskCandidateStatus.CONFIRMED:
        actions_html = _render_risk_evaluation_block(risk)
    else:
        actions_html = ""

    return f"""
    <li class="risk-item">
      <p class="risk-name">{_escape(risk.name)}（{status_label}）</p>
      <p class="risk-description">{_escape(risk.description)}</p>
      <p class="risk-reason">候補となった理由：{_escape(risk.reason)}</p>
      {related_html}
      {review_note}
      {actions_html}
    </li>
    """


def _render_step4_risks(state: IntakeDemoState) -> str:
    confirmed_pi_count = sum(
        1
        for candidate in state.candidates
        if candidate.status == PersonalInformationCandidateStatus.CONFIRMED
    )
    confirmed_risks = [risk for risk in state.risks if risk.status == RiskCandidateStatus.CONFIRMED]
    high_risk_count = sum(
        1 for risk in confirmed_risks if evaluate_risk(risk).level == RiskLevel.HIGH
    )

    summary = f"""
    <ul class="risk-summary">
      <li>確認済み個人情報：{confirmed_pi_count}件</li>
      <li>リスク候補：{len(state.risks)}件</li>
      <li>確認済みリスク：{len(confirmed_risks)}件</li>
      <li>高リスク：{high_risk_count}件</li>
    </ul>
    <p class="risk-disclaimer">{RISK_LEVEL_DISCLAIMER}</p>
    """

    if not state.answers_submitted:
        body = "<p>STEP1に回答すると、ここでリスク候補を確認できるようになります。</p>"
    elif not state.risks:
        body = "<p>現在の回答・確認済み個人情報からは、該当するリスク候補はありません。</p>"
    else:
        rows = "".join(_render_risk_item(state, risk) for risk in state.risks)
        body = f'<ul class="risk-list">{rows}</ul>'

    return f"""
    <section class="step">
      <h2>STEP 4　リスク確認</h2>
      <p>確認済みの個人情報・業務内容から、想定されるリスクの候補です。内容を確認し、実際に該当するかどうかを判断してください。</p>
      {summary}
      {body}
    </section>
    """


# ---------------------------------------------------------------------------
# STEP 5: 管理策確認
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

    confirmed_risks = [risk for risk in state.risks if risk.status == RiskCandidateStatus.CONFIRMED]
    risk_reasons = confirmed_risk_reasons_for_control(suggestion.control_id, confirmed_risks)
    reason_items = "".join(f"<li>{_escape(text)}</li>" for text in [suggestion.reason, *risk_reasons])
    reason_html = f'<p class="control-reason">提示理由：</p><ul class="control-reason-list">{reason_items}</ul>'

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
      {reason_html}
      {related_html}
      {review_note}
      {actions_html}
    </li>
    """


def _render_unmapped_risk_note(state: IntakeDemoState) -> str:
    mapped_risk_ids = {
        risk_id for ids in CONTROL_RELATED_RISK_IDS.values() for risk_id in ids
    }
    confirmed_unmapped = [
        risk
        for risk in state.risks
        if risk.status == RiskCandidateStatus.CONFIRMED and risk.risk_id not in mapped_risk_ids
    ]
    if not confirmed_unmapped:
        return ""
    names = "、".join(_escape(risk.name) for risk in confirmed_unmapped)
    return (
        f'<p class="control-unmapped-note">{names}については、今回のMVPでは対応する管理策を'
        "実装していません（関連する管理策は今後追加予定です）。</p>"
    )


def _render_step5_controls(state: IntakeDemoState) -> str:
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
      <h2>STEP 5　管理策確認</h2>
      <p>確認した業務・個人情報・リスクの内容から、必要になり得る管理策候補です。採用するか、非適用にするかを判断してください。</p>
      {body}
      {_render_unmapped_risk_note(state)}
    </section>
    """


# ---------------------------------------------------------------------------
# STEP 6: 運用開始
# ---------------------------------------------------------------------------


def _render_step6_summary(state: IntakeDemoState) -> str:
    adopted = [
        suggestion
        for suggestion in state.control_suggestions
        if suggestion.status == ControlDecisionStatus.ADOPTED
    ]

    if not adopted:
        body = "<p>採用した管理策はまだありません。STEP5で管理策を採用すると、ここに運用画面への導線が表示されます。</p>"
    else:
        links = "".join(
            f'<li><a href="{suggestion.link_url}">{_escape(CONTROL_LINK_LABELS.get(suggestion.control_id, suggestion.name))}</a></li>'
            for suggestion in adopted
            if suggestion.link_url
        )
        body = f'<p>採用した管理策の運用画面に進めます。</p><ul class="next-links">{links}</ul>'

    return f"""
    <section class="step">
      <h2>STEP 6　運用開始</h2>
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
    setup_status = get_setup_status(state)
    status_label = SETUP_STATUS_LABELS[setup_status]
    status_class = SETUP_STATUS_CSS_CLASS[setup_status]

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
    .status-badge {{ display: inline-block; padding: 0.2rem 0.6rem; border-radius: 4px; color: #fff; }}
    .status-badge.not-started {{ background: #666; }}
    .status-badge.needs-action {{ background: #b30000; }}
    .status-badge.compliant {{ background: #0a7a0a; }}
    .ledger-status {{ font-weight: bold; }}
    .ledger-entry-complete {{ margin: 0 0 0.5rem; color: #0a7a0a; font-weight: bold; }}
    .ledger-entry-incomplete {{ margin: 0 0 0.5rem; color: #b30000; font-weight: bold; }}
    .ledger-form label {{ display: inline-block; margin-right: 0.75rem; }}
    .ledger-form input[type="text"] {{ margin-left: 0.3rem; }}
    .ledger-form-row {{ margin: 0 0 0.5rem; }}
    .ledger-form-row-label {{ font-weight: bold; margin-right: 0.5rem; }}
    .ledger-form-row label {{ display: inline-block; margin-right: 0.75rem; font-weight: normal; }}
    .question {{ margin-bottom: 0.75rem; }}
    .question p {{ margin: 0 0 0.3rem; font-weight: bold; }}
    .question label {{ margin-right: 1rem; }}
    .candidate-list, .control-list, .risk-list {{ list-style: none; margin: 0; padding: 0; }}
    .candidate-item, .control-item, .risk-item {{
      padding: 0.75rem 1rem; margin-bottom: 0.75rem; border-radius: 4px;
      background: #f5f5f5; border-left: 4px solid #888;
    }}
    .candidate-name, .control-name, .risk-name {{ font-weight: bold; margin: 0 0 0.3rem; }}
    .candidate-reason, .control-reason, .control-related,
    .risk-description, .risk-reason, .risk-related {{ margin: 0 0 0.5rem; color: #555; }}
    .control-reason-list {{ margin: 0 0 0.5rem; padding-left: 1.2rem; color: #555; }}
    .non-applicable-reason, .control-unmapped-note {{ margin: 0; color: #555; }}
    .needs-review {{ margin: 0 0 0.5rem; color: #a15c00; font-weight: bold; }}
    form {{ display: inline-block; margin: 0 0.5rem 0.5rem 0; }}
    .not-applicable-form input[type="text"] {{ margin-right: 0.3rem; }}
    .records-table {{ border-collapse: collapse; }}
    .records-table th, .records-table td {{ text-align: left; border: 1px solid #ccc; padding: 4px 8px; }}
    .next-links {{ padding-left: 1.2rem; font-size: 1.1rem; }}
    .risk-summary {{ display: flex; flex-wrap: wrap; gap: 1rem; padding: 0; margin: 0.5rem 0; list-style: none; }}
    .risk-summary li {{
      background: #f5f5f5; border: 1px solid #ccc; border-radius: 4px; padding: 0.3rem 0.7rem;
    }}
    .risk-disclaimer {{ font-size: 0.85rem; color: #777; margin: 0 0 1rem; }}
    .risk-evaluation {{ margin-top: 0.5rem; }}
    .risk-evaluation select {{ margin: 0 0.5rem; }}
    .risk-badge {{ display: inline-block; padding: 0.2rem 0.6rem; border-radius: 4px; font-weight: bold; }}
    .risk-badge.risk-low {{ background: #e6f4ea; color: #0a7a0a; }}
    .risk-badge.risk-medium {{ background: #fff4e0; color: #a15c00; }}
    .risk-badge.risk-high {{ background: #fdeaea; color: #b30000; }}
  </style>
</head>
<body>
  <p><a href="/">&laquo; トップへ戻る</a></p>
  <h1>Pマーク準備</h1>
  <p>会社・業務について回答すると、取り扱っている可能性のある個人情報や、必要になり得る管理策の候補が提示されます。内容を確認・採用しながら準備を進めます。</p>
  <p class="setup-status">初期設定の状態：<span class="status-badge {status_class}">{status_label}</span></p>
  {_render_stepper()}

  {_render_step1_answers(state)}
  {_render_step2_candidates(state)}
  {_render_step3_confirmation(state)}
  {_render_ledger_section(state)}
  {_render_step4_risks(state)}
  {_render_step5_controls(state)}
  {_render_step6_summary(state)}
  {_render_reset_section()}
</body>
</html>
"""
