"""取得計画・年間PMS運用計画の共通HTML描画。

Plan / PlanStep の内容をそのまま表現し、計画種別ごとの業務判定は行わない。
"""

from __future__ import annotations

from html import escape

from app.plan_models import Plan


def _status_style(kind: str) -> str:
    return {
        "complete": "background:#0a7a0a;color:#fff;",
        "current": "background:#b36b00;color:#fff;",
        "pending": "background:#666;color:#fff;",
        "future": "background:#eee;color:#555;border:1px solid #bbb;",
        "not-applicable": "background:#f2f2f2;color:#555;border:1px solid #bbb;",
    }.get(kind, "background:#666;color:#fff;")


def render_plan(
    plan: Plan,
    *,
    css_class: str = "plan-overview",
    current_only_actions: bool = False,
) -> str:
    """計画を表形式で描画する。

    current_only_actions=True の場合は、全体計画を「地図」として使うため、
    現在工程だけに行動リンクを表示する。年間PMS等の既存画面は既定値Falseのまま
    従来どおり各工程のリンクを表示できる。
    """

    rows: list[str] = []
    for step in plan.steps:
        current_marker = " ← 現在" if step.current else ""
        row_style = "background:#fff8ef;" if step.current else ""
        action_visible = bool(step.link) and (not current_only_actions or step.current)
        action = (
            f'<a href="{escape(step.link)}">現在の工程へ</a>'
            if action_visible and current_only_actions
            else f'<a href="{escape(step.link)}">確認する</a>'
            if action_visible
            else "—"
        )
        rows.append(
            f"""
            <tr style="{row_style}">
              <td style="padding:10px;border-bottom:1px solid #ddd;white-space:nowrap;">{step.number}</td>
              <td style="padding:10px;border-bottom:1px solid #ddd;">
                <strong>{escape(step.name)}</strong>{current_marker}<br>
                <span style="color:#666;font-size:0.9em;">{escape(step.description)}</span>
              </td>
              <td style="padding:10px;border-bottom:1px solid #ddd;white-space:nowrap;">
                <span style="display:inline-block;padding:2px 8px;border-radius:4px;{_status_style(step.status_kind)}">{escape(step.status)}</span>
              </td>
              <td style="padding:10px;border-bottom:1px solid #ddd;white-space:nowrap;">{action}</td>
            </tr>
            """
        )

    footer = (
        f'<p style="font-size:0.9em;color:#666;">{escape(plan.footer_note)}</p>'
        if plan.footer_note
        else ""
    )
    return f"""
    <section class="{escape(css_class)}" style="border:1px solid #bbb;border-radius:4px;padding:16px;margin:24px 0;">
      <h2 style="margin-top:0;">{escape(plan.title)}</h2>
      <p>{escape(plan.description)}</p>
      <p><strong>{escape(plan.progress_label)}：{plan.completed_count} / {plan.tracked_total} 工程 完了</strong></p>
      <div style="overflow-x:auto;">
        <table style="width:100%;border-collapse:collapse;min-width:700px;">
          <thead>
            <tr>
              <th style="text-align:left;padding:8px;border-bottom:2px solid #bbb;">順序</th>
              <th style="text-align:left;padding:8px;border-bottom:2px solid #bbb;">工程</th>
              <th style="text-align:left;padding:8px;border-bottom:2px solid #bbb;">状態</th>
              <th style="text-align:left;padding:8px;border-bottom:2px solid #bbb;">詳細</th>
            </tr>
          </thead>
          <tbody>{''.join(rows)}</tbody>
        </table>
      </div>
      <p><strong>現在地：{escape(plan.current_text)}</strong></p>
      {footer}
    </section>
    """
