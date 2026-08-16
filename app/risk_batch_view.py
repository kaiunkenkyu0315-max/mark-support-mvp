"""STEP4 リスク確認の一括判断・一括評価UI。

1. 候補ごとに「該当する／該当しない」をまとめて判断
2. 該当するとしたリスクだけ、システム初期案の影響度・発生可能性をまとめて確認

という2段階にし、1件操作するたびの画面再読込を避ける。
"""

from __future__ import annotations

from html import escape

from app.intake_demo_state import IntakeDemoState
from app.risk import evaluate_risk
from app.risk_schemas import RiskCandidateStatus
from app.setup_step_gating import step4_unlocked


_SCALE = {1: "低", 2: "中", 3: "高"}


def _replace_step4(html: str, replacement: str) -> str:
    marker = '<section class="step" id="step4">'
    start = html.find(marker)
    if start == -1:
        return html
    end = html.find("</section>", start)
    if end == -1:
        return html
    end += len("</section>")
    return html[:start] + replacement + html[end:]


def _related_names(state: IntakeDemoState, risk) -> list[str]:
    keys = set(risk.related_personal_information_keys)
    if not keys:
        return []
    return [c.name for c in state.candidates if c.source_key in keys]


def _decision_checked(risk, value: str) -> str:
    if risk.needs_review:
        return ""
    if value == "yes" and risk.status == RiskCandidateStatus.CONFIRMED:
        return " checked"
    if value == "no" and risk.status == RiskCandidateStatus.EXCLUDED:
        return " checked"
    return ""


def _decision_item(state: IntakeDemoState, risk) -> str:
    related = _related_names(state, risk)
    related_html = (
        f'<p class="question-help">関連する個人情報：{escape("、".join(related))}</p>'
        if related
        else ""
    )
    review_html = (
        '<p class="needs-review">⚠ 前提情報が変更されたため、もう一度判断してください。</p>'
        if risk.needs_review
        else ""
    )
    return f"""
    <div class="risk-item risk-batch-item">
      <p class="risk-name">{escape(risk.name)}</p>
      <p class="risk-description">{escape(risk.description)}</p>
      <p class="risk-reason">候補となった理由：{escape(risk.reason)}</p>
      {related_html}
      {review_html}
      <label><input type="radio" name="risk_{risk.id}" value="yes" required{_decision_checked(risk, 'yes')}> 該当する</label>
      <label><input type="radio" name="risk_{risk.id}" value="no" required{_decision_checked(risk, 'no')}> 該当しない</label>
    </div>
    """


def _render_decision_phase(state: IntakeDemoState) -> str:
    items = "".join(_decision_item(state, risk) for risk in state.risks)
    return f"""
    <section class="step" id="step4">
      <h2>STEP 4　リスク確認</h2>
      <p>想定されるリスク候補です。実際の業務に該当するかをまとめて判断してください。</p>
      <form method="post" action="/setup/risks/decide" style="display:block;">
        {items}
        <button type="submit">回答を保存して評価へ</button>
      </form>
      <p class="risk-disclaimer">リスク候補があること自体は、事故発生・法令違反・Pマーク取得可否を意味しません。</p>
      <p class="back-to-top"><a href="#setup-top">↑ 初期設定の先頭へ戻る</a></p>
    </section>
    """


def _select(name: str, current: int) -> str:
    options = "".join(
        f'<option value="{value}"{" selected" if value == current else ""}>{value}（{label}）</option>'
        for value, label in _SCALE.items()
    )
    return f'<select name="{name}" required>{options}</select>'


def _evaluation_item(risk) -> str:
    suggested = evaluate_risk(risk)
    return f"""
    <div class="risk-item risk-evaluation-item">
      <p class="risk-name">{escape(risk.name)}</p>
      <p class="risk-description">{escape(risk.description)}</p>
      <p>システム初期案：影響度 {_SCALE[risk.suggested_impact]} ／ 発生可能性 {_SCALE[risk.suggested_likelihood]}</p>
      <p class="question-help">初期案のままで問題なければ変更せず保存してください。必要に応じて修正できます。</p>
      <label>影響度 {_select(f'impact_{risk.id}', risk.impact)}</label>
      <label>発生可能性 {_select(f'likelihood_{risk.id}', risk.likelihood)}</label>
      <p class="question-help">現在値の評価：{suggested.score}（{suggested.level.value}）</p>
    </div>
    """


def _render_evaluation_phase(state: IntakeDemoState) -> str:
    confirmed = [r for r in state.risks if r.status == RiskCandidateStatus.CONFIRMED]
    excluded_count = sum(1 for r in state.risks if r.status == RiskCandidateStatus.EXCLUDED)
    items = "".join(_evaluation_item(risk) for risk in confirmed)

    if not confirmed:
        # 全候補を非該当と判断した場合は、評価対象がないため次工程へ進める。
        body = '<p>該当すると判断したリスクはありません。STEP5へ進めます。</p>'
    else:
        body = f"""
        <p>該当すると判断したリスクだけ評価します。システムの初期案を確認し、必要な箇所だけ変更してください。</p>
        <p class="question-help">評価対象：{len(confirmed)}件 ／ 非該当：{excluded_count}件</p>
        <form method="post" action="/setup/risks/evaluate-batch" style="display:block;">
          {items}
          <button type="submit">評価をまとめて確定して次へ</button>
        </form>
        """

    return f"""
    <section class="step" id="step4">
      <h2>STEP 4　リスク評価</h2>
      {body}
      <p class="risk-disclaimer">リスクレベルは優先的に対策を検討するための目安です。</p>
      <p class="back-to-top"><a href="#setup-top">↑ 初期設定の先頭へ戻る</a></p>
    </section>
    """


def _final_item(risk) -> str:
    result = evaluate_risk(risk)
    if risk.status == RiskCandidateStatus.EXCLUDED:
        return f'<li>{escape(risk.name)}：該当しない</li>'
    return (
        f'<li>{escape(risk.name)}：影響度{risk.impact} × 発生可能性{risk.likelihood}'
        f' ＝ {result.score}（{result.level.value}）</li>'
    )


def _render_complete_phase(state: IntakeDemoState) -> str:
    rows = "".join(_final_item(risk) for risk in state.risks)
    review_items = "".join(_decision_item(state, risk) for risk in state.risks)
    return f"""
    <section class="step" id="step4">
      <h2>STEP 4　リスク確認</h2>
      <p><strong>リスク判断・評価は完了しています。</strong></p>
      <ul>{rows}</ul>
      <details>
        <summary>リスク判断を見直す</summary>
        <form method="post" action="/setup/risks/decide" style="display:block; margin-top:0.8rem;">
          {review_items}
          <button type="submit">判断を保存して評価を確認する</button>
        </form>
      </details>
      <p class="back-to-top"><a href="#setup-top">↑ 初期設定の先頭へ戻る</a></p>
    </section>
    """


def apply_risk_batch_view(html: str, state: IntakeDemoState) -> str:
    """STEP4がアンロック済みの場合、現在の段階に合った一括UIへ置き換える。"""

    if not step4_unlocked(state):
        return html

    unresolved_decisions = any(
        risk.status == RiskCandidateStatus.CANDIDATE or risk.needs_review
        for risk in state.risks
    )
    if unresolved_decisions:
        return _replace_step4(html, _render_decision_phase(state))

    pending_evaluations = any(
        risk.status == RiskCandidateStatus.CONFIRMED and not risk.evaluation_reviewed
        for risk in state.risks
    )
    if pending_evaluations:
        return _replace_step4(html, _render_evaluation_phase(state))

    return _replace_step4(html, _render_complete_phase(state))
