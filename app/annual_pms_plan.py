"""取得後の年間PMS運用計画を表現する計画ビルダー。

教育・委託先・アクセス権限・紙媒体に加え、内部監査・必要な是正処置・
マネジメントレビューも同じ年間サイクルへ接続する。年度計画や台帳・リスクの
定期見直しは専用記録機能がまだないため、引き続き後続実装として示す。
"""

from __future__ import annotations

from dataclasses import replace

from app.dashboard import DashboardData, OperationalAreaSummary
from app.intake_schemas import SetupStatus
from app.plan_models import Plan, PlanStep
from app.pms_review_schemas import PmsReviewEvaluationResult


_OPERATION_STEP_DEFINITIONS: tuple[tuple[str, int, str, str], ...] = (
    ("education", 3, "教育", "従業者への個人情報保護教育を実施し、受講・理解度・承認の記録を残します。"),
    ("vendor_management", 4, "委託先評価", "委託先の評価、契約確認、定期評価の記録を維持します。"),
    ("access_control", 5, "アクセス権限棚卸し", "アカウントと権限を棚卸しし、不要権限の処理と承認記録を残します。"),
    ("paper_management", 6, "紙媒体管理", "保管・持出し・廃棄の管理状況を確認し、実施記録を残します。"),
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
    area = _area_by_id(data, control_id)
    if data.setup_status != SetupStatus.COMPLETE:
        return PlanStep(number, name, description, "初期設定後", "pending", "/setup#step5"), False, False
    if area is None or not area.adopted:
        label = area.label if area is not None else "対象外"
        return PlanStep(number, name, description, label, "not-applicable", area.link if area else None), False, False
    complete = area.css_class == "compliant"
    return (
        PlanStep(number, name, description, "完了" if complete else "対応中", "complete" if complete else "current", area.link),
        True,
        complete,
    )


def _review_steps(
    review_result: PmsReviewEvaluationResult | None,
) -> tuple[list[PlanStep], list[tuple[int, bool]]]:
    if review_result is None:
        return (
            [
                PlanStep(7, "内部監査", "PMSが定めたとおり運用されているかを内部監査で確認します。", "後続実装", "future", implemented=False),
                PlanStep(8, "是正・改善", "監査や運用で見つかった不足について、是正と有効性確認を行います。", "後続実装", "future", implemented=False),
                PlanStep(9, "マネジメントレビュー・次年度計画", "経営層が運用結果を確認し、改善事項と次年度の計画につなげます。", "後続実装", "future", implemented=False),
            ],
            [],
        )

    audit_complete = review_result.audit_complete
    audit_step = PlanStep(
        7,
        "内部監査",
        "監査目的・基準・範囲・客観性を明確にし、結果を管理層・トップマネジメントへ報告します。",
        "完了" if audit_complete else "対応中",
        "complete" if audit_complete else "current",
        "/pms-review",
    )

    if not audit_complete:
        correction_complete = False
        correction_status = "監査結果待ち"
        correction_kind = "pending"
    elif not review_result.corrective_required:
        correction_complete = True
        correction_status = "対象なし"
        correction_kind = "not-applicable"
    else:
        correction_complete = review_result.corrective_complete
        correction_status = "完了" if correction_complete else "対応中"
        correction_kind = "complete" if correction_complete else "current"
    correction_step = PlanStep(
        8,
        "是正・改善",
        "不適合がある場合、原因分析・是正処置・有効性確認・承認まで記録します。",
        correction_status,
        correction_kind,
        "/pms-review",
    )

    review_complete = review_result.management_review_complete
    prereq_complete = audit_complete and correction_complete
    review_step = PlanStep(
        9,
        "マネジメントレビュー・次年度計画",
        "監査・是正・リスク・運用状況等をトップマネジメントが見直し、改善や変更の必要性を決定します。",
        "完了" if review_complete else ("対応中" if prereq_complete else "監査・是正後"),
        "complete" if review_complete else ("current" if prereq_complete else "pending"),
        "/pms-review",
    )
    return [audit_step, correction_step, review_step], [
        (7, audit_complete),
        (8, correction_complete),
        (9, review_complete),
    ]


def build_annual_pms_plan(
    data: DashboardData,
    review_result: PmsReviewEvaluationResult | None = None,
) -> Plan:
    steps: list[PlanStep] = [
        PlanStep(1, "年度運用計画・体制確認", "年度の運用方針、担当体制、実施予定を確認します。", "後続実装", "future", implemented=False),
        PlanStep(2, "個人情報台帳・リスク見直し", "業務変更を踏まえて個人情報台帳、リスク、管理策を定期的に見直します。", "後続実装", "future", implemented=False),
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

    review_steps, review_tracking = _review_steps(review_result)
    steps.extend(review_steps)
    tracked_steps.extend(review_tracking)

    current_number = next((number for number, complete in tracked_steps if not complete), None)
    if current_number is not None:
        steps = [replace(step, current=step.number == current_number) for step in steps]
        current_name = next(step.name for step in steps if step.number == current_number)
        current_text = f"{current_number}. {current_name}"
    elif tracked_steps:
        current_text = (
            "現MVP運用範囲完了（次の後続工程：7. 内部監査）"
            if review_result is None
            else "現MVP運用範囲完了"
        )
    elif data.setup_status != SetupStatus.COMPLETE:
        current_text = "初期設定完了後に年間運用対象を確定"
    else:
        current_text = "年間運用対象の管理策を確認"

    return Plan(
        title="年間PMS運用計画",
        description="取得後も年間の全体像から現在地を確認し、運用記録・内部監査・是正・マネジメントレビューへ順に降りる構造を使います。",
        steps=steps,
        completed_count=sum(1 for _, complete in tracked_steps if complete),
        tracked_total=len(tracked_steps),
        current_text=current_text,
        progress_label="現MVP運用範囲進捗",
        footer_note="年間の実施月、期限、担当者、証跡へのリンクは、今後この共通計画モデルへ追加できます。",
    )
