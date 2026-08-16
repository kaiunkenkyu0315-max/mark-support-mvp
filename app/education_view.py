"""教育管理デモ画面のHTML描画。

ここでは業務判定を一切行わない。渡された EducationEvaluationResult
（app.education.evaluate_training の結果）をそのまま表示するだけとする。

画面は「今どういう状態か」「何が不足しているか」「次に何をすればいいか」を
最初に伝えることを優先し、会社情報・管理策・規程・全体実績などの詳細情報は
<details> にまとめて後段に置く。
"""

from __future__ import annotations

from app.control_status import operational_status
from app.demo_state import POLICY_CLAUSES, EducationDemoState
from app.education import ROLE_LABELS, frequency_label
from app.intake import CONTROL_STATUS_LABELS, find_control_suggestion
from app.intake_schemas import ControlDecisionStatus, ControlSuggestion
from app.schemas import (
    ComprehensionResult,
    EducationEvaluationResult,
    EducationEvaluationStatus,
    EducationIssue,
    Employee,
    EmployeeRole,
    TrainingRecord,
)

# 全体実績（詳細情報内）での優先表示件数。未受講・要確認者を優先し、全50名は常時表示しない。
RECORD_PREVIEW_LIMIT = 10

# 不足事項（rule_id）を、利用者向けの見出し・対応ボタン・短い説明へ変換するための表示定義。
# rule_idそのものはここでは主表示に使わず、判定詳細（詳細情報内）でのみ表示する。
# explainは「何を確認／登録すれば解消するのか」の一文（長文ヘルプにはしない）。
ISSUE_DISPLAY = {
    "EDU-003": {
        "headline": "未受講者がいます",
        "explain": "対象者に個人情報保護教育を受講してもらい、受講記録を登録してください。",
        "action_label": "未受講者を受講済みにする",
        "action_url": "/education/actions/complete-trainings",
    },
    "EDU-006": {
        "headline": "理解度確認が未登録の受講者がいます",
        "explain": "受講後の理解度確認（テスト等）の結果を、対象者ごとに登録してください。",
        "action_label": "理解度確認結果を登録する（合格）",
        "action_url": "/education/actions/register-comprehension",
    },
    "EDU-008": {
        "headline": "教材の記録がありません",
        "explain": "今回の教育で使用した教材を識別できる情報を登録してください。",
        "action_label": "教材記録を登録する",
        "action_url": "/education/actions/register-material-evidence",
    },
    "EDU-009": {
        "headline": "教育実施結果が未承認です",
        "explain": "個人情報保護管理者が、今年度の教育実施結果を確認し承認してください。",
        "action_label": "承認する",
        "action_url": "/education/actions/approve",
    },
}


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _role_label(role: EmployeeRole) -> str:
    return ROLE_LABELS.get(role, role.value)


def _frequency_label(control) -> str:
    return frequency_label(control)


def _training_status_label(record: TrainingRecord | None) -> str:
    if record is None or not record.completed:
        return "未受講"
    return "受講済み"


def _comprehension_label(record: TrainingRecord | None) -> str:
    if record is None or not record.completed:
        return "-"
    if record.comprehension_result is None:
        return "未登録"
    if record.comprehension_result == ComprehensionResult.PASSED:
        return "確認済み（合格）"
    return "確認済み（不合格）"


def _issue_by_rule(result: EducationEvaluationResult, rule_id: str) -> EducationIssue | None:
    return next((issue for issue in result.issues if issue.rule_id == rule_id), None)


def _setup_adoption_label(suggestion: ControlSuggestion | None) -> str:
    """初期設定での採用判断（正本）を表示用ラベルへ変換する。

    この管理策自体（TrainingControl）は採用可否の判断を持たないため、
    ここでは必ず初期設定側のControlSuggestionを参照する。
    """

    if suggestion is None:
        return "未確認（初期設定で未回答）"
    return CONTROL_STATUS_LABELS[suggestion.status]


def _render_adoption_notice(control_suggestions: list[ControlSuggestion]) -> str:
    """この管理策が初期設定で採用済みかどうかを、画面冒頭で明示する。

    未採用（未提示／採用判断待ち／非適用）の間は、以下に表示される実績・不足が
    正式な運用上の要対応ではないことが分かるようにする。
    """

    suggestion = find_control_suggestion(control_suggestions, "education")
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


def _employee_names(state: EducationDemoState, employee_ids: list[int]) -> str:
    employees_by_id = {employee.id: employee for employee in state.employees}
    return "、".join(
        _escape(employees_by_id[employee_id].name)
        for employee_id in employee_ids
        if employee_id in employees_by_id
    )


# ---------------------------------------------------------------------------
# 1. 現在の状態サマリー
# ---------------------------------------------------------------------------


