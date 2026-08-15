"""アクセス権限管理デモ画面のHTML描画。

ここでは業務判定を一切行わない。渡された AccessEvaluationResult
（app.access_control.evaluate_access_control の結果）をそのまま表示するだけとする。

委託先管理デモ画面（app.vendor_view）と同じUI思想を踏襲し、「今どういう状態か」
「何が不足しているか」「次に何をすればいいか」を最初に伝える。
"""

from __future__ import annotations

from app.access_control_demo_state import POLICY_CLAUSES, AccessControlDemoState
from app.access_control_schemas import (
    Account,
    AccessEvaluationResult,
    AccessEvaluationStatus,
    AccessIssue,
    AccountReviewStatus,
)
from app.intake import CONTROL_STATUS_LABELS, find_control_suggestion
from app.intake_schemas import ControlSuggestion

# 不足事項（rule_id）を、利用者向けの見出し・対応ボタンへ変換するための表示定義。
ISSUE_DISPLAY = {
    "ACC-001": {
        "headline": "アカウント確認が未実施の対象者がいます",
        "action_label": "アカウント確認を完了する",
        "action_url": "/access-control/actions/complete-account-reviews",
    },
    "ACC-002": {
        "headline": "削除されていない不要アカウントがあります",
        "action_label": "不要アカウントを削除する",
        "action_url": "/access-control/actions/remove-unnecessary-accounts",
    },
    "ACC-003": {
        "headline": "権限レビューが未実施です",
        "action_label": "権限レビューを完了する",
        "action_url": "/access-control/actions/complete-review-cycle",
    },
    "ACC-004": {
        "headline": "実施結果が未承認です",
        "action_label": "実施結果を承認する",
        "action_url": "/access-control/actions/approve-review-cycle",
    },
}

REVIEW_STATUS_LABELS = {
    AccountReviewStatus.PENDING: "未確認",
    AccountReviewStatus.CONFIRMED: "確認済み",
}


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _necessary_label(account: Account) -> str:
    if account.necessary is None:
        return "未確認"
    if account.necessary:
        return "必要"
    return "不要（削除済み）" if account.removed else "不要（未削除）"


def _issue_by_rule(result: AccessEvaluationResult, rule_id: str) -> AccessIssue | None:
    return next((issue for issue in result.issues if issue.rule_id == rule_id), None)


def _setup_adoption_label(suggestion: ControlSuggestion | None) -> str:
    """setupでの採用判断（正本）を表示用ラベルへ変換する。

    この管理策自体（AccessControl）は採用可否の判断を持たないため、
    ここでは必ずsetupのControlSuggestionを参照する。
    """

    if suggestion is None:
        return "未確認（setupで未回答、またはリスク未確認）"
    return CONTROL_STATUS_LABELS[suggestion.status]


def _account_names(state: AccessControlDemoState, account_ids: list[int]) -> str:
    accounts_by_id = {account.id: account for account in state.accounts}
    return "、".join(
        _escape(accounts_by_id[account_id].user_name)
        for account_id in account_ids
        if account_id in accounts_by_id
    )


# ---------------------------------------------------------------------------
# 1. 現在の状態サマリー
# ---------------------------------------------------------------------------


def _render_status_summary(state: AccessControlDemoState, result: AccessEvaluationResult) -> str:
    status_class = (
        "compliant" if result.status == AccessEvaluationStatus.COMPLIANT else "needs-action"
    )

    unconfirmed_issue = _issue_by_rule(result, "ACC-001")
    unconfirmed_count = len(unconfirmed_issue.account_ids) if unconfirmed_issue else 0
    target_count = len(result.target_account_ids)
    confirmed_count = target_count - unconfirmed_count

    unnecessary_issue = _issue_by_rule(result, "ACC-002")
    unnecessary_count = len(unnecessary_issue.account_ids) if unnecessary_issue else 0

    return f"""
    <section class="status-summary">
      <p class="control-title">{_escape(state.control.name)}</p>
      <p class="status-badge {status_class}">現在の状態：<strong>{result.status.value}</strong></p>
      <p class="issue-count">対応が必要な項目：{len(result.issues)}件</p>
      <ul class="status-figures">
        <li>管理対象アカウント：{target_count}名</li>
        <li>確認済み：{confirmed_count}名</li>
        <li>未確認：{unconfirmed_count}名</li>
        <li>削除されていない不要アカウント：{unnecessary_count}件</li>
      </ul>
    </section>
    """


# ---------------------------------------------------------------------------
# 2. 今やること（不足事項＋対応操作）
# ---------------------------------------------------------------------------


def _render_todo_section(state: AccessControlDemoState, result: AccessEvaluationResult) -> str:
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
        names = _account_names(state, issue.account_ids)
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
# 3. 問題のあるアカウント
# ---------------------------------------------------------------------------


def _render_problem_accounts_section(
    state: AccessControlDemoState, result: AccessEvaluationResult
) -> str:
    accounts_by_id = {account.id: account for account in state.accounts}

    problem_ids: list[int] = []
    seen: set[int] = set()
    for issue in result.issues:
        for account_id in issue.account_ids:
            if account_id not in seen:
                seen.add(account_id)
                problem_ids.append(account_id)

    if not problem_ids:
        return """
        <section class="problem-accounts">
          <h2>問題のあるアカウント</h2>
          <p>問題のあるアカウントはいません。</p>
        </section>
        """

    rows = []
    for account_id in problem_ids:
        account = accounts_by_id.get(account_id)
        if account is None:
            continue
        rows.append(
            "<tr>"
            f"<td>{account.id}</td>"
            f"<td>{_escape(account.user_name)}</td>"
            f"<td>{_escape(account.department)}</td>"
            f"<td>{REVIEW_STATUS_LABELS[account.review_status]}</td>"
            f"<td>{_necessary_label(account)}</td>"
            "</tr>"
        )

    return f"""
    <section class="problem-accounts">
      <h2>問題のあるアカウント</h2>
      <table class="records-table">
        <thead>
          <tr><th>ID</th><th>利用者</th><th>所属</th><th>確認状況</th><th>要否</th></tr>
        </thead>
        <tbody>{"".join(rows)}</tbody>
      </table>
    </section>
    """


