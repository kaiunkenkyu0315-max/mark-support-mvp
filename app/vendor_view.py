"""委託先管理デモ画面のHTML描画。

ここでは業務判定を一切行わない。渡された VendorEvaluationResult
（app.vendors.evaluate_vendors の結果）をそのまま表示するだけとする。

教育管理デモ画面（app.education_view）と同じUI思想を踏襲し、
「今どういう状態か」「何が不足しているか」「次に何をすればいいか」を
最初に伝える。会社情報に相当する委託先一覧・管理策・規程などの詳細情報は
<details> にまとめて後段に置く。
"""

from __future__ import annotations

from app.control_status import operational_status
from app.intake import CONTROL_STATUS_LABELS, find_control_suggestion
from app.intake_schemas import ControlDecisionStatus, ControlSuggestion
from app.vendor_demo_state import POLICY_CLAUSES, VendorDemoState
from app.vendor_schemas import (
    AssessmentResult,
    VendorAssessment,
    VendorContractStatus,
    VendorEvaluationResult,
    VendorEvaluationStatus,
    VendorIssue,
)
from app.vendors import assessment_frequency_label

# 不足事項（rule_id）を、利用者向けの見出し・対応ボタン・短い説明へ変換するための表示定義。
# rule_idそのものはここでは主表示に使わず、判定詳細（詳細情報内）でのみ表示する。
ISSUE_DISPLAY = {
    "VEN-001": {
        "headline": "初回評価が未実施の委託先があります",
        "explain": "委託開始前に確認すべき初回評価の結果を登録してください。",
        "action_label": "評価済みにする",
        "action_url": "/vendors/actions/complete-initial-assessments",
    },
    "VEN-002": {
        "headline": "契約確認が未完了の委託先があります",
        "explain": "委託契約に個人情報保護に関する事項が定められているか確認してください。",
        "action_label": "契約確認を完了する",
        "action_url": "/vendors/actions/confirm-contracts",
    },
    "VEN-004": {
        "headline": "有効な定期評価がない委託先があります",
        "explain": "委託先の個人情報取扱状況について、定期評価を実施し結果を登録してください。",
        "action_label": "定期評価を完了する",
        "action_url": "/vendors/actions/complete-periodic-assessments",
    },
    "VEN-006": {
        "headline": "次回評価期限を超過している委託先があります",
        "explain": "評価期限を過ぎています。速やかに定期評価を実施してください。",
        "action_label": "定期評価を完了する",
        "action_url": "/vendors/actions/complete-periodic-assessments",
    },
}


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _initial_assessment_label(assessment: VendorAssessment | None) -> str:
    if assessment is None or not assessment.initial_assessment_completed:
        return "未実施"
    return "実施済み"


def _contract_label(contract: VendorContractStatus | None) -> str:
    if contract is None or not contract.contract_confirmed:
        return "未完了"
    return "完了"


def _assessment_result_label(assessment: VendorAssessment | None) -> str:
    if assessment is None or assessment.assessment_result is None:
        return "未評価"
    return "合格" if assessment.assessment_result == AssessmentResult.PASSED else "不合格"


def _date_label(value) -> str:
    return value.isoformat() if value else "未設定"


def _issue_by_rule(result: VendorEvaluationResult, rule_id: str) -> VendorIssue | None:
    return next((issue for issue in result.issues if issue.rule_id == rule_id), None)


def _setup_adoption_label(suggestion: ControlSuggestion | None) -> str:
    """初期設定での採用判断（正本）を表示用ラベルへ変換する。

    この管理策自体（VendorControl）は採用可否の判断を持たないため、
    ここでは必ず初期設定側のControlSuggestionを参照する。
    """

    if suggestion is None:
        return "未確認（初期設定で未回答）"
    return CONTROL_STATUS_LABELS[suggestion.status]


def _render_adoption_notice(control_suggestions: list[ControlSuggestion]) -> str:
    """この管理策が初期設定で採用済みかどうかを、画面冒頭で明示する。"""

    suggestion = find_control_suggestion(control_suggestions, "vendor_management")
    if suggestion is not None and suggestion.status == ControlDecisionStatus.ADOPTED:
        return ""
    _, _, note = operational_status(suggestion, has_issues=False)
    return f"""
    <div class="adoption-notice">
      <p>⚠ {_escape(note)}</p>
      <p><a href="/setup">初期設定を確認する</a></p>
    </div>
    """


def _render_flash(flash: str | None) -> str:
    if not flash:
        return ""
    return f'<div class="flash-message">{_escape(flash)}</div>'