def _render_status_summary(state: EducationDemoState, result: EducationEvaluationResult) -> str:
    status_class = (
        "compliant" if result.status == EducationEvaluationStatus.COMPLIANT else "needs-action"
    )

    not_completed_issue = _issue_by_rule(result, "EDU-003")
    comprehension_issue = _issue_by_rule(result, "EDU-006")
    not_completed_count = len(not_completed_issue.employee_ids) if not_completed_issue else 0
    missing_comprehension_count = (
        len(comprehension_issue.employee_ids) if comprehension_issue else 0
    )
    target_count = len(result.target_employee_ids)
    completed_count = target_count - not_completed_count

    return f"""
    <section class="status-summary">
      <p class="fiscal-title">{state.plan.fiscal_year}年度 {_escape(state.control.name)}</p>
      <p class="status-badge {status_class}">現在の状態：<strong>{result.status.value}</strong></p>
      <p class="issue-count">対応が必要な項目：{len(result.issues)}件</p>
      <ul class="status-figures">
        <li>対象者：{target_count}名</li>
        <li>受講済み：{completed_count}名</li>
        <li>未受講：{not_completed_count}名</li>
        <li>理解度確認未登録：{missing_comprehension_count}名</li>
      </ul>
    </section>
    """


# ---------------------------------------------------------------------------
# 2. 今やること（不足事項＋対応操作）
# ---------------------------------------------------------------------------


def _render_todo_section(state: EducationDemoState, result: EducationEvaluationResult) -> str:
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
        names = _employee_names(state, issue.employee_ids)
        names_html = f'<p class="todo-names">対象者：{names}</p>' if names else ""

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
# 3. 教育実績の問題対象者
# ---------------------------------------------------------------------------


def _render_problem_employees_section(
    state: EducationDemoState, result: EducationEvaluationResult
) -> str:
    employees_by_id = {employee.id: employee for employee in state.employees}
    records_by_employee = {record.employee_id: record for record in state.records}

    problem_ids: list[int] = []
    seen: set[int] = set()
    for issue in result.issues:
        for employee_id in issue.employee_ids:
            if employee_id not in seen:
                seen.add(employee_id)
                problem_ids.append(employee_id)

    if not problem_ids:
        return """
        <section class="problem-employees">
          <h2>教育実績の問題対象者</h2>
          <p>問題のある対象者はいません。</p>
        </section>
        """

    rows = []
    for employee_id in problem_ids:
        employee = employees_by_id.get(employee_id)
        if employee is None:
            continue
        record = records_by_employee.get(employee_id)
        rows.append(
            "<tr>"
            f"<td>{employee.id}</td>"
            f"<td>{_escape(employee.name)}</td>"
            f"<td>{_role_label(employee.role)}</td>"
            f"<td>{_training_status_label(record)}</td>"
            f"<td>{_comprehension_label(record)}</td>"
            "</tr>"
        )

    return f"""
    <section class="problem-employees">
      <h2>教育実績の問題対象者</h2>
      <table class="records-table">
        <thead>
          <tr><th>ID</th><th>名前</th><th>役割</th><th>受講状態</th><th>理解度確認</th></tr>
        </thead>
        <tbody>{"".join(rows)}</tbody>
      </table>
    </section>
    """


# ---------------------------------------------------------------------------
# 4. 詳細情報（会社情報・管理策・規程・年間計画・全体実績・判定詳細）
# ---------------------------------------------------------------------------


def _render_company_detail(state: EducationDemoState) -> str:
    company = state.company
    return f"""
    <div class="detail-block">
      <h3>会社情報</h3>
      <ul>
        <li>会社名：{_escape(company.name)}</li>
        <li>従業者数：{len(state.employees)}名</li>
        <li>対象年度：{company.fiscal_year}年度</li>
      </ul>
    </div>
    """


def _render_control_detail(
    state: EducationDemoState, control_suggestions: list[ControlSuggestion]
) -> str:
    control = state.control
    roles = "、".join(_role_label(role) for role in control.target_roles)
    suggestion = find_control_suggestion(control_suggestions, "education")
    return f"""
    <div class="detail-block">
      <h3>教育管理策</h3>
      <ul>
        <li>管理策名：{_escape(control.name)}</li>
        <li>採用状態（初期設定での判断）：{_setup_adoption_label(suggestion)}</li>
        <li>実施頻度：{_frequency_label(control)}</li>
        <li>教育対象：{roles}</li>
        <li>理解度確認：{"必須" if control.comprehension_required else "任意"}</li>
        <li>教材証跡：{"必須" if control.material_evidence_required else "任意"}</li>
        <li>承認：{"必須" if control.approval_required else "任意"}</li>
      </ul>
    </div>
    """