# ---------------------------------------------------------------------------
# 4. 詳細情報（アカウント一覧・管理策・規程・判定詳細）
# ---------------------------------------------------------------------------


def _render_account_list_detail(state: AccessControlDemoState) -> str:
    rows = "".join(
        "<tr>"
        f"<td>{account.id}</td>"
        f"<td>{_escape(account.user_name)}</td>"
        f"<td>{_escape(account.department)}</td>"
        f"<td>{REVIEW_STATUS_LABELS[account.review_status]}</td>"
        f"<td>{_necessary_label(account)}</td>"
        "</tr>"
        for account in state.accounts
    )
    return f"""
    <div class="detail-block">
      <h3>アカウント一覧</h3>
      <table class="records-table">
        <thead>
          <tr><th>ID</th><th>利用者</th><th>所属</th><th>確認状況</th><th>要否</th></tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
    """


def _render_control_detail(
    state: AccessControlDemoState, control_suggestions: list[ControlSuggestion]
) -> str:
    control = state.control
    cycle = state.cycle
    suggestion = find_control_suggestion(control_suggestions, "access_control")
    return f"""
    <div class="detail-block">
      <h3>アクセス権限管理策</h3>
      <ul>
        <li>管理策名：{_escape(control.name)}</li>
        <li>採用状態（setupでの判断）：{_setup_adoption_label(suggestion)}</li>
        <li>権限レビュー：{"必須" if control.review_required else "任意"}
          （実施状況：{"実施済み" if cycle.review_completed else "未実施"}）</li>
        <li>実施結果承認：{"必須" if control.approval_required else "任意"}
          （承認状況：{"承認済み" if cycle.approved else "未承認"}）</li>
      </ul>
    </div>
    """


def _render_policy_detail() -> str:
    items = "".join(f"<li>{_escape(clause)}</li>" for clause in POLICY_CLAUSES)
    return f"""
    <div class="detail-block">
      <h3>規程内容（プレビュー）</h3>
      <p>アクセス権限管理に関する標準規程条項の抜粋です。今回のMVPでは文書としての生成は行いません。</p>
      <ol>{items}</ol>
    </div>
    """


def _render_judgement_detail(state: AccessControlDemoState, result: AccessEvaluationResult) -> str:
    if not result.issues:
        return """
        <div class="detail-block">
          <h3>判定詳細</h3>
          <p>不足はありません。</p>
        </div>
        """

    items = []
    for issue in result.issues:
        names = _account_names(state, issue.account_ids)
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
    state: AccessControlDemoState,
    result: AccessEvaluationResult,
    control_suggestions: list[ControlSuggestion],
) -> str:
    return f"""
    <details class="detail">
      <summary>詳細を見る</summary>
      {_render_account_list_detail(state)}
      {_render_control_detail(state, control_suggestions)}
      {_render_policy_detail()}
      {_render_judgement_detail(state, result)}
    </details>
    """


def _render_reset_section() -> str:
    return """
    <section class="reset">
      <form method="post" action="/access-control/reset">
        <button type="submit">デモを初期状態に戻す</button>
      </form>
    </section>
    """


# ---------------------------------------------------------------------------
# ページ全体
# ---------------------------------------------------------------------------


def render_access_control_page(
    state: AccessControlDemoState,
    result: AccessEvaluationResult,
    control_suggestions: list[ControlSuggestion],
) -> str:
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <title>アクセス権限管理デモ - Pマーク取得・運用支援ツール MVP</title>
  <style>
    body {{ font-family: sans-serif; margin: 2rem; line-height: 1.6; max-width: 900px; }}
    h1 {{ margin-bottom: 0.5rem; }}
    section, details {{ margin-bottom: 1.5rem; }}
    .status-summary {{ padding: 1rem; border: 1px solid #ccc; border-radius: 4px; }}
    .control-title {{ font-size: 1.1rem; font-weight: bold; margin: 0 0 0.5rem; }}
    .status-badge {{
      display: inline-block; padding: 0.3rem 0.8rem; border-radius: 4px; font-size: 1.1rem;
    }}
    .status-badge.needs-action {{ background: #b30000; color: #fff; }}
    .status-badge.compliant {{ background: #0a7a0a; color: #fff; }}
    .issue-count {{ font-weight: bold; }}
    .status-figures {{ margin: 0.5rem 0 0; padding-left: 1.2rem; }}
    .todo-list {{ list-style: none; margin: 0; padding: 0; }}
    .todo-item {{
      padding: 0.75rem 1rem; margin-bottom: 0.75rem; border-radius: 4px;
    }}
    .todo-item.warning {{ background: #fff8ef; border-left: 4px solid #d9822b; }}
    .todo-headline {{ font-weight: bold; margin: 0 0 0.3rem; }}
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
  <h1>アクセス権限管理</h1>

  {_render_status_summary(state, result)}
  {_render_todo_section(state, result)}
  {_render_problem_accounts_section(state, result)}
  {_render_details_section(state, result, control_suggestions)}
  {_render_reset_section()}
</body>
</html>
"""
