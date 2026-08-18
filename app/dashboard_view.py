"""管理者ダッシュボード（トップページ）のHTML描画。

ここでは集約・業務判定を一切行わない。app.dashboard.build_dashboard_data()が
組み立てた DashboardData をそのまま表示するだけとする。
"""

from __future__ import annotations

from app.control_status import SETUP_STATUS_CSS_CLASS, SETUP_STATUS_LABELS
from app.dashboard import DashboardData
from app.intake_schemas import SetupStatus

SETUP_LINK_LABELS: dict[SetupStatus, str] = {
    SetupStatus.NOT_STARTED: "初期設定を始める",
    SetupStatus.IN_PROGRESS: "初期設定を続ける",
    SetupStatus.COMPLETE: "初期設定を確認する",
}


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _render_setup_card(data: DashboardData) -> str:
    label = SETUP_STATUS_LABELS[data.setup_status]
    css_class = SETUP_STATUS_CSS_CLASS[data.setup_status]
    link_label = SETUP_LINK_LABELS[data.setup_status]
    return f"""
    <div class="summary-card">
      <h3>初期設定</h3>
      <p>業務ヒアリング・個人情報の確認・リスク確認・管理策の採用判断をまとめて行います。</p>
      <p>状態：<span class="status-badge {css_class}">{label}</span></p>
      <p><a href="/setup">{_escape(link_label)}</a></p>
    </div>
    """


def _render_personal_information_card(data: DashboardData) -> str:
    incomplete_class = "needs-action" if data.personal_information_incomplete_count else "compliant"
    return f"""
    <div class="summary-card">
      <h3>個人情報</h3>
      <ul class="summary-figures">
        <li>確認済み：{data.personal_information_confirmed_count}件</li>
        <li class="{incomplete_class}">入力不足：{data.personal_information_incomplete_count}件</li>
      </ul>
      <p><a href="/setup">個人情報を確認</a></p>
    </div>
    """


def _render_risk_card(data: DashboardData) -> str:
    return f"""
    <div class="summary-card">
      <h3>リスク</h3>
      <ul class="summary-figures">
        <li>確認済み：{data.risk_confirmed_count}件</li>
        <li>高：{data.risk_high_count}件／中：{data.risk_medium_count}件／低：{data.risk_low_count}件</li>
      </ul>
      <p><a href="/setup">リスクを確認</a></p>
    </div>
    """


def _render_controls_card(data: DashboardData) -> str:
    needs_review_class = "needs-action" if data.controls_needs_review_count else "compliant"
    return f"""
    <div class="summary-card">
      <h3>管理策</h3>
      <ul class="summary-figures">
        <li>採用：{data.controls_adopted_count}件</li>
        <li>非適用：{data.controls_not_applicable_count}件</li>
        <li class="{needs_review_class}">要確認：{data.controls_needs_review_count}件</li>
      </ul>
      <p><a href="/setup">管理策を確認</a></p>
    </div>
    """


def _render_documents_card(data: DashboardData) -> str:
    if data.setup_status == SetupStatus.NOT_STARTED:
        figures = '<li>初期設定待ち：文書の生成にはまず初期設定が必要です。</li>'
        link_href = "/setup"
        link_label = "初期設定を始める"
    elif data.personal_information_confirmed_count == 0:
        figures = '<li>個人情報確認待ち：取り扱う個人情報を確認すると、文書の準備状況を判定します。</li>'
        link_href = "/setup"
        link_label = "個人情報を確認"
    else:
        draft_class = "needs-action" if data.documents_draft_count else "compliant"
        figures = f"""
        <li>準備完了：{data.documents_ready_count}件</li>
        <li class="{draft_class}">情報不足：{data.documents_draft_count}件</li>
        <li>未生成：{data.documents_not_applicable_count}件</li>
        """
        link_href = "/documents"
        link_label = "文書を確認"
    return f"""
    <div class="summary-card">
      <h3>文書管理</h3>
      <p>個人情報管理台帳・教育手順・委託先管理手順など、管理策に対応するPMS文書のプレビューです。</p>
      <ul class="summary-figures">{figures}</ul>
      <p><a href="{link_href}">{_escape(link_label)}</a></p>
    </div>
    """