def _render_policy_detail() -> str:
    items = "".join(f"<li>{_escape(clause)}</li>" for clause in POLICY_CLAUSES)
    return f"""
    <div class="detail-block">
      <h3>規程内容（プレビュー）</h3>
      <p>教育に関する標準規程条項の抜粋です。今回のMVPでは文書としての生成は行いません。</p>
      <ol>{items}</ol>
    </div>
    """


def _render_plan_detail(state: EducationDemoState, result: EducationEvaluationResult) -> str:
    plan = state.plan
    return f"""
    <div class="detail-block">
      <h3>年間教育計画</h3>
      <ul>
        <li>教育名称：{_escape(plan.title)}</li>
        <li>対象年度：{plan.fiscal_year}年度</li>
        <li>実施頻度：{_frequency_label(state.control)}</li>
        <li>対象者数：{len(result.target_employee_ids)}名</li>
        <li>状態：<strong>{result.status.value}</strong></li>
      </ul>
    </div>
    """


def _record_priority(record: TrainingRecord | None) -> int:
    """未受講・理解度未登録を優先表示するための並び順。値が小さいほど優先。"""

    if record is None or not record.completed:
        return 0
    if record.comprehension_result is None:
        return 1
    return 2


def _render_full_records_detail(
    state: EducationDemoState, result: EducationEvaluationResult
) -> str:
    records_by_employee = {record.employee_id: record for record in state.records}
    target_ids = set(result.target_employee_ids)
    target_employees = [employee for employee in state.employees if employee.id in target_ids]

    sorted_employees: list[Employee] = sorted(
        target_employees,
        key=lambda employee: (
            _record_priority(records_by_employee.get(employee.id)),
            employee.id,
        ),
    )

    preview_employees = sorted_employees[:RECORD_PREVIEW_LIMIT]
    remaining_count = len(sorted_employees) - len(preview_employees)

    rows = []
    for employee in preview_employees:
        record = records_by_employee.get(employee.id)
        rows.append(
            "<tr>"
            f"<td>{employee.id}</td>"
            f"<td>{_escape(employee.name)}</td>"
            f"<td>{_role_label(employee.role)}</td>"
            f"<td>{_training_status_label(record)}</td>"
            f"<td>{_comprehension_label(record)}</td>"
            "</tr>"
        )
    rows_html = "".join(rows)

    footer = (
        f"<p>他{remaining_count}名は受講・理解度確認とも問題ありません。</p>"
        if remaining_count > 0
        else ""
    )

    return f"""
    <div class="detail-block">
      <h3>全体実績（対象{len(target_employees)}名中、未受講・要確認者を優先表示）</h3>
      <table class="records-table">
        <thead>
          <tr><th>ID</th><th>名前</th><th>役割</th><th>受講状態</th><th>理解度確認</th></tr>
        </thead>
        <tbody>{rows_html}</tbody>
      </table>
      {footer}
    </div>
    """


def _render_judgement_detail(state: EducationDemoState, result: EducationEvaluationResult) -> str:
    if not result.issues:
        return """
        <div class="detail-block">
          <h3>判定詳細</h3>
          <p>不足はありません。</p>
        </div>
        """

    items = []
    for issue in result.issues:
        names = _employee_names(state, issue.employee_ids)
        names_html = f"<br>対象者：{names}" if names else ""
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
    state: EducationDemoState,
    result: EducationEvaluationResult,
    control_suggestions: list[ControlSuggestion],
) -> str:
    return f"""
    <details class="detail">
      <summary>詳細を見る</summary>
      {_render_company_detail(state)}
      {_render_control_detail(state, control_suggestions)}
      {_render_policy_detail()}
      {_render_plan_detail(state, result)}
      {_render_full_records_detail(state, result)}
      {_render_judgement_detail(state, result)}
    </details>
    """


def _render_reset_section() -> str:
    return """
    <section class="reset">
      <form method="post" action="/education/reset">
        <button type="submit">デモを初期状態に戻す</button>
      </form>
    </section>
    """


# ---------------------------------------------------------------------------
# ページ全体
# ---------------------------------------------------------------------------


def render_education_page(
    state: EducationDemoState,
    result: EducationEvaluationResult,
    control_suggestions: list[ControlSuggestion],
    flash: str | None = None,
) -> str:
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <title>教育管理 - Pマーク取得・運用支援ツール MVP</title>
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
    .fiscal-title {{ font-size: 1.1rem; font-weight: bold; margin: 0 0 0.5rem; }}
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
  <h1>教育管理：{_escape(state.company.name)}</h1>
  {_render_flash(flash)}
  {_render_adoption_notice(control_suggestions)}

  {_render_status_summary(state, result)}
  {_render_todo_section(state, result)}
  {_render_problem_employees_section(state, result)}
  {_render_details_section(state, result, control_suggestions)}
  {_render_reset_section()}
</body>
</html>
"""
