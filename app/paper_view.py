"""紙媒体管理デモ画面のHTML描画。

ここでは業務判定を一切行わない。渡された PaperEvaluationResult
（app.paper.evaluate_paper_management の結果）をそのまま表示するだけとする。

委託先管理・アクセス権限管理デモ画面と同じUI思想を踏襲し、「今どういう状態か」
「何が不足しているか」「次に何をすればいいか」を最初に伝える。
"""

from __future__ import annotations

from app.control_status import operational_status
from app.intake import CONTROL_STATUS_LABELS, find_control_suggestion
from app.intake_schemas import ControlDecisionStatus, ControlSuggestion
from app.paper_demo_state import POLICY_CLAUSES, PaperDemoState
from app.paper_schemas import PaperEvaluationResult, PaperEvaluationStatus, PaperIssue

# 不足事項（rule_id）を、利用者向けの見出し・対応ボタン・短い説明へ変換するための表示定義。
ISSUE_DISPLAY = {
    "PAP-001": {
        "headline": "保管場所の施錠管理が未確認です",
        "explain": "紙媒体の保管場所が施錠されているかを確認してください。",
        "action_label": "施錠管理を確認する",
        "action_url": "/paper/actions/confirm-storage-lock",
    },
    "PAP-002": {
        "headline": "持出しルールが未設定です",
        "explain": "紙媒体を持ち出す際のルール（許可の得方・記録方法等）を定めてください。",
        "action_label": "持出しルールを設定する",
        "action_url": "/paper/actions/define-take-out-rule",
    },
    "PAP-003": {
        "headline": "廃棄確認が未実施です",
        "explain": "不要になった紙媒体が、定めた方法で確実に廃棄されたことを確認してください。",
        "action_label": "廃棄確認を実施する",
        "action_url": "/paper/actions/confirm-disposal",
    },
    "PAP-004": {
        "headline": "実施結果が未承認です",
        "explain": "紙媒体管理の実施結果を、責任者が確認し承認してください。",
        "action_label": "実施結果を承認する",
        "action_url": "/paper/actions/approve",
    },
}


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _issue_by_rule(result: PaperEvaluationResult, rule_id: str) -> PaperIssue | None:
    return next((issue for issue in result.issues if issue.rule_id == rule_id), None)


def _setup_adoption_label(suggestion: ControlSuggestion | None) -> str:
    """初期設定での採用判断（正本）を表示用ラベルへ変換する。

    この管理策自体（PaperControl）は採用可否の判断を持たないため、
    ここでは必ず初期設定側のControlSuggestionを参照する。
    """

    if suggestion is None:
        return "未確認（初期設定で未回答、またはリスク未確認）"
    return CONTROL_STATUS_LABELS[suggestion.status]


def _render_adoption_notice(control_suggestions: list[ControlSuggestion]) -> str:
    """この管理策が初期設定で採用済みかどうかを、画面冒頭で明示する。"""

    suggestion = find_control_suggestion(control_suggestions, "paper_management")
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


# ---------------------------------------------------------------------------
# 1. 現在の状態サマリー
# ---------------------------------------------------------------------------


def _render_status_summary(state: PaperDemoState, result: PaperEvaluationResult) -> str:
    status_class = (
        "compliant" if result.status == PaperEvaluationStatus.COMPLIANT else "needs-action"
    )
    handled_items = "、".join(_escape(name) for name in state.status.handled_personal_information)

    return f"""
    <section class="status-summary">
      <p class="control-title">{_escape(state.control.name)}</p>
      <p class="status-badge {status_class}">現在の状態：<strong>{result.status.value}</strong></p>
      <p class="issue-count">対応が必要な項目：{len(result.issues)}件</p>
      <ul class="status-figures">
        <li>紙媒体で取り扱う個人情報：{handled_items or "（登録なし）"}</li>
        <li>保管場所：{_escape(state.status.storage_location) if state.status.storage_location else "未登録"}</li>
        <li>施錠管理：{"確認済み" if state.status.storage_locked else "未確認"}</li>
        <li>持出しルール：{"設定済み" if (state.status.take_out_rule or "").strip() else "未設定"}</li>
        <li>廃棄方法：{_escape(state.status.disposal_method) if state.status.disposal_method else "未登録"}</li>
        <li>廃棄確認：{"実施済み" if state.status.disposal_confirmed else "未実施"}</li>
        <li>実施結果承認：{"承認済み" if state.status.approved else "未承認"}</li>
      </ul>
    </section>
    """


