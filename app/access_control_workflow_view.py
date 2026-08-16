"""アクセス権限管理画面を「全体工程 → 現在地 → 今やる1件 → 記録入力」に整える。"""

from __future__ import annotations

from html import escape

from app import company_profile
from app.access_control_demo_state import AccessControlDemoState
from app.access_control_schemas import AccessEvaluationResult, AccountReviewStatus


def _has_issue(result: AccessEvaluationResult, rule_id: str) -> bool:
    return any(issue.rule_id == rule_id for issue in result.issues)


def _issue_account_ids(result: AccessEvaluationResult, rule_id: str) -> list[int]:
    issue = next((item for item in result.issues if item.rule_id == rule_id), None)
    return list(issue.account_ids) if issue else []


def _account_names(state: AccessControlDemoState, account_ids: list[int]) -> str:
    by_id = {account.id: account.user_name for account in state.accounts}
    return "、".join(escape(by_id[item]) for item in account_ids if item in by_id)


def _step_complete(result: AccessEvaluationResult, step: int) -> bool:
    # 順序依存にする。先行工程が未完了なら、後工程に個別不足が無くても「完了」扱いしない。
    step1 = not _has_issue(result, "ACC-001")
    step2 = step1 and not _has_issue(result, "ACC-002")
    step3 = step2 and not _has_issue(result, "ACC-003")
    step4 = step3 and not _has_issue(result, "ACC-004")
    return {1: step1, 2: step2, 3: step3, 4: step4}[step]


def _current_step(result: AccessEvaluationResult) -> int | None:
    for step in (1, 2, 3, 4):
        if not _step_complete(result, step):
            return step
    return None


def _step_label(result: AccessEvaluationResult, step: int) -> str:
    if _step_complete(result, step):
        return "完了"
    if _current_step(result) == step:
        return "対応中 ← 現在"
    return "未完了"


def _manager_default() -> str:
    profile = company_profile.get_state()
    return (
        profile.application_contact_name
        or profile.privacy_manager_name
        or profile.application_contact_department_role
        or "Pマーク担当者"
    )


def _approver_default() -> str:
    profile = company_profile.get_state()
    return profile.privacy_manager_name or "個人情報保護管理者"


def _progress_counts(state: AccessControlDemoState) -> tuple[int, int, int, int]:
    total = len(state.accounts)
    confirmed = sum(
        1 for account in state.accounts if account.review_status == AccountReviewStatus.CONFIRMED
    )
    unnecessary = [account for account in state.accounts if account.necessary is False]
    removed = sum(1 for account in unnecessary if account.removed)
    return total, confirmed, len(unnecessary), removed


def _render_overview(state: AccessControlDemoState, result: AccessEvaluationResult) -> str:
    total, confirmed, unnecessary_count, removed_count = _progress_counts(state)
    completed_steps = sum(1 for step in (1, 2, 3, 4) if _step_complete(result, step))
    current = _current_step(result)
    current_label = {
        1: "1. アカウント棚卸し",
        2: "2. 不要アカウント削除",
        3: "3. 権限レビュー",
        4: "4. 実施結果の承認",
        None: "全工程完了",
    }[current]
    review_status = "実施済み" if state.cycle.review_completed else "未実施"
    approval_status = "承認済み" if state.cycle.approved else "未承認"

    return f"""
    <section class="access-workflow-overview" style="border:1px solid #ccc; padding:16px; border-radius:4px; margin:24px 0;">
      <h2 style="margin-top:0;">アクセス権限管理の全体工程</h2>
      <p>まず全体像と現在地を確認し、下で現在の1工程だけ対応します。</p>
      <p><strong>全体進捗：{completed_steps} / 4 工程 完了</strong></p>
      <ol style="padding-left:1.5rem;">
        <li style="margin-bottom:8px;"><strong>アカウント棚卸し</strong> — {confirmed} / {total}名 確認済み　<strong>{_step_label(result, 1)}</strong></li>
        <li style="margin-bottom:8px;"><strong>不要アカウント削除</strong> — {removed_count} / {unnecessary_count}件 削除済み　<strong>{_step_label(result, 2)}</strong></li>
        <li style="margin-bottom:8px;"><strong>権限レビュー</strong> — {review_status}　<strong>{_step_label(result, 3)}</strong></li>
        <li><strong>実施結果の承認</strong> — {approval_status}　<strong>{_step_label(result, 4)}</strong></li>
      </ol>
      <p><strong>現在地：{current_label}</strong></p>
    </section>
    """


