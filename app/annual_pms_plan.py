"""取得後の年間PMS運用計画を表現するための計画ビルダー。

現MVPで実際に状態判定できる教育・委託先・アクセス権限・紙媒体を、年間運用計画の
一部として配置する。年度計画、個人情報・リスクの定期見直し、内部監査、是正、
マネジメントレビューはまだ専用の記録機能がないため、完了とは判定せず後続実装とする。

このモジュールは将来トップ画面を「取得計画」から「年間運用計画」へ切り替える際の
土台であり、現時点では取得中の利用者画面へ自動表示しない。
"""

from __future__ import annotations

from app.dashboard import DashboardData, OperationalAreaSummary
from app.intake_schemas import SetupStatus
from app.plan_models import Plan, PlanStep


_OPERATION_STEP_DEFINITIONS: tuple[tuple[str, int, str, str], ...] = (
    (
        "education",
        3,
        "教育",
        "従業者への個人情報保護教育を実施し、受講・理解度・承認の記録を残します。",
    ),
    (
        "vendor_management",
        4,
        "委託先評価",
        "委託先の評価、契約確認、定期評価の記録を維持します。",
    ),
    (
        "access_control",
        5,
        "アクセス権限棚卸し",
        "アカウントと権限を棚卸しし、不要権限の処理と承認記録を残します。",
    ),
    (
        "paper_management",
        6,
        "紙媒体管理",
        "保管・持出し・廃棄の管理状況を確認し、実施記録を残します。",
    ),
)


def _area_by_id(data: DashboardData, control_id: str) -> OperationalAreaSummary | None:
    return next((area for area in data.operational_areas if area.control_id == control_id), None)


def _operation_step(
    data: DashboardData,
    *,
    control_id: str,
    number: int,
    name: str,
    description: str,
) -> tuple[PlanStep, bool, bool]:
    """1管理領域を年間計画用Stepへ変換する。

    戻り値は (step, tracked, complete)。採用済みだけを年間運用の進捗母数へ含める。
    """

    area = _area_by_id(data, control_id)
    if data.setup_status != SetupStatus.COMPLETE:
        return (
            PlanStep(
                number=number,
                name=name,
                description=description,
                status="初期設定後",
                status_kind="pending",
                link="/setup#step5",
                implemented=True,
            ),
            False,
            False,
        )

    if area is None or not area.adopted:
        label = area.label if area is not None else "対象外"
        return (
            PlanStep(
                number=number,
                name=name,
                description=description,
                status=label,
                status_kind="not-applicable",
                link=area.link if area is not None else None,
                implemented=True,
            ),
            False,
            False,
        )

    complete = area.css_class == "compliant"
    return (
        PlanStep(
            number=number,
            name=name,
            description=description,
            status="完了" if complete else "対応中",
            status_kind="complete" if complete else "current",
            link=area.link,
            implemented=True,
        ),
        True,
        complete,
    )


def build_annual_pms_plan(data: DashboardData) -> Plan:
    """DashboardDataから、取得後の年間PMS運用計画テンプレートを組み立てる。"""

    steps: list[PlanStep] = [
        PlanStep(
            number=1,
            name="年度運用計画・体制確認",
            description="年度の運用方針、担当体制、実施予定を確認します。",
            status="後続実装",
            status_kind="future",
            implemented=False,
        ),
        PlanStep(
            number=2,
            name="個人情報台帳・リスク見直し",
            description="業務変更を踏まえて個人情報台帳、リスク、管理策を定期的に見直します。",
            status="後続実装",
            status_kind="future",
            implemented=False,
        ),
    ]

    tracked_steps: list[tuple[int, bool]] = []
    for control_id, number, name, description in _OPERATION_STEP_DEFINITIONS:
        step, tracked, complete = _operation_step(
            data,
            control_id=control_id,
            number=number,
            name=name,
            description=description,
        )
        steps.append(step)
        if tracked:
            tracked_steps.append((number, complete))

    steps.extend(
        [
            PlanStep(
                number=7,
                name="内部監査",
                description="PMSが定めたとおり運用されているかを内部監査で確認します。",
                status="後続実装",
                status_kind="future",
                implemented=False,
            ),
            PlanStep(
                number=8,
                name="是正・改善",
                description="監査や運用で見つかった不足について、是正と有効性確認を行います。",
                status="後続実装",
                status_kind="future",
                implemented=False,
            ),
            PlanStep(
                number=9,
                name="マネジメントレビュー・次年度計画",
                description="経営層が運用結果を確認し、改善事項と次年度の計画につなげます。",
                status="後続実装",
                status_kind="future",
                implemented=False,
            ),
        ]
    )

    current_number = next((number for number, complete in tracked_steps if not complete), None)
    if current_number is not None:
        steps = [
            step.__class__(**{**step.__dict__, "current": step.number == current_number})
            for step in steps
        ]
        current_name = next(step.name for step in steps if step.number == current_number)
        current_text = f"{current_number}. {current_name}"
    elif tracked_steps:
        current_text = "現MVP運用範囲完了（次の後続工程：7. 内部監査）"
    elif data.setup_status != SetupStatus.COMPLETE:
        current_text = "初期設定完了後に年間運用対象を確定"
    else:
        current_text = "年間運用対象の管理策を確認"

    return Plan(
        title="年間PMS運用計画",
        description=(
            "取得後の運用でも、年間の全体像から現在地を確認し、各管理領域の記録へ降りる構造を使います。"
            "現MVPでは採用済みの4管理領域だけを進捗判定します。"
        ),
        steps=steps,
        completed_count=sum(1 for _, complete in tracked_steps if complete),
        tracked_total=len(tracked_steps),
        current_text=current_text,
        progress_label="現MVP運用範囲進捗",
        footer_note=(
            "年間の実施月、期限、担当者、証跡へのリンクは、今後この共通計画モデルへ追加できます。"
        ),
    )
