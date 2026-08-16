"""教育管理画面へ、実施記録・証跡を登録する入力UIを追加する。

既存の education_view は状態サマリー・不足一覧・詳細表示を担当しているため、
本モジュールではそのHTMLへ記録入力パネルを差し込み、デモ用ワンクリック操作を
「事実を登録する」導線へ置き換える。業務判定は行わない。

入力負担を抑えるため、現在必要な1工程だけを表示し、保存後に次工程へ進む。
STEP0や前工程で分かっている値は初期値として再利用する。
"""

from __future__ import annotations

from html import escape

from app import company_profile
from app.demo_state import EducationDemoState
from app.schemas import EducationEvaluationResult


_OLD_ACTION_FORMS = {
    "complete-trainings": (
        '<form method="post" action="/education/actions/complete-trainings">'
        '<button type="submit">未受講者を受講済みにする</button></form>'
    ),
    "register-comprehension": (
        '<form method="post" action="/education/actions/register-comprehension">'
        '<button type="submit">理解度確認結果を登録する（合格）</button></form>'
    ),
    "register-material-evidence": (
        '<form method="post" action="/education/actions/register-material-evidence">'
        '<button type="submit">教材記録を登録する</button></form>'
    ),
    "approve": (
        '<form method="post" action="/education/actions/approve">'
        '<button type="submit">承認する</button></form>'
    ),
}


def _has_issue(result: EducationEvaluationResult, rule_id: str) -> bool:
    return any(issue.rule_id == rule_id for issue in result.issues)


def _issue_employee_names(
    state: EducationDemoState, result: EducationEvaluationResult, rule_id: str
) -> str:
    issue = next((issue for issue in result.issues if issue.rule_id == rule_id), None)
    if issue is None:
        return ""
    employees = {employee.id: employee.name for employee in state.employees}
    return "、".join(
        escape(employees[employee_id])
        for employee_id in issue.employee_ids
        if employee_id in employees
    )


def _value(value: str | None) -> str:
    return escape(value or "未登録")


def _selected(current: str | None, value: str) -> str:
    return " selected" if current == value else ""


def _render_record_summary(state: EducationDemoState) -> str:
    plan = state.plan
    return f"""
    <div style="background:#f7f7f7; padding:12px; margin:12px 0 18px 0;">
      <strong>現在の教育実施記録</strong>
      <ul>
        <li>実施日：{_value(plan.execution_date)}</li>
        <li>実施方法：{_value(plan.delivery_method)}</li>
        <li>教材：{_value(plan.material_name)}</li>
        <li>実施責任者：{_value(plan.instructor_name)}</li>
        <li>理解度確認方法：{_value(plan.comprehension_method)}</li>
        <li>承認：{_value(plan.approved_by)} / {_value(plan.approved_at)}</li>
      </ul>
    </div>
    """


def _render_execution_form(state: EducationDemoState) -> str:
    plan = state.plan
    profile = company_profile.get_state()
    material_name = plan.material_name or f"{plan.fiscal_year}年度 個人情報保護教育資料"
    instructor_name = (
        plan.instructor_name
        or profile.application_contact_name
        or profile.application_contact_department_role
        or "Pマーク担当者"
    )
    return f"""
    <div style="border:1px solid #ddd; padding:12px; margin:10px 0;">
      <h3 style="margin-top:0;">1. 教育実施・教材記録</h3>
      <p>まず、実施した教育を後から説明できる最低限の情報を登録します。</p>
      <form method="post" action="/education/actions/register-material-evidence" style="display:block;">
        <label>実施日 <input type="date" name="execution_date" value="{escape(plan.execution_date or '')}" required></label><br><br>
        <label>実施方法
          <select name="delivery_method" required>
            <option value="">選択してください</option>
            <option value="集合研修"{_selected(plan.delivery_method, '集合研修')}>集合研修</option>
            <option value="オンライン研修"{_selected(plan.delivery_method, 'オンライン研修')}>オンライン研修</option>
            <option value="eラーニング"{_selected(plan.delivery_method, 'eラーニング')}>eラーニング</option>
            <option value="資料配布・自己学習"{_selected(plan.delivery_method, '資料配布・自己学習')}>資料配布・自己学習</option>
          </select>
        </label><br><br>
        <label>教材名 <input type="text" name="material_name" value="{escape(material_name)}" required></label><br><br>
        <label>実施責任者 <input type="text" name="instructor_name" value="{escape(instructor_name)}" required></label><br><br>
        <button type="submit">教育実施・教材記録を保存して次へ</button>
      </form>
    </div>
    """


def _render_completion_form(state: EducationDemoState, result: EducationEvaluationResult) -> str:
    names = _issue_employee_names(state, result, "EDU-003")
    completed_on = state.plan.execution_date or ""
    return f"""
    <div style="border:1px solid #ddd; padding:12px; margin:10px 0;">
      <h3 style="margin-top:0;">2. 受講記録</h3>
      <p>未受講として残っている対象者：{names}</p>
      <p>対象者は自動抽出済みです。同日に受講した場合は日付だけ確認してください。</p>
      <form method="post" action="/education/actions/complete-trainings" style="display:block;">
        <label>受講日 <input type="date" name="completed_on" value="{escape(completed_on)}" required></label>
        <button type="submit">上記対象者の受講記録を保存して次へ</button>
      </form>
    </div>
    """


