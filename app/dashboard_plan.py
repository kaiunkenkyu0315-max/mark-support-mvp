"""トップダッシュボードに表示するPマーク取得ロードマップ。

取得計画固有の状態判定だけを担当し、計画モデルとHTML描画は共通部品へ分離する。
これにより、同じ「森→現在地→詳細」の形式を年間PMS運用計画にも再利用できる。

またトップの「今やること」は同じ管理領域の不足を複数並べず、領域ごとに
最初の1件だけへ絞る。詳細な不足は各管理画面の全体工程へ降りて確認する。
"""

from __future__ import annotations

from app.dashboard import DashboardData, OperationalAreaSummary
from app.intake_schemas import SetupStatus
from app.plan_models import Plan, PlanStep
from app.plan_view import render_plan


def focus_dashboard_todos(data: DashboardData) -> None:
    """トップ画面用にtodoを管理領域ごと1件へ絞る。"""

    focused = []
    seen_areas: set[str] = set()
    for item in data.todo_items:
        if item.area in seen_areas:
            continue
        seen_areas.add(item.area)
        focused.append(item)
    data.todo_items = focused


def _first_operation_link(areas: list[OperationalAreaSummary]) -> str:
    adopted = [area for area in areas if area.adopted]
    needs_action = [area for area in adopted if area.css_class != "compliant"]
    if needs_action:
        return needs_action[0].link
    if adopted:
        return adopted[0].link
    return "/setup#step5"


def _documents_link(data: DashboardData) -> str:
    """文書画面へ進める前提がなければ、必要な初期設定工程へ戻す。"""

    if data.personal_information_confirmed_count == 0:
        return "/setup#step2"
    return "/documents"


def _operations_link(data: DashboardData) -> str:
    """初期設定完了前は運用画面へ直接入れず、管理策確認へ案内する。"""

    if data.setup_status != SetupStatus.COMPLETE:
        return "/setup#step5"
    return _first_operation_link(data.operational_areas)


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


def build_acquisition_plan(data: DashboardData) -> Plan:
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
            _documents_link(data),
            docs_complete,
        ),
        (
            3,
            "採用管理策の運用",
            "教育・委託先・アクセス権限・紙媒体など、採用した管理策の実施記録を整えます。",
            operations_status,
            operations_kind,
            _operations_link(data),
            operations_complete,
        ),
    ]

    current_number: int | None = None
    for number, _, _, _, _, _, complete in implemented_raw:
        if not complete:
            current_number = number
            break

    steps: list[PlanStep] = []
    for number, name, description, status, status_kind, link, _complete in implemented_raw:
        steps.append(
            PlanStep(
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
            PlanStep(
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

    return Plan(
        title="Pマーク取得の全体計画",
        description=(
            "まず全体の順序と現在地を確認し、その後で下の詳細へ進みます。"
            "現在はMVPで自動判定できる範囲を表示し、内部監査以降は後続工程として示しています。"
        ),
        steps=steps,
        completed_count=completed,
        tracked_total=3,
        current_text=current_text,
        progress_label="実装範囲進捗",
        footer_note=(
            "具体的な開始日・目標申請日を持つ計画や、取得後の年間PMS運用計画も、"
            "同じ計画形式へ拡張できる構造にしています。"
        ),
    )


def render_acquisition_plan(plan: Plan) -> str:
    """既存呼び出し名を維持しつつ、共通計画描画器を利用する。"""

    return render_plan(plan, css_class="acquisition-plan")


def enhance_dashboard_with_plan(html: str, data: DashboardData) -> str:
    """既存ダッシュボードの「今やること」より前に取得ロードマップを挿入する。"""

    plan_html = render_acquisition_plan(build_acquisition_plan(data))
    marker = '<section class="todo-section">'
    if marker in html:
        return html.replace(marker, plan_html + marker, 1)
    return html.replace("</p>", "</p>" + plan_html, 1)
