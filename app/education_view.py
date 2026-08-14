"""教育管理デモ画面のHTML描画。

ここでは業務判定を一切行わない。渡された EducationEvaluationResult
（app.education.evaluate_training の結果）をそのまま表示するだけとする。
"""

from __future__ import annotations

from app.demo_state import POLICY_CLAUSES, EducationDemoState
from app.schemas import (
    ComprehensionResult,
    EducationEvaluationResult,
    EducationEvaluationStatus,
    Employee,
    EmployeeRole,
    TrainingRecord,
)

ROLE_LABELS = {
    EmployeeRole.EXECUTIVE: "経営者",
    EmployeeRole.PRIVACY_MANAGER: "個人情報保護管理者",
    EmployeeRole.PMARK_STAFF: "Pマーク担当者",
    EmployeeRole.GENERAL_EMPLOYEE: "一般従業員",
}

# 優先表示件数（未受講・要確認者を優先し、全50名は常時表示しない）。
RECORD_PREVIEW_LIMIT = 10


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _role_label(role: EmployeeRole) -> str:
    return ROLE_LABELS.get(role, role.value)


def _frequency_label(control) -> str:
    return "年1回" if control.frequency.value == "annual" else control.frequency.value


def _render_company_section(state: EducationDemoState) -> str:
    company = state.company
    return f"""
    <section>
      <h2>A. 会社情報</h2>
      <ul>
        <li>会社名：{_escape(company.name)}</li>
        <li>従業者数：{len(state.employees)}名</li>
        <li>対象年度：{company.fiscal_year}年度</li>
      </ul>
    </section>
    """


def _render_control_section(state: EducationDemoState) -> str:
    control = state.control
    roles = "、".join(_role_label(role) for role in control.target_roles)
    return f"""
    <section>
      <h2>B. 教育管理策</h2>
      <ul>
        <li>管理策名：{_escape(control.name)}</li>
        <li>採用状態：{"採用中" if control.adopted else "未採用"}</li>
        <li>実施頻度：{_frequency_label(control)}</li>
        <li>対象role：{roles}</li>
        <li>理解度確認：{"必須" if control.comprehension_required else "任意"}</li>
        <li>教材証跡：{"必須" if control.material_evidence_required else "任意"}</li>
        <li>承認：{"必須" if control.approval_required else "任意"}</li>
      </ul>
    </section>
    """


def _render_policy_section() -> str:
    items = "".join(f"<li>{_escape(clause)}</li>" for clause in POLICY_CLAUSES)
    return f"""
    <section>
      <h2>C. 規程内容（プレビュー）</h2>
      <p>教育に関する標準規程条項の抜粋です。今回のMVPでは文書としての生成は行いません。</p>
      <ol>{items}</ol>
    </section>
    """


def _render_plan_section(state: EducationDemoState, result: EducationEvaluationResult) -> str:
    plan = state.plan
    return f"""
    <section>
      <h2>D. 年間教育計画</h2>
      <ul>
        <li>教育名称：{_escape(plan.title)}</li>
        <li>対象年度：{plan.fiscal_year}年度</li>
        <li>実施頻度：{_frequency_label(state.control)}</li>
        <li>対象者数：{len(result.target_employee_ids)}名</li>
        <li>状態：<strong>{result.status.value}</strong></li>
      </ul>
    </section>
    """


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


def _record_priority(record: TrainingRecord | None) -> int:
    """未受講・理解度未登録を優先表示するための並び順。値が小さいほど優先。"""

    if record is None or not record.completed:
        return 0
    if record.comprehension_result is None:
        return 1
    return 2


def _render_records_section(state: EducationDemoState, result: EducationEvaluationResult) -> str:
    records_by_employee = {record.employee_id: record for record in state.records}
    target_ids = set(result.target_employee_ids)
    target_employees = [employee for employee in state.employees if employee.id in target_ids]

    sorted_employees: list[Employee] = sorted(
        target_employees,
        key=lambda employee: (_record_priority(records_by_employee.get(employee.id)), employee.id),
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
    <section>
      <h2>E. 教育実績（対象{len(target_employees)}名中、未受講・要確認者を優先表示）</h2>
      <table border="1" cellpadding="4" cellspacing="0">
        <thead>
          <tr><th>ID</th><th>名前</th><th>role</th><th>受講状態</th><th>理解度確認</th></tr>
        </thead>
        <tbody>{rows_html}</tbody>
      </table>
      {footer}
    </section>
    """


def _render_evaluation_section(
    state: EducationDemoState, result: EducationEvaluationResult
) -> str:
    employees_by_id = {employee.id: employee for employee in state.employees}
    status_class = (
        "compliant" if result.status == EducationEvaluationStatus.COMPLIANT else "needs-action"
    )

    if result.issues:
        issue_items = []
        for issue in result.issues:
            names = "、".join(
                _escape(employees_by_id[employee_id].name)
                for employee_id in issue.employee_ids
                if employee_id in employees_by_id
            )
            names_html = f"<br>対象者：{names}" if names else ""
            issue_items.append(
                f"<li><strong>{issue.rule_id}</strong>：{_escape(issue.message)}{names_html}</li>"
            )
        issues_html = f"<ul>{''.join(issue_items)}</ul>"
    else:
        issues_html = "<p>不足はありません。</p>"

    return f"""
    <section>
      <h2>F. 整合性チェック結果</h2>
      <p class="{status_class}">
        現在の状態：<strong>{result.status.value}</strong>（問題件数：{len(result.issues)}件）
      </p>
      {issues_html}
    </section>
    """


def _render_actions_section() -> str:
    return """
    <section>
      <h2>不足を解消する</h2>
      <p>各操作の後、判定は自動的に再評価されます（既存の evaluate_training を再実行）。</p>
      <form method="post" action="/education/actions/complete-trainings">
        <button type="submit">操作1：未受講者を受講済みにする</button>
      </form>
      <form method="post" action="/education/actions/register-comprehension">
        <button type="submit">操作2：理解度確認結果を登録する（pass）</button>
      </form>
      <form method="post" action="/education/actions/register-material-evidence">
        <button type="submit">操作3：教材証跡を登録済みにする</button>
      </form>
      <form method="post" action="/education/actions/approve">
        <button type="submit">操作4：実施結果を承認する</button>
      </form>
      <form method="post" action="/education/reset">
        <button type="submit">デモを初期状態に戻す</button>
      </form>
    </section>
    """


def render_education_page(state: EducationDemoState, result: EducationEvaluationResult) -> str:
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <title>教育管理デモ - Pマーク取得・運用支援ツール MVP</title>
  <style>
    body {{ font-family: sans-serif; margin: 2rem; line-height: 1.6; max-width: 900px; }}
    section {{ margin-bottom: 2rem; padding-bottom: 1rem; border-bottom: 1px solid #ccc; }}
    table {{ border-collapse: collapse; }}
    th, td {{ text-align: left; }}
    .compliant {{ color: #0a7a0a; }}
    .needs-action {{ color: #b30000; }}
    form {{ display: inline-block; margin-right: 0.5rem; margin-bottom: 0.5rem; }}
  </style>
</head>
<body>
  <p><a href="/">&laquo; トップへ戻る</a></p>
  <h1>教育管理デモ：{_escape(state.company.name)}</h1>
  {_render_company_section(state)}
  {_render_control_section(state)}
  {_render_policy_section()}
  {_render_plan_section(state, result)}
  {_render_records_section(state, result)}
  {_render_evaluation_section(state, result)}
  {_render_actions_section()}
</body>
</html>
"""
