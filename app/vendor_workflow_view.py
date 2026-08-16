"""委託先管理画面を「全体工程 → 現在地 → 今やる1件 → 記録入力」に整える。

既存 vendor_view は状態サマリー・問題委託先・詳細情報を担当する。
本モジュールは、そのHTML内の従来のワンクリックToDoを、
全体工程と構造化記録フォームへ置き換える。
"""

from __future__ import annotations

from datetime import date
from html import escape

from app import company_profile
from app.vendor_demo_state import VendorDemoState
from app.vendor_schemas import AssessmentResult, VendorEvaluationResult


def _has_issue(result: VendorEvaluationResult, *rule_ids: str) -> bool:
    wanted = set(rule_ids)
    return any(issue.rule_id in wanted for issue in result.issues)


def _issue_vendor_ids(result: VendorEvaluationResult, *rule_ids: str) -> list[int]:
    wanted = set(rule_ids)
    found: list[int] = []
    seen: set[int] = set()
    for issue in result.issues:
        if issue.rule_id not in wanted:
            continue
        for vendor_id in issue.vendor_ids:
            if vendor_id not in seen:
                seen.add(vendor_id)
                found.append(vendor_id)
    return found


def _vendor_names(state: VendorDemoState, vendor_ids: list[int]) -> str:
    vendors = {vendor.id: vendor.name for vendor in state.vendors}
    return "、".join(escape(vendors[vendor_id]) for vendor_id in vendor_ids if vendor_id in vendors)


def _current_step(result: VendorEvaluationResult) -> int | None:
    if _has_issue(result, "VEN-001", "VEN-003"):
        return 1
    if _has_issue(result, "VEN-002"):
        return 2
    if _has_issue(result, "VEN-004", "VEN-006"):
        return 3
    return None


def _step_is_complete(result: VendorEvaluationResult, step: int) -> bool:
    if step == 1:
        return not _has_issue(result, "VEN-001", "VEN-003")
    if step == 2:
        return not _has_issue(result, "VEN-002")
    return not _has_issue(result, "VEN-004", "VEN-006")


def _assessor_default() -> str:
    profile = company_profile.get_state()
    return (
        profile.application_contact_name
        or profile.privacy_manager_name
        or profile.application_contact_department_role
        or "Pマーク担当者"
    )


def _progress_counts(state: VendorDemoState, result: VendorEvaluationResult) -> tuple[int, int, int, int]:
    target_ids = set(result.target_vendor_ids)
    assessments = {assessment.vendor_id: assessment for assessment in state.assessments}
    contracts = {contract.vendor_id: contract for contract in state.contracts}
    today = date.today()

    initial_count = sum(
        1
        for vendor_id in target_ids
        if (assessment := assessments.get(vendor_id)) is not None
        and assessment.initial_assessment_completed
        and assessment.initial_assessment_result != AssessmentResult.FAILED
    )
    contract_count = sum(
        1
        for vendor_id in target_ids
        if (contract := contracts.get(vendor_id)) is not None and contract.contract_confirmed
    )
    periodic_count = sum(
        1
        for vendor_id in target_ids
        if (assessment := assessments.get(vendor_id)) is not None
        and assessment.latest_assessment_date is not None
        and assessment.assessment_result == AssessmentResult.PASSED
        and (
            assessment.next_assessment_due is None
            or assessment.next_assessment_due >= today
        )
    )
    return len(target_ids), initial_count, contract_count, periodic_count


def _step_label(result: VendorEvaluationResult, step: int) -> str:
    if _step_is_complete(result, step):
        return "完了"
    if _current_step(result) == step:
        return "対応中 ← 現在"
    return "未完了"