def _render_preparation_section(data: DashboardData) -> str:
    return f"""
    <details class="secondary-section">
      <summary>Pマーク準備状況を詳しく見る</summary>
      <section>
        <h2>Pマーク準備状況</h2>
        <p>初期設定・個人情報・リスク・管理策・文書の現在状態を確認できます。</p>
        <div class="summary-grid">
          {_render_setup_card(data)}
          {_render_personal_information_card(data)}
          {_render_risk_card(data)}
          {_render_controls_card(data)}
          {_render_documents_card(data)}
        </div>
      </section>
    </details>
    """


def _render_operational_card(area) -> str:
    return f"""
    <div class="summary-card">
      <h3>{_escape(area.name)}</h3>
      <p>状態：<span class="status-badge {area.css_class}">{_escape(area.label)}</span></p>
      <p class="operational-note">{_escape(area.note)}</p>
      <p><a href="{area.link}">確認する</a></p>
    </div>
    """


def _render_operational_section(data: DashboardData) -> str:
    cards = "".join(_render_operational_card(area) for area in data.operational_areas)
    return f"""
    <details class="secondary-section">
      <summary>運用状況を詳しく見る</summary>
      <section>
        <h2>運用状況</h2>
        <p>採用済みの管理策についてのみ、運用上の状態（適合しているか、対応が必要か）を表示します。
        未採用の管理策は、運用中であるかのようには表示しません。</p>
        <div class="summary-grid">{cards}</div>
      </section>
    </details>
    """


def _render_remaining_todos(items) -> str:
    if not items:
        return ""

    rows = "".join(
        f"""
        <li>
          <strong>{_escape(item.area)}</strong>：{_escape(item.message)}
          <a href="{item.link}">確認する</a>
        </li>
        """
        for item in items
    )
    return f"""
      <details class="remaining-actions">
        <summary>そのほかの対応予定　{len(items)}件</summary>
        <ul>{rows}</ul>
      </details>
    """


def _render_todo_section(data: DashboardData) -> str:
    if not data.todo_items:
        return """
        <section class="todo-section current-action-section">
          <h2>次にやること</h2>
          <div class="todo-empty complete">
            <strong>現在、対応が必要な項目はありません。</strong>
            <p>全体計画の現在地と各工程の状態を確認してください。</p>
          </div>
        </section>
        """

    primary = data.todo_items[0]
    remaining_html = _render_remaining_todos(data.todo_items[1:])
    return f"""
    <section class="todo-section current-action-section">
      <h2>次にやること</h2>
      <p class="current-action-intro">まずはこの1件を進めてください。完了すると、次に必要な作業が更新されます。</p>
      <div class="current-action-card">
        <p class="current-action-label">現在の作業</p>
        <h3>{_escape(primary.area)}</h3>
        <p class="current-action-message">{_escape(primary.message)}</p>
        <p><a class="primary-action" href="{primary.link}">この作業を進める</a></p>
      </div>
      {remaining_html}
    </section>
    """


def _render_dev_tools() -> str:
    return """
    <section class="dev-tools">
      <h2>開発用ショートカット</h2>
      <p>検証時だけ利用する開発機能です。通常利用者には表示されません。</p>
      <form method="post" action="/dev/preset/operations" style="margin-bottom:0.75rem;">
        <button type="submit">運用検証用プリセットをセット</button>
        <span> — 初期設定完了後、4つの管理策運用を最初から確認</span>
      </form>
      <form method="post" action="/dev/preset/annual-pms" style="margin-bottom:0.75rem;">
        <button type="submit">年間PMS検証用プリセットをセット</button>
        <span> — 初期設定完了後、年度運用計画から9工程の年間サイクルを確認</span>
      </form>
      <form method="post" action="/dev/preset/pms-review" style="margin-bottom:0.75rem;">
        <button type="submit">PMSレビュー検証用プリセットをセット</button>
        <span> — 4つの管理策運用まで完了し、内部監査から確認</span>
      </form>
      <form method="post" action="/dev/preset/application-prep">
        <button type="submit">申請準備検証用プリセットをセット</button>
        <span> — PMSレビューまで完了し、申請先・方法の確認から開始</span>
      </form>
    </section>
    """