def _render_comprehension_form(state: EducationDemoState, result: EducationEvaluationResult) -> str:
    names = _issue_employee_names(state, result, "EDU-006")
    method = state.plan.comprehension_method
    return f"""
    <div style="border:1px solid #ddd; padding:12px; margin:10px 0;">
      <h3 style="margin-top:0;">3. 理解度確認記録</h3>
      <p>結果が未登録の対象者：{names}</p>
      <p>対象者は自動抽出済みです。共通の確認方法・結果をまとめて登録できます。</p>
      <form method="post" action="/education/actions/register-comprehension" style="display:block;">
        <label>確認方法
          <select name="comprehension_method" required>
            <option value="">選択してください</option>
            <option value="理解度確認テスト"{_selected(method, '理解度確認テスト')}>理解度確認テスト</option>
            <option value="確認アンケート"{_selected(method, '確認アンケート')}>確認アンケート</option>
            <option value="口頭確認"{_selected(method, '口頭確認')}>口頭確認</option>
          </select>
        </label>
        <label>結果
          <select name="result" required>
            <option value="passed">合格・確認済み</option>
            <option value="failed">不合格・要再教育</option>
          </select>
        </label>
        <button type="submit">理解度確認結果を保存して次へ</button>
      </form>
    </div>
    """


def _render_reeducation_notice(state: EducationDemoState, result: EducationEvaluationResult) -> str:
    names = _issue_employee_names(state, result, "EDU-007")
    return f"""
    <div style="border:1px solid #e1a100; background:#fff9e8; padding:12px; margin:10px 0;">
      <h3 style="margin-top:0;">4. 再教育が必要です</h3>
      <p>理解度確認で要再教育となった対象者：{names}</p>
      <p>再教育の実施・再確認記録は次の拡張対象です。現時点ではこの状態のまま承認へは進めません。</p>
    </div>
    """


def _render_approval_form(state: EducationDemoState) -> str:
    profile = company_profile.get_state()
    approver = state.plan.approved_by or profile.privacy_manager_name
    return f"""
    <div style="border:1px solid #ddd; padding:12px; margin:10px 0;">
      <h3 style="margin-top:0;">4. 教育実施結果の承認</h3>
      <p>個人情報保護管理者が実施結果と記録を確認したうえで承認します。</p>
      <form method="post" action="/education/actions/approve" style="display:block;">
        <label>承認者 <input type="text" name="approved_by" value="{escape(approver or '')}" placeholder="個人情報保護管理者氏名" required></label><br><br>
        <label>承認日 <input type="date" name="approved_at" value="{escape(state.plan.approved_at or '')}" required></label>
        <button type="submit">承認記録を保存して完了</button>
      </form>
    </div>
    """


def _render_current_action(state: EducationDemoState, result: EducationEvaluationResult) -> str:
    """教育実施記録の現在工程を1つだけ返す。"""

    if _has_issue(result, "EDU-008"):
        return _render_execution_form(state)
    if _has_issue(result, "EDU-003"):
        return _render_completion_form(state, result)
    if _has_issue(result, "EDU-006"):
        return _render_comprehension_form(state, result)
    if _has_issue(result, "EDU-007"):
        return _render_reeducation_notice(state, result)
    if _has_issue(result, "EDU-009"):
        return _render_approval_form(state)
    return "<p>必要な教育実施記録は登録済みです。</p>"


def render_record_panel(state: EducationDemoState, result: EducationEvaluationResult) -> str:
    """現在必要な1工程だけを表示する教育実施記録パネルを返す。"""

    return f"""
    <section id="education-record" style="margin:24px 0;">
      <h2>教育実施記録</h2>
      <p>実施した事実と証跡を順番に登録します。完了した項目は再入力する必要はありません。</p>
      {_render_record_summary(state)}
      {_render_current_action(state, result)}
    </section>
    """


def enhance_education_page(
    html: str, state: EducationDemoState, result: EducationEvaluationResult
) -> str:
    """既存教育画面へ記録パネルを追加し、ワンクリック操作を記録入力導線へ置換する。"""

    replacements = {
        _OLD_ACTION_FORMS["complete-trainings"]: '<a href="#education-record">教育実施記録で対応する</a>',
        _OLD_ACTION_FORMS["register-comprehension"]: '<a href="#education-record">教育実施記録で対応する</a>',
        _OLD_ACTION_FORMS["register-material-evidence"]: '<a href="#education-record">教育実施記録で対応する</a>',
        _OLD_ACTION_FORMS["approve"]: '<a href="#education-record">教育実施記録で対応する</a>',
    }
    for old, new in replacements.items():
        html = html.replace(old, new)

    marker = '<section class="todo">'
    panel = render_record_panel(state, result)
    if marker in html:
        return html.replace(marker, panel + marker, 1)
    return html.replace("</h1>", "</h1>" + panel, 1)