def _vendor_names(state: VendorDemoState, vendor_ids: list[int]) -> str:
    vendors_by_id = {vendor.id: vendor for vendor in state.vendors}
    return "、".join(
        _escape(vendors_by_id[vendor_id].name) for vendor_id in vendor_ids if vendor_id in vendors_by_id
    )


# ---------------------------------------------------------------------------
# 1. 現在の状態サマリー
# ---------------------------------------------------------------------------


def _render_status_summary(state: VendorDemoState, result: VendorEvaluationResult) -> str:
    status_class = (
        "compliant" if result.status == VendorEvaluationStatus.COMPLIANT else "needs-action"
    )

    missing_initial_issue = _issue_by_rule(result, "VEN-001")
    unevaluated_count = len(missing_initial_issue.vendor_ids) if missing_initial_issue else 0
    target_count = len(result.target_vendor_ids)
    evaluated_count = target_count - unevaluated_count

    return f"""
    <section class="status-summary">
      <p class="control-title">{_escape(state.control.name)}</p>
      <p class="status-badge {status_class}">現在の状態：<strong>{result.status.value}</strong></p>
      <p class="issue-count">対応が必要な項目：{len(result.issues)}件</p>
      <ul class="status-figures">
        <li>管理対象委託先：{target_count}社</li>
        <li>評価済み：{evaluated_count}社</li>
        <li>未評価：{unevaluated_count}社</li>
      </ul>
    </section>
    """


# ---------------------------------------------------------------------------
# 2. 今やること（不足事項＋対応操作）
# ---------------------------------------------------------------------------


def _render_todo_section(state: VendorDemoState, result: VendorEvaluationResult) -> str:
    if not result.issues:
        return """
        <section class="todo">
          <h2>今やること</h2>
          <p class="todo-empty complete">対応が必要な項目はありません。すべて適合しています。</p>
        </section>
        """

    items = []
    for issue in result.issues:
        display = ISSUE_DISPLAY.get(issue.rule_id)
        headline = display["headline"] if display else issue.message
        explain_html = (
            f'<p class="todo-explain">{_escape(display["explain"])}</p>'
            if display and display.get("explain")
            else ""
        )
        names = _vendor_names(state, issue.vendor_ids)
        names_html = f'<p class="todo-names">対象：{names}</p>' if names else ""

        if display:
            action_html = (
                f'<form method="post" action="{display["action_url"]}">'
                f'<button type="submit">{_escape(display["action_label"])}</button>'
                "</form>"
            )
        else:
            action_html = ""

        items.append(
            '<li class="todo-item warning">'
            f'<p class="todo-headline">{_escape(headline)}</p>'
            f"{explain_html}"
            f"{names_html}"
            f"{action_html}"
            "</li>"
        )

    return f"""
    <section class="todo">
      <h2>今やること</h2>
      <ul class="todo-list">{"".join(items)}</ul>
    </section>
    """


# ---------------------------------------------------------------------------
# 3. 問題のある委託先
# ---------------------------------------------------------------------------


def _render_problem_vendors_section(
    state: VendorDemoState, result: VendorEvaluationResult
) -> str:
    vendors_by_id = {vendor.id: vendor for vendor in state.vendors}
    assessments_by_vendor = {assessment.vendor_id: assessment for assessment in state.assessments}
    contracts_by_vendor = {contract.vendor_id: contract for contract in state.contracts}

    problem_ids: list[int] = []
    seen: set[int] = set()
    for issue in result.issues:
        for vendor_id in issue.vendor_ids:
            if vendor_id not in seen:
                seen.add(vendor_id)
                problem_ids.append(vendor_id)

    if not problem_ids:
        return """
        <section class="problem-vendors">
          <h2>問題のある委託先</h2>
          <p>問題のある委託先はいません。</p>
        </section>
        """

    rows = []
    for vendor_id in problem_ids:
        vendor = vendors_by_id.get(vendor_id)
        if vendor is None:
            continue
        assessment = assessments_by_vendor.get(vendor_id)
        contract = contracts_by_vendor.get(vendor_id)
        rows.append(
            "<tr>"
            f"<td>{vendor.id}</td>"
            f"<td>{_escape(vendor.name)}</td>"
            f"<td>{_escape(vendor.service_description)}</td>"
            f"<td>{_initial_assessment_label(assessment)}</td>"
            f"<td>{_contract_label(contract)}</td>"
            f"<td>{_assessment_result_label(assessment)}</td>"
            f"<td>{_date_label(assessment.next_assessment_due if assessment else None)}</td>"
            "</tr>"
        )

    return f"""
    <section class="problem-vendors">
      <h2>問題のある委託先</h2>
      <table class="records-table">
        <thead>
          <tr>
            <th>ID</th><th>名前</th><th>業務内容</th><th>初回評価</th>
            <th>契約確認</th><th>定期評価結果</th><th>次回評価期限</th>
          </tr>
        </thead>
        <tbody>{"".join(rows)}</tbody>
      </table>
    </section>
    """