def render_dashboard_page(
    app_name: str,
    data: DashboardData,
    *,
    show_dev_tools: bool = False,
) -> str:
    dev_tools_html = _render_dev_tools() if show_dev_tools else ""
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <title>{_escape(app_name)}</title>
  <style>
    body {{ font-family: sans-serif; margin: 2rem; line-height: 1.6; max-width: 1000px; color:#222; }}
    h1 {{ margin-bottom: 0.3rem; }}
    .tagline {{ color: #555; margin-top: 0; max-width:760px; }}
    section {{ margin-bottom: 2rem; }}
    section > p {{ color: #555; }}
    .todo-section {{ margin-top: 1.25rem; }}
    .current-action-section {{ margin-bottom:2rem; }}
    .current-action-intro {{ margin-top:-0.4rem; }}
    .current-action-card {{
      border:2px solid #b36b00; border-radius:8px; padding:1.25rem 1.4rem; background:#fffaf2;
    }}
    .current-action-card h3 {{ margin:0.1rem 0 0.6rem; font-size:1.35rem; }}
    .current-action-label {{ margin:0; color:#8a5200; font-size:0.85rem; font-weight:bold; }}
    .current-action-message {{ font-size:1.05rem; color:#222; }}
    .primary-action {{
      display:inline-block; padding:0.65rem 1rem; border-radius:5px; background:#8a5200; color:#fff;
      text-decoration:none; font-weight:bold;
    }}
    .primary-action:hover {{ text-decoration:underline; }}
    .remaining-actions {{ margin-top:0.9rem; color:#555; }}
    .remaining-actions summary {{ cursor:pointer; font-weight:bold; }}
    .remaining-actions li {{ margin:0.45rem 0; }}
    .remaining-actions a {{ margin-left:0.5rem; }}
    .secondary-section {{ border-top:1px solid #ddd; padding:0.9rem 0; }}
    .secondary-section > summary {{ cursor:pointer; font-weight:bold; font-size:1.05rem; color:#444; }}
    .secondary-section > section {{ margin:1rem 0 0; }}
    .summary-grid {{
      display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1rem;
    }}
    .summary-card {{ border: 1px solid #ccc; border-radius: 4px; padding: 1rem; }}
    .summary-card h3 {{ margin-top: 0; }}
    .summary-figures {{ list-style: none; margin: 0.5rem 0; padding: 0; }}
    .summary-figures li {{ margin-bottom: 0.2rem; }}
    .summary-figures li.needs-action {{ color: #b30000; font-weight: bold; }}
    .summary-figures li.compliant {{ color: #0a7a0a; }}
    .operational-note {{ font-size: 0.85rem; color: #666; }}
    .status-badge {{ display: inline-block; padding: 0.2rem 0.6rem; border-radius: 4px; }}
    .status-badge.needs-action {{ background: #b30000; color: #fff; }}
    .status-badge.compliant {{ background: #0a7a0a; color: #fff; }}
    .status-badge.not-started {{ background: #666; color: #fff; }}
    .todo-empty.complete {{
      padding: 0.9rem 1rem; background: #eefaf0; border-left: 4px solid #0a7a0a;
    }}
    .todo-empty.complete p {{ margin-bottom:0; }}
    .dev-tools {{ border-top: 1px dashed #aaa; padding-top: 1rem; color: #666; }}
    .dev-tools h2 {{ font-size: 1rem; }}
  </style>
</head>
<body>
  <h1>{_escape(app_name)}</h1>
  <p class="tagline">全体の現在地を確認し、画面に表示される「次にやること」を順番に進めることで、Pマーク申請に必要な準備を整えていきます。</p>

  {_render_todo_section(data)}
  {_render_preparation_section(data)}
  {_render_operational_section(data)}
  {dev_tools_html}
</body>
</html>
"""