def _render_focused_todo(state: AccessControlDemoState, result: AccessEvaluationResult) -> str:
    current = _current_step(result)
    if current is None:
        return """
        <section class="focused-todo" style="margin:18px 0;">
          <h2>今やること</h2>
          <p style="color:#167c3a;"><strong>対応が必要な項目はありません。アクセス権限管理は完了しています。</strong></p>
        </section>
        """

    if current == 1:
        ids = _issue_account_ids(result, "ACC-001")
        message = f"未確認の{len(ids)}名について、アカウントが現在も必要か確認してください。"
        names = _account_names(state, ids)
    elif current == 2:
        ids = _issue_account_ids(result, "ACC-002")
        message = f"不要と確認された{len(ids)}件のアカウントを削除し、記録を残してください。"
        names = _account_names(state, ids)
    elif current == 3:
        message = "付与されているアクセス権限が業務上適切かレビューし、実施記録を登録してください。"
        names = ""
    else:
        message = "個人情報保護管理者が権限レビュー結果を確認し、承認記録を登録してください。"
        names = ""

    names_html = f"<p>対象：{names}</p>" if names else ""
    return f"""
    <section class="focused-todo" style="margin:18px 0; padding:12px 16px; background:#fff8ef; border-left:4px solid #d9822b;">
      <h2 style="margin-top:0;">今やること <span style="font-size:0.8em; font-weight:normal;">1件</span></h2>
      <p><strong>{escape(message)}</strong></p>
      {names_html}
    </section>
    """


def _render_account_review_form(state: AccessControlDemoState, result: AccessEvaluationResult) -> str:
    ids = _issue_account_ids(result, "ACC-001")
    accounts = {account.id: account for account in state.accounts}
    rows = []
    for account_id in ids:
        account = accounts.get(account_id)
        if account is None:
            continue
        rows.append(
            "<tr>"
            f"<td>{escape(account.user_name)}</td>"
            f"<td>{escape(account.department)}</td>"
            f'<td><select name="decision_{account.id}" required>'
            '<option value="necessary" selected>必要</option>'
            '<option value="unnecessary">不要</option>'
            "</select></td>"
            "</tr>"
        )
    reviewer = escape(_manager_default())
    return f"""
    <section id="access-record" style="border:1px solid #ddd; padding:14px; margin:18px 0;">
      <h2 style="margin-top:0;">1. アカウント棚卸し記録</h2>
      <p>未確認の対象者だけを表示しています。各アカウントの要否を確認してください。</p>
      <form method="post" action="/access-control/actions/complete-account-reviews" style="display:block;">
        <table class="records-table">
          <thead><tr><th>利用者</th><th>所属</th><th>要否</th></tr></thead>
          <tbody>{''.join(rows)}</tbody>
        </table><br>
        <label>確認日 <input type="date" name="reviewed_on" required></label><br><br>
        <label>確認者 <input type="text" name="reviewed_by" value="{reviewer}" required></label><br><br>
        <label>確認方法
          <select name="review_method" required>
            <option value="所属・在籍情報との照合" selected>所属・在籍情報との照合</option>
            <option value="システム利用責任者への確認">システム利用責任者への確認</option>
            <option value="アカウント一覧と人事情報の照合">アカウント一覧と人事情報の照合</option>
          </select>
        </label><br><br>
        <button type="submit">棚卸し記録を保存して次へ</button>
      </form>
    </section>
    """