# ---------------------------------------------------------------------------
# 4. 詳細情報（委託先一覧・管理策・規程・評価状況・契約状況・判定詳細）
# ---------------------------------------------------------------------------


def _render_vendor_list_detail(state: VendorDemoState) -> str:
    rows = "".join(
        "<tr>"
        f"<td>{vendor.id}</td>"
        f"<td>{_escape(vendor.name)}</td>"
        f"<td>{_escape(vendor.service_description)}</td>"
        f"<td>{'あり' if vendor.handles_personal_data else 'なし'}</td>"
        f"<td>{'稼働中' if vendor.active else '停止'}</td>"
        "</tr>"
        for vendor in state.vendors
    )
    return f"""
    <div class="detail-block">
      <h3>委託先一覧</h3>
      <table class="records-table">
        <thead>
          <tr><th>ID</th><th>名前</th><th>業務内容</th><th>個人情報取扱い</th><th>状態</th></tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
    """


def _render_control_detail(
    state: VendorDemoState, control_suggestions: list[ControlSuggestion]
) -> str:
    control = state.control
    frequency_label = assessment_frequency_label(control)
    suggestion = find_control_suggestion(control_suggestions, "vendor_management")
    return f"""
    <div class="detail-block">
      <h3>委託先管理策</h3>
      <ul>
        <li>管理策名：{_escape(control.name)}</li>
        <li>採用状態（初期設定での判断）：{_setup_adoption_label(suggestion)}</li>
        <li>初回評価：{"必須" if control.initial_assessment_required else "任意"}</li>
        <li>契約確認：{"必須" if control.contract_check_required else "任意"}</li>
        <li>定期評価：{"必須" if control.periodic_assessment_required else "任意"}</li>
        <li>評価頻度：{frequency_label}</li>
      </ul>
    </div>
    """


def _render_policy_detail() -> str:
    items = "".join(f"<li>{_escape(clause)}</li>" for clause in POLICY_CLAUSES)
    return f"""
    <div class="detail-block">
      <h3>規程内容（プレビュー）</h3>
      <p>委託先管理に関する標準規程条項の抜粋です。今回のMVPでは文書としての生成は行いません。</p>
      <ol>{items}</ol>
    </div>
    """


def _render_assessment_status_detail(state: VendorDemoState) -> str:
    vendors_by_id = {vendor.id: vendor for vendor in state.vendors}
    rows = "".join(
        "<tr>"
        f"<td>{assessment.vendor_id}</td>"
        f"<td>{_escape(vendors_by_id[assessment.vendor_id].name)}</td>"
        f"<td>{_initial_assessment_label(assessment)}</td>"
        f"<td>{_date_label(assessment.latest_assessment_date)}</td>"
        f"<td>{_date_label(assessment.next_assessment_due)}</td>"
        f"<td>{_assessment_result_label(assessment)}</td>"
        "</tr>"
        for assessment in state.assessments
        if assessment.vendor_id in vendors_by_id
    )
    return f"""
    <div class="detail-block">
      <h3>評価状況</h3>
      <table class="records-table">
        <thead>
          <tr>
            <th>ID</th><th>名前</th><th>初回評価</th><th>直近評価日</th>
            <th>次回評価期限</th><th>評価結果</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
    """


def _render_contract_status_detail(state: VendorDemoState) -> str:
    vendors_by_id = {vendor.id: vendor for vendor in state.vendors}
    rows = "".join(
        "<tr>"
        f"<td>{contract.vendor_id}</td>"
        f"<td>{_escape(vendors_by_id[contract.vendor_id].name)}</td>"
        f"<td>{_contract_label(contract)}</td>"
        "</tr>"
        for contract in state.contracts
        if contract.vendor_id in vendors_by_id
    )
    return f"""
    <div class="detail-block">
      <h3>契約状況</h3>
      <table class="records-table">
        <thead>
          <tr><th>ID</th><th>名前</th><th>契約確認</th></tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
    """