def _render_overview(state: VendorDemoState, result: VendorEvaluationResult) -> str:
    total, initial_count, contract_count, periodic_count = _progress_counts(state, result)
    completed_steps = sum(1 for step in (1, 2, 3) if _step_is_complete(result, step))
    current = _current_step(result)
    current_label = {
        1: "1. 初回評価",
        2: "2. 契約確認",
        3: "3. 定期評価",
        None: "全工程完了",
    }[current]

    return f"""
    <section class="vendor-workflow-overview" style="border:1px solid #ccc; padding:16px; border-radius:4px; margin:24px 0;">
      <h2 style="margin-top:0;">委託先管理の全体工程</h2>
      <p>まず全体像と現在地を確認し、下で現在の1工程だけ対応します。</p>
      <p><strong>全体進捗：{completed_steps} / 3 工程 完了</strong></p>
      <ol style="padding-left:1.5rem;">
        <li style="margin-bottom:8px;"><strong>1. 初回評価</strong> — {initial_count} / {total}社 適格確認済み　<strong>{_step_label(result, 1)}</strong></li>
        <li style="margin-bottom:8px;"><strong>2. 契約確認</strong> — {contract_count} / {total}社 確認済み　<strong>{_step_label(result, 2)}</strong></li>
        <li><strong>3. 定期評価</strong> — {periodic_count} / {total}社 有効　<strong>{_step_label(result, 3)}</strong></li>
      </ol>
      <p><strong>現在地：{current_label}</strong></p>
    </section>
    """


def _render_focused_todo(state: VendorDemoState, result: VendorEvaluationResult) -> str:
    current = _current_step(result)
    if current is None:
        return """
        <section class="focused-todo" style="margin:18px 0;">
          <h2>今やること</h2>
          <p style="color:#167c3a;"><strong>対応が必要な項目はありません。委託先管理は完了しています。</strong></p>
        </section>
        """

    if current == 1:
        if _has_issue(result, "VEN-001"):
            vendor_ids = _issue_vendor_ids(result, "VEN-001")
            message = f"初回評価が必要な{len(vendor_ids)}社について評価記録を登録してください。"
        else:
            vendor_ids = _issue_vendor_ids(result, "VEN-003")
            message = f"初回評価で不適格となった{len(vendor_ids)}社について再評価記録を登録してください。"
    elif current == 2:
        vendor_ids = _issue_vendor_ids(result, "VEN-002")
        message = f"契約確認が未完了の{len(vendor_ids)}社について確認記録を登録してください。"
    else:
        vendor_ids = _issue_vendor_ids(result, "VEN-004", "VEN-006")
        message = f"定期評価が必要な{len(vendor_ids)}社について評価記録を登録してください。"

    names = _vendor_names(state, vendor_ids)
    names_html = f"<p>対象：{names}</p>" if names else ""
    return f"""
    <section class="focused-todo" style="margin:18px 0; padding:12px 16px; background:#fff8ef; border-left:4px solid #d9822b;">
      <h2 style="margin-top:0;">今やること <span style="font-size:0.8em; font-weight:normal;">1件</span></h2>
      <p><strong>{escape(message)}</strong></p>
      {names_html}
    </section>
    """


def _method_options() -> str:
    return """
      <option value="チェックリスト" selected>チェックリスト</option>
      <option value="ヒアリング">ヒアリング</option>
      <option value="資料確認">資料確認</option>
      <option value="現地確認">現地確認</option>
    """


def _result_options() -> str:
    return """
      <option value="passed" selected>適格・合格</option>
      <option value="failed">不適格・要対応</option>
    """


def _render_initial_form(state: VendorDemoState, result: VendorEvaluationResult) -> str:
    vendor_ids = _issue_vendor_ids(result, "VEN-001", "VEN-003")
    names = _vendor_names(state, vendor_ids)
    assessor = escape(_assessor_default())
    return f"""
    <section id="vendor-record" style="border:1px solid #ddd; padding:14px; margin:18px 0;">
      <h2 style="margin-top:0;">1. 初回評価記録</h2>
      <p>対象：{names}</p>
      <p>委託開始前の適格性確認について、後から説明できる最低限の記録を残します。</p>
      <form method="post" action="/vendors/actions/complete-initial-assessments" style="display:block;">
        <label>評価日 <input type="date" name="assessment_date" required></label><br><br>
        <label>評価者 <input type="text" name="assessor_name" value="{assessor}" required></label><br><br>
        <label>評価方法 <select name="assessment_method" required>{_method_options()}</select></label><br><br>
        <label>評価結果 <select name="assessment_result" required>{_result_options()}</select></label><br><br>
        <label>評価票・証跡名 <input type="text" name="evidence_name" value="委託先初回評価票" required></label><br><br>
        <button type="submit">初回評価記録を保存して次へ</button>
      </form>
    </section>
    """