def _render_removal_form(state: AccessControlDemoState, result: AccessEvaluationResult) -> str:
    ids = _issue_account_ids(result, "ACC-002")
    names = _account_names(state, ids)
    operator = escape(_manager_default())
    return f"""
    <section id="access-record" style="border:1px solid #ddd; padding:14px; margin:18px 0;">
      <h2 style="margin-top:0;">2. 不要アカウント削除記録</h2>
      <p>対象：{names}</p>
      <p>実際に削除した事実を、後から確認できる形で記録します。</p>
      <form method="post" action="/access-control/actions/remove-unnecessary-accounts" style="display:block;">
        <label>削除日 <input type="date" name="removal_date" required></label><br><br>
        <label>実施者 <input type="text" name="removed_by" value="{operator}" required></label><br><br>
        <label>証跡名 <input type="text" name="removal_evidence" value="アカウント削除記録" required></label><br><br>
        <button type="submit">削除記録を保存して次へ</button>
      </form>
    </section>
    """


def _render_review_cycle_form() -> str:
    reviewer = escape(_manager_default())
    return f"""
    <section id="access-record" style="border:1px solid #ddd; padding:14px; margin:18px 0;">
      <h2 style="margin-top:0;">3. 権限レビュー記録</h2>
      <p>アカウントの有無だけでなく、付与されている権限が業務上必要な範囲か確認します。</p>
      <form method="post" action="/access-control/actions/complete-review-cycle" style="display:block;">
        <label>実施日 <input type="date" name="review_date" required></label><br><br>
        <label>実施者 <input type="text" name="reviewer_name" value="{reviewer}" required></label><br><br>
        <label>確認方法
          <select name="review_method" required>
            <option value="権限一覧との照合" selected>権限一覧との照合</option>
            <option value="所属・職務との照合">所属・職務との照合</option>
            <option value="システム管理者とのレビュー">システム管理者とのレビュー</option>
          </select>
        </label><br><br>
        <label>証跡名 <input type="text" name="review_evidence" value="アクセス権限レビュー記録" required></label><br><br>
        <button type="submit">権限レビュー記録を保存して次へ</button>
      </form>
    </section>
    """


def _render_approval_form() -> str:
    approver = escape(_approver_default())
    return f"""
    <section id="access-record" style="border:1px solid #ddd; padding:14px; margin:18px 0;">
      <h2 style="margin-top:0;">4. 実施結果の承認</h2>
      <p>個人情報保護管理者が棚卸し・削除・権限レビューの結果を確認して承認します。</p>
      <form method="post" action="/access-control/actions/approve-review-cycle" style="display:block;">
        <label>承認者 <input type="text" name="approved_by" value="{approver}" required></label><br><br>
        <label>承認日 <input type="date" name="approved_at" required></label><br><br>
        <button type="submit">承認記録を保存して完了</button>
      </form>
    </section>
    """


def _render_current_form(state: AccessControlDemoState, result: AccessEvaluationResult) -> str:
    current = _current_step(result)
    if current == 1:
        return _render_account_review_form(state, result)
    if current == 2:
        return _render_removal_form(state, result)
    if current == 3:
        return _render_review_cycle_form()
    if current == 4:
        return _render_approval_form()
    return """
    <section id="access-record" style="margin:18px 0;">
      <h2>アクセス権限管理記録</h2>
      <p>必要なアクセス権限管理記録は登録済みです。</p>
    </section>
    """


def render_access_workflow(state: AccessControlDemoState, result: AccessEvaluationResult) -> str:
    return _render_overview(state, result) + _render_focused_todo(state, result) + _render_current_form(state, result)


def enhance_access_control_page(
    html: str, state: AccessControlDemoState, result: AccessEvaluationResult
) -> str:
    """既存の全件ToDoを、全体工程＋現在工程の記録入力へ置き換える。"""

    workflow = render_access_workflow(state, result)
    todo_start = html.find('<section class="todo">')
    if todo_start >= 0:
        todo_end = html.find("</section>", todo_start)
        if todo_end >= 0:
            todo_end += len("</section>")
            return html[:todo_start] + workflow + html[todo_end:]

    marker = '<section class="problem-accounts">'
    if marker in html:
        return html.replace(marker, workflow + marker, 1)
    return html.replace("</h1>", "</h1>" + workflow, 1)