def _render_judgement_detail(state: VendorDemoState, result: VendorEvaluationResult) -> str:
    if not result.issues:
        return """
        <div class="detail-block">
          <h3>判定詳細</h3>
          <p>不足はありません。</p>
        </div>
        """

    items = []
    for issue in result.issues:
        names = _vendor_names(state, issue.vendor_ids)
        names_html = f"<br>対象：{names}" if names else ""
        items.append(
            f"<li><strong>{issue.rule_id}</strong>：{_escape(issue.message)}{names_html}</li>"
        )

    return f"""
    <div class="detail-block">
      <h3>判定詳細</h3>
      <ul>{"".join(items)}</ul>
    </div>
    """


def _render_details_section(
    state: VendorDemoState,
    result: VendorEvaluationResult,
    control_suggestions: list[ControlSuggestion],
) -> str:
    return f"""
    <details class="detail">
      <summary>詳細を見る</summary>
      {_render_vendor_list_detail(state)}
      {_render_control_detail(state, control_suggestions)}
      {_render_policy_detail()}
      {_render_assessment_status_detail(state)}
      {_render_contract_status_detail(state)}
      {_render_judgement_detail(state, result)}
    </details>
    """


def _render_reset_section() -> str:
    return """
    <section class="reset">
      <form method="post" action="/vendors/reset">
        <button type="submit">デモを初期状態に戻す</button>
      </form>
    </section>
    """


# ---------------------------------------------------------------------------
# ページ全体
# ---------------------------------------------------------------------------


def render_vendor_page(
    state: VendorDemoState,
    result: VendorEvaluationResult,
    control_suggestions: list[ControlSuggestion],
    flash: str | None = None,
) -> str:
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <title>委託先管理 - Pマーク取得・運用支援ツール MVP</title>
  <style>
    body {{ font-family: sans-serif; margin: 2rem; line-height: 1.6; max-width: 900px; }}
    h1 {{ margin-bottom: 0.5rem; }}
    section, details {{ margin-bottom: 1.5rem; }}
    .flash-message {{
      padding: 0.6rem 1rem; margin-bottom: 1rem; border-radius: 4px;
      background: #eefaf0; border-left: 4px solid #0a7a0a; font-weight: bold;
    }}
    .adoption-notice {{
      padding: 0.6rem 1rem; margin-bottom: 1rem; border-radius: 4px;
      background: #f5f5f5; border-left: 4px solid #888; color: #555;
    }}
    .status-summary {{ padding: 1rem; border: 1px solid #ccc; border-radius: 4px; }}
    .control-title {{ font-size: 1.1rem; font-weight: bold; margin: 0 0 0.5rem; }}
    .status-badge {{
      display: inline-block; padding: 0.3rem 0.8rem; border-radius: 4px; font-size: 1.1rem;
    }}
    .status-badge.needs-action {{ background: #b30000; color: #fff; }}
    .status-badge.compliant {{ background: #0a7a0a; color: #fff; }}
    .status-badge.not-started {{ background: #666; color: #fff; }}
    .issue-count {{ font-weight: bold; }}
    .status-figures {{ margin: 0.5rem 0 0; padding-left: 1.2rem; }}
    .todo-list {{ list-style: none; margin: 0; padding: 0; }}
    .todo-item {{
      padding: 0.75rem 1rem; margin-bottom: 0.75rem; border-radius: 4px;
    }}
    .todo-item.warning {{ background: #fff8ef; border-left: 4px solid #d9822b; }}
    .todo-headline {{ font-weight: bold; margin: 0 0 0.3rem; }}
    .todo-explain {{ margin: 0 0 0.5rem; color: #555; font-size: 0.9rem; }}
    .todo-names {{ margin: 0 0 0.5rem; color: #555; }}
    .todo-empty.complete {{
      padding: 0.75rem 1rem; background: #eefaf0; border-left: 4px solid #0a7a0a;
    }}
    .records-table {{ border-collapse: collapse; }}
    .records-table th, .records-table td {{ text-align: left; border: 1px solid #ccc; padding: 4px 8px; }}
    .detail-block {{ margin-bottom: 1.5rem; }}
    form {{ display: inline-block; margin: 0; }}
  </style>
</head>
<body>
  <p><a href="/">&laquo; トップへ戻る</a></p>
  <h1>委託先管理</h1>
  {_render_flash(flash)}
  {_render_adoption_notice(control_suggestions)}

  {_render_status_summary(state, result)}
  {_render_todo_section(state, result)}
  {_render_problem_vendors_section(state, result)}
  {_render_details_section(state, result, control_suggestions)}
  {_render_reset_section()}
</body>
</html>
"""