# ---------------------------------------------------------------------------
# 2. 今やること（不足事項＋対応操作）
# ---------------------------------------------------------------------------


def _render_todo_section(result: PaperEvaluationResult) -> str:
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
# 3. 詳細情報（管理策・規程・判定詳細）
# ---------------------------------------------------------------------------


def _render_control_detail(
    state: PaperDemoState, control_suggestions: list[ControlSuggestion]
) -> str:
    control = state.control
    suggestion = find_control_suggestion(control_suggestions, "paper_management")
    return f"""
    <div class="detail-block">
      <h3>紙媒体管理策</h3>
      <ul>
        <li>管理策名：{_escape(control.name)}</li>
        <li>採用状態（初期設定での判断）：{_setup_adoption_label(suggestion)}</li>
        <li>施錠管理の確認：{"必須" if control.lock_check_required else "任意"}</li>
        <li>持出しルールの設定：{"必須" if control.take_out_rule_required else "任意"}</li>
        <li>廃棄確認：{"必須" if control.disposal_check_required else "任意"}</li>
        <li>実施結果承認：{"必須" if control.approval_required else "任意"}</li>
      </ul>
    </div>
    """


def _render_policy_detail() -> str:
    items = "".join(f"<li>{_escape(clause)}</li>" for clause in POLICY_CLAUSES)
    return f"""
    <div class="detail-block">
      <h3>規程内容（プレビュー）</h3>
      <p>紙媒体管理に関する標準規程条項の抜粋です。今回のMVPでは文書としての生成は行いません。</p>
      <ol>{items}</ol>
    </div>
    """


def _render_status_detail(state: PaperDemoState) -> str:
    status = state.status
    return f"""
    <div class="detail-block">
      <h3>実施状況</h3>
      <table class="records-table">
        <tbody>
          <tr><th>保管場所</th><td>{_escape(status.storage_location) if status.storage_location else "未登録"}</td></tr>
          <tr><th>施錠管理</th><td>{"確認済み" if status.storage_locked else "未確認"}</td></tr>
          <tr><th>持出しルール</th><td>{_escape(status.take_out_rule) if status.take_out_rule else "未設定"}</td></tr>
          <tr><th>廃棄方法</th><td>{_escape(status.disposal_method) if status.disposal_method else "未登録"}</td></tr>
          <tr><th>廃棄確認</th><td>{"実施済み" if status.disposal_confirmed else "未実施"}</td></tr>
          <tr><th>実施結果承認</th><td>{"承認済み" if status.approved else "未承認"}</td></tr>
        </tbody>
      </table>
    </div>
    """


def _render_judgement_detail(result: PaperEvaluationResult) -> str:
    if not result.issues:
        return """
        <div class="detail-block">
          <h3>判定詳細</h3>
          <p>不足はありません。</p>
        </div>
        """

    items = "".join(
        f"<li><strong>{issue.rule_id}</strong>：{_escape(issue.message)}</li>"
        for issue in result.issues
    )

    return f"""
    <div class="detail-block">
      <h3>判定詳細</h3>
      <ul>{items}</ul>
    </div>
    """


def _render_details_section(
    state: PaperDemoState,
    result: PaperEvaluationResult,
    control_suggestions: list[ControlSuggestion],
) -> str:
    return f"""
    <details class="detail">
      <summary>詳細を見る</summary>
      {_render_control_detail(state, control_suggestions)}
      {_render_policy_detail()}
      {_render_status_detail(state)}
      {_render_judgement_detail(result)}
    </details>
    """


def _render_reset_section() -> str:
    return """
    <section class="reset">
      <form method="post" action="/paper/reset">
        <button type="submit">デモを初期状態に戻す</button>
      </form>
    </section>
    """


# ---------------------------------------------------------------------------
# ページ全体
# ---------------------------------------------------------------------------


def render_paper_page(
    state: PaperDemoState,
    result: PaperEvaluationResult,
    control_suggestions: list[ControlSuggestion],
    flash: str | None = None,
) -> str:
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <title>紙媒体管理 - Pマーク取得・運用支援ツール MVP</title>
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
  <h1>紙媒体管理</h1>
  {_render_flash(flash)}
  {_render_adoption_notice(control_suggestions)}

  {_render_status_summary(state, result)}
  {_render_todo_section(result)}
  {_render_details_section(state, result, control_suggestions)}
  {_render_reset_section()}
</body>
</html>
"""