def _render_contract_form(state: VendorDemoState, result: VendorEvaluationResult) -> str:
    vendor_ids = _issue_vendor_ids(result, "VEN-002")
    names = _vendor_names(state, vendor_ids)
    confirmer = escape(_assessor_default())
    return f"""
    <section id="vendor-record" style="border:1px solid #ddd; padding:14px; margin:18px 0;">
      <h2 style="margin-top:0;">2. 契約確認記録</h2>
      <p>対象：{names}</p>
      <p>個人情報保護に関する必要事項を契約等で確認した事実を記録します。</p>
      <form method="post" action="/vendors/actions/confirm-contracts" style="display:block;">
        <label>確認日 <input type="date" name="confirmed_on" required></label><br><br>
        <label>確認者 <input type="text" name="confirmed_by" value="{confirmer}" required></label><br><br>
        <label>契約・確認資料 <input type="text" name="contract_reference" value="業務委託契約書" required></label><br><br>
        <button type="submit">契約確認記録を保存して次へ</button>
      </form>
    </section>
    """


def _render_periodic_form(state: VendorDemoState, result: VendorEvaluationResult) -> str:
    vendor_ids = _issue_vendor_ids(result, "VEN-004", "VEN-006")
    names = _vendor_names(state, vendor_ids)
    assessor = escape(_assessor_default())
    return f"""
    <section id="vendor-record" style="border:1px solid #ddd; padding:14px; margin:18px 0;">
      <h2 style="margin-top:0;">3. 定期評価記録</h2>
      <p>対象：{names}</p>
      <p>委託期間中の取扱状況を確認し、評価日・方法・結果・証跡を記録します。</p>
      <form method="post" action="/vendors/actions/complete-periodic-assessments" style="display:block;">
        <label>評価日 <input type="date" name="assessment_date" required></label><br><br>
        <label>評価者 <input type="text" name="assessor_name" value="{assessor}" required></label><br><br>
        <label>評価方法 <select name="assessment_method" required>{_method_options()}</select></label><br><br>
        <label>評価結果 <select name="assessment_result" required>{_result_options()}</select></label><br><br>
        <label>評価票・証跡名 <input type="text" name="evidence_name" value="委託先定期評価票" required></label><br><br>
        <button type="submit">定期評価記録を保存して完了</button>
      </form>
    </section>
    """


def _render_current_form(state: VendorDemoState, result: VendorEvaluationResult) -> str:
    current = _current_step(result)
    if current == 1:
        return _render_initial_form(state, result)
    if current == 2:
        return _render_contract_form(state, result)
    if current == 3:
        return _render_periodic_form(state, result)
    return """
    <section id="vendor-record" style="margin:18px 0;">
      <h2>委託先管理記録</h2>
      <p>必要な委託先管理記録は登録済みです。</p>
    </section>
    """


def render_vendor_workflow(state: VendorDemoState, result: VendorEvaluationResult) -> str:
    return (
        _render_overview(state, result)
        + _render_focused_todo(state, result)
        + _render_current_form(state, result)
    )


def enhance_vendor_page(
    html: str, state: VendorDemoState, result: VendorEvaluationResult
) -> str:
    """既存の全件ToDoを、全体工程＋現在工程の記録入力へ置き換える。"""

    workflow = render_vendor_workflow(state, result)
    todo_start = html.find('<section class="todo">')
    if todo_start >= 0:
        todo_end = html.find("</section>", todo_start)
        if todo_end >= 0:
            todo_end += len("</section>")
            return html[:todo_start] + workflow + html[todo_end:]

    marker = '<section class="problem-vendors">'
    if marker in html:
        return html.replace(marker, workflow + marker, 1)
    return html.replace("</h1>", "</h1>" + workflow, 1)
