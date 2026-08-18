"""申請準備完了時に表示するプロトタイプ用ゴールサマリー。"""

from __future__ import annotations

from html import escape

from app.application_prep import evaluate_application_prep
from app.application_prep_schemas import ApplicationPreparationState, ApplicationPrerequisites


def _application_method_label(method: str | None) -> str:
    return {
        "online": "オンライン",
        "mail": "郵送・持参",
        "other": "審査機関指定の方法",
    }.get(method, "未設定")


def _form_set_label(state: ApplicationPreparationState) -> str:
    if state.uses_jipdec_forms is True and state.application_method == "online":
        return "JIPDEC 新規申請様式（オンライン）"
    if state.uses_jipdec_forms is True:
        return "JIPDEC 新規申請書類一式"
    if state.uses_jipdec_forms is False:
        return "申請先審査機関の指定様式一式"
    return "未設定"


def _summary_row(label: str, value: str) -> str:
    return f"""
      <div class="goal-summary-row">
        <span class="goal-summary-label">{escape(label)}</span>
        <strong>{escape(value)}</strong>
      </div>
    """


def render_application_prep_goal(
    state: ApplicationPreparationState,
    prerequisites: ApplicationPrerequisites,
) -> str:
    """申請準備がすべて完了した場合だけ、提出前サマリーを返す。"""

    result = evaluate_application_prep(state, prerequisites)
    if not result.complete:
        return ""

    prerequisite_count = sum(
        (
            prerequisites.company_profile_ready,
            prerequisites.pms_documents_ready,
            prerequisites.operations_ready,
            prerequisites.pms_review_ready,
        )
    )
    account_value = "準備済み" if state.application_method == "online" else "対象外"

    summary = "".join(
        (
            _summary_row("申請先", state.examining_body_name or "未設定"),
            _summary_row("申請方法", _application_method_label(state.application_method)),
            _summary_row("申請様式", _form_set_label(state)),
            _summary_row("PMS前提記録", f"{prerequisite_count} / 4 項目 確認済み"),
            _summary_row("提出するPMS文書一式", "準備済み"),
            _summary_row("オンライン申請アカウント", account_value),
            _summary_row("最終確認者", state.final_reviewed_by or "未設定"),
            _summary_row("最終確認日", state.final_reviewed_at or "未設定"),
        )
    )

    return f"""
    <section class="application-goal" aria-labelledby="application-goal-title">
      <p class="application-goal-kicker">申請準備 4 / 4 工程 完了</p>
      <h2 id="application-goal-title">申請提出前の準備が整いました</h2>
      <p>
        このツールで確認する申請準備項目はすべて完了しています。
        これまで入力・記録した内容が、申請準備へつながっています。
      </p>

      <div class="goal-summary">
        <h3>申請準備サマリー</h3>
        {summary}
      </div>

      <div class="external-next-step">
        <h3>次は、審査機関への実際の申請・審査です</h3>
        <ol>
          <li>選択した審査機関の最新の申請案内・提出様式を最終確認する</li>
          <li>審査機関へ申請書類・PMS文書等を提出する</li>
          <li>文書審査・現地審査等、審査機関から案内される外部手続へ進む</li>
        </ol>
      </div>

      <p class="goal-caution">
        ここでの完了は、申請提出前の準備確認が完了したことを示すものであり、
        Pマークの付与適格性・認定・取得を保証するものではありません。
      </p>
    </section>
    """


def enhance_application_prep_page(
    html: str,
    state: ApplicationPreparationState,
    prerequisites: ApplicationPrerequisites,
) -> str:
    """完了時だけ、既存の工程表示より前にゴールサマリーを差し込む。"""

    goal_html = render_application_prep_goal(state, prerequisites)
    if not goal_html:
        return html

    style_marker = "    input, select { padding:.35rem; margin-top:.25rem; }"
    styles = """
    .application-goal { border:2px solid #0a7a0a; border-radius:8px; padding:1.4rem; margin:1.5rem 0; background:#f7fff8; }
    .application-goal h2 { margin:.15rem 0 .6rem; }
    .application-goal-kicker { color:#0a7a0a; font-weight:bold; margin:0; }
    .goal-summary { background:#fff; border:1px solid #c9ddcd; border-radius:6px; padding:1rem; margin:1rem 0; }
    .goal-summary h3 { margin-top:0; }
    .goal-summary-row { display:grid; grid-template-columns:minmax(170px, 1fr) 2fr; gap:1rem; padding:.45rem 0; border-bottom:1px solid #eee; }
    .goal-summary-row:last-child { border-bottom:0; }
    .goal-summary-label { color:#666; }
    .external-next-step { background:#eef5ff; border-left:4px solid #356aa0; padding:1rem; margin-top:1rem; }
    .external-next-step h3 { margin-top:0; }
    .goal-caution { color:#666; font-size:.9em; margin-bottom:0; }
    """
    if style_marker in html:
        html = html.replace(style_marker, style_marker + styles, 1)

    marker = '<section class="workflow">'
    if marker in html:
        return html.replace(marker, goal_html + marker, 1)
    return html
