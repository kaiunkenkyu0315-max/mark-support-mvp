"""トップダッシュボードに表示するPマーク取得ロードマップ。

取得計画固有の状態判定だけを担当し、計画モデルとHTML描画は共通部品へ分離する。
同じ「森→現在地→詳細」の形式を年間PMS運用計画にも再利用する。
"""

from __future__ import annotations

from app.dashboard import DashboardData, OperationalAreaSummary
from app.intake_schemas import SetupStatus
from app.plan_models import Plan, PlanStep
from app.plan_view import render_plan
from app.pms_review_schemas import PmsReviewEvaluationResult


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
    if data.personal_information_confirmed_count == 0:
        return "/setup#step2"
    return "/documents"


def _operations_link(data: DashboardData) -> str:
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


def _audit_status(
    operations_complete: bool,
    review_result: PmsReviewEvaluationResult | None,
) -> tuple[str, str, bool]:
    if not operations_complete:
        return "運用完了後", "pending", False
    if review_result is None:
        return "後続工程", "future", False
    complete = review_result.audit_complete and (
        not review_result.corrective_required or review_result.corrective_complete
    )
    return ("完了", "complete", True) if complete else ("対応中", "current", False)


def _management_review_status(
    audit_complete: bool,
    review_result: PmsReviewEvaluationResult | None,
) -> tuple[str, str, bool]:
    if not audit_complete:
        return "監査・是正後", "pending", False
    if review_result is None:
        return "後続工程", "future", False
    complete = review_result.management_review_complete
    return ("完了", "complete", True) if complete else ("対応中", "current", False)


def build_acquisition_plan(
    data: DashboardData,
    review_result: PmsReviewEvaluationResult | None = None,
) -> Plan:
    """現在の状態から取得ロードマップを組み立てる。

    review_resultを渡した場合は内部監査・是正・マネジメントレビューまで追跡する。
    省略した呼び出しは初期設定〜運用までの3工程を追跡する。
    """

    setup_status, setup_kind, setup_complete = _setup_status(data)
    docs_status, docs_kind, docs_complete = _documents_status(data)
    operations_status, operations_kind, operations_complete = _operations_status(data)
    audit_status, audit_kind, audit_complete = _audit_status(operations_complete, review_result)
    mr_status, mr_kind, mr_complete = _management_review_status(audit_complete, review_result)

    implemented_raw = [
        (1, "初期設定", "会社・PMS体制、業務、個人情報、リスク、管理策を整理・確定します。", setup_status, setup_kind, "/setup", setup_complete),
        (2, "PMS文書準備", "個人情報管理台帳や、採用した管理策に対応する規程・手順の準備状況を確認します。", docs_status, docs_kind, _documents_link(data), docs_complete),
        (3, "採用管理策の運用", "教育・委託先・アクセス権限・紙媒体など、採用した管理策の実施記録を整えます。", operations_status, operations_kind, _operations_link(data), operations_complete),
    ]
    if review_result is not None:
        implemented_raw.extend(
            [
                (4, "内部監査・是正", "PMSの適合性・有効性を内部監査で確認し、不適合があれば原因分析・是正・有効性確認を行います。", audit_status, audit_kind, "/pms-review", audit_complete),
                (5, "マネジメントレビュー", "監査・是正・リスク・運用状況等をトップマネジメントが見直し、改善や変更の必要性を決定します。", mr_status, mr_kind, "/pms-review", mr_complete),
            ]
        )

    current_number: int | None = None
    for number, _, _, _, _, _, complete in implemented_raw:
        if not complete:
            current_number = number
            break

    steps = [
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
        for number, name, description, status, status_kind, link, _complete in implemented_raw
    ]

    next_number = len(implemented_raw) + 1
    if review_result is None:
        future_steps = (
            (4, "内部監査", "PMSが定めたとおり運用されているかを内部監査で確認します。"),
            (5, "マネジメントレビュー", "監査や運用結果を経営層が確認し、改善・次の方針につなげます。"),
            (6, "申請準備", "申請に必要な情報・文書・運用記録を最終確認します。"),
        )
    else:
        future_steps = ((6, "申請準備", "申請に必要な情報・文書・運用記録を最終確認します。"),)

    for number, name, description in future_steps:
        steps.append(
            PlanStep(
                number=number,
                name=name,
                description=description,
                status="後続工程",
                status_kind="future",
                implemented=False,
            )
        )

    tracked_completions = [item[6] for item in implemented_raw]
    completed = sum(1 for complete in tracked_completions if complete)
    if current_number is None:
        current_text = f"準備工程完了（次の工程：{next_number}. {next(step.name for step in steps if step.number == next_number)}）"
    else:
        current_name = next(step.name for step in steps if step.number == current_number)
        current_text = f"{current_number}. {current_name}"

    return Plan(
        title="Pマーク取得の全体計画",
        description="申請準備までの全体の順序と現在地を示しています。作業は下の「次にやること」から順番に進めてください。",
        steps=steps,
        completed_count=completed,
        tracked_total=len(implemented_raw),
        current_text=current_text,
        progress_label="取得準備の進捗",
        footer_note="この計画は申請準備までの標準的な進め方を示します。実際の申請・審査は選択した審査機関の手続に従います。",
    )


def render_acquisition_plan(plan: Plan) -> str:
    return render_plan(
        plan,
        css_class="acquisition-plan",
        current_only_actions=True,
    )


def enhance_dashboard_with_plan(
    html: str,
    data: DashboardData,
    review_result: PmsReviewEvaluationResult | None = None,
) -> str:
    plan_html = render_acquisition_plan(build_acquisition_plan(data, review_result))
    marker = '<section class="todo-section">'
    if marker in html:
        return html.replace(marker, plan_html + marker, 1)
    return html.replace("</p>", "</p>" + plan_html, 1)
