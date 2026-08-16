"""トップダッシュボードに表示するPマーク取得ロードマップ。

既存のDashboardDataに集約済みの状態だけを使い、取得全体の「森」を示す。
内部監査・マネジメントレビュー・申請準備はまだMVPで実装していないため、
未完了とは判定せず「後続工程」として明示する。
"""

from __future__ import annotations

from dataclasses import dataclass
from html import escape

from app.dashboard import DashboardData, OperationalAreaSummary
from app.intake_schemas import SetupStatus


@dataclass(frozen=True)
class AcquisitionPlanStep:
    number: int
    name: str
    description: str
    status: str
    status_kind: str
    link: str | None
    implemented: bool
    current: bool = False


@dataclass(frozen=True)
class AcquisitionPlan:
    steps: list[AcquisitionPlanStep]
    implemented_completed: int
    implemented_total: int
    current_text: str


def _first_operation_link(areas: list[OperationalAreaSummary]) -> str:
    adopted = [area for area in areas if area.adopted]
    needs_action = [area for area in adopted if area.css_class != "compliant"]
    if needs_action:
        return needs_action[0].link
    if adopted:
        return adopted[0].link
    return "/setup#step5"


def _setup_status(data: DashboardData) -> tuple[str, str, bool]:
    if data.setup_status == SetupStatus.COMPLETE:
        return "完了", "complete", True
    if data.setup_status == SetupStatus.IN_PROGRESS:
        return "対応中", "current", False
    return "未着手", "pending", False


def _documents_status(data: DashboardData) -> tuple[str, str, bool]:
    if data.setup_status != SetupStatus.COMPLETE:
        return "初期設定後", "pending", False
    if data.documents_draft_count:
        return "対応中", "current", False
    return "完了", "complete", True


def _operations_status(data: DashboardData) -> tuple[str, str, bool]:
    if data.setup_status != SetupStatus.COMPLETE:
        return "初期設定後", "pending", False

    adopted = [area for area in data.operational_areas if area.adopted]
    if not adopted:
        return "対象なし", "complete", True
    if all(area.css_class == "compliant" for area in adopted):
        return "完了", "complete", True
    return "対応中", "current", False


def build_acquisition_plan(data: DashboardData) -> AcquisitionPlan:
    """現在の集約状態から、MVPで判定可能な取得ロードマップを組み立てる。"""

    setup_status, setup_kind, setup_complete = _setup_status(data)
    docs_status, docs_kind, docs_complete = _documents_status(data)
    operations_status, operations_kind, operations_complete = _operations_status(data)

    implemented_raw = [
        (
            1,
            "初期設定",
            "会社・PMS体制、業務、個人情報、リスク、管理策を整理・確定します。",
            setup_status,
            setup_kind,
            "/setup",
            setup_complete,
        ),
        (
            2,
            "PMS文書準備",
            "個人情報管理台帳や、採用した管理策に対応する規程・手順の準備状況を確認します。",
            docs_status,
            docs_kind,
            "/documents",
            docs_complete,
        ),
        (
            3,
            "採用管理策の運用",
            "教育・委託先・アクセス権限・紙媒体など、採用した管理策の実施記録を整えます。",
            operations_status,
            operations_kind,
            _first_operation_link(data.operational_areas),
            operations_complete,
        ),
    ]

    current_number: int | None = None
    for number, _, _, _, _, _, complete in implemented_raw:
        if not complete:
            current_number = number
            break

    steps: list[AcquisitionPlanStep] = []
    for number, name, description, status, status_kind, link, complete in implemented_raw:
        steps.append(
            AcquisitionPlanStep(
                number=number,
                name=name,
                description=description,
                status=status,
                status_kind=status_kind,
                link=link,
                implemented=True,
                current=number == current_number,
            )
        )

    future_steps = (
        (4, "内部監査", "PMSが定めたとおり運用されているかを内部監査で確認します。"),
        (5, "マネジメントレビュー", "監査や運用結果を経営層が確認し、改善・次の方針につなげます。"),
        (6, "申請準備", "申請に必要な情報・文書・運用記録を最終確認します。"),
    )
    for number, name, description in future_steps:
        steps.append(
            AcquisitionPlanStep(
                number=number,
                name=name,
                description=description,
                status="後続工程",
                status_kind="future",
                link=None,
                implemented=False,
            )
        )

    completed = sum(1 for item in (setup_complete, docs_complete, operations_complete) if item)
    if current_number is None:
        current_text = "MVP実装範囲完了（次の後続工程：4. 内部監査）"
    else:
        current_name = next(step.name for step in steps if step.number == current_number)
        current_text = f"{current_number}. {current_name}"

    return AcquisitionPlan(
        steps=steps,
        implemented_completed=completed,
        implemented_total=3,
        current_text=current_text,
    )


def _status_style(kind: str) -> str:
    return {
        "complete": "background:#0a7a0a;color:#fff;",
        "current": "background:#b36b00;color:#fff;",
        "pending": "background:#666;color:#fff;",
        "future": "background:#eee;color:#555;border:1px solid #bbb;",
    }[kind]


def render_acquisition_plan(plan: AcquisitionPlan) -> str:
    rows: list[str] = []
    for step in plan.steps:
        current_marker = " ← 現在" if step.current else ""
        row_style = "background:#fff8ef;" if step.current else ""
        if step.link:
            action = f'<a href="{escape(step.link)}">確認する</a>'
        else:
            action = "—"
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

    return f"""
    <section class="acquisition-plan" style="border:1px solid #bbb;border-radius:4px;padding:16px;margin:24px 0;">
      <h2 style="margin-top:0;">Pマーク取得の全体計画</h2>
      <p>まず全体の順序と現在地を確認し、その後で下の詳細へ進みます。現在はMVPで自動判定できる範囲を表示し、内部監査以降は後続工程として示しています。</p>
      <p><strong>実装範囲進捗：{plan.implemented_completed} / {plan.implemented_total} 工程 完了</strong></p>
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
      <p style="font-size:0.9em;color:#666;">具体的な開始日・目標申請日を持つ年間計画への展開は、後続機能として追加できる構造にしています。</p>
    </section>
    """


def enhance_dashboard_with_plan(html: str, data: DashboardData) -> str:
    """既存ダッシュボードの「今やること」より前に取得ロードマップを挿入する。"""

    plan_html = render_acquisition_plan(build_acquisition_plan(data))
    marker = '<section class="todo-section">'
    if marker in html:
        return html.replace(marker, plan_html + marker, 1)
    return html.replace("</p>", "</p>" + plan_html, 1)
