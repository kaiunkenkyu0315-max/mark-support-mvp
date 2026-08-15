"""教育管理の整合性判定ロジック。

事実データ（Employee / TrainingControl / TrainingPlan / TrainingRecord）に
業務ルールを適用し、評価結果（EducationEvaluationResult）を導出する。

FastAPIやHTTP処理には依存しない、純粋な業務ロジックとして実装する。
"""

from __future__ import annotations

from app.schemas import (
    EducationEvaluationResult,
    EducationEvaluationStatus,
    EducationIssue,
    Employee,
    EmployeeRole,
    EmployeeStatus,
    TrainingControl,
    TrainingPlan,
    TrainingRecord,
)

# 役割の表示ラベル。教育管理画面（app.education_view）・文書生成（app.document_templates）の
# 双方から参照される、事実データ（EmployeeRole）に対する表示名の単一の定義。
ROLE_LABELS: dict[EmployeeRole, str] = {
    EmployeeRole.EXECUTIVE: "経営者",
    EmployeeRole.PRIVACY_MANAGER: "個人情報保護管理者",
    EmployeeRole.PMARK_STAFF: "Pマーク担当者",
    EmployeeRole.GENERAL_EMPLOYEE: "一般従業員",
}


def frequency_label(control: TrainingControl) -> str:
    """教育管理策の実施頻度を表示用ラベルへ変換する。"""

    return "年1回" if control.frequency.value == "annual" else control.frequency.value


def evaluate_training(
    employees: list[Employee],
    control: TrainingControl,
    plan: TrainingPlan,
    records: list[TrainingRecord],
) -> EducationEvaluationResult:
    """教育管理策に対する実施状況を評価する。

    判定対象者は、status が active かつ role が control.target_roles に
    含まれる従業者のみとする。
    """

    targets = [
        employee
        for employee in employees
        if employee.status == EmployeeStatus.ACTIVE and employee.role in control.target_roles
    ]
    target_ids = [employee.id for employee in targets]

    records_by_employee = {record.employee_id: record for record in records}

    issues: list[EducationIssue] = []

    # EDU-003: 未受講者
    # completed=true の受講記録が存在しない対象者を不足とする。
    not_completed_ids = [
        employee_id
        for employee_id in target_ids
        if not (
            employee_id in records_by_employee and records_by_employee[employee_id].completed
        )
    ]
    if not_completed_ids:
        issues.append(
            EducationIssue(
                rule_id="EDU-003",
                message=f"未受講者が{len(not_completed_ids)}名います。",
                employee_ids=not_completed_ids,
            )
        )

    completed_ids = [
        employee_id for employee_id in target_ids if employee_id not in not_completed_ids
    ]

    # EDU-006: 理解度確認
    # 受講済み対象者について comprehension_result が未登録(None)なら不足とする。
    if control.comprehension_required:
        missing_comprehension_ids = [
            employee_id
            for employee_id in completed_ids
            if records_by_employee[employee_id].comprehension_result is None
        ]
        if missing_comprehension_ids:
            issues.append(
                EducationIssue(
                    rule_id="EDU-006",
                    message=(
                        f"理解度確認が未登録の受講者が{len(missing_comprehension_ids)}名います。"
                    ),
                    employee_ids=missing_comprehension_ids,
                )
            )

    # EDU-008: 教材証跡
    if control.material_evidence_required and not plan.material_evidence_registered:
        issues.append(
            EducationIssue(
                rule_id="EDU-008",
                message="教材証跡が未登録です。",
            )
        )

    # EDU-009: 承認
    if control.approval_required and not plan.approved:
        issues.append(
            EducationIssue(
                rule_id="EDU-009",
                message="実施結果が未承認です。",
            )
        )

    status = (
        EducationEvaluationStatus.NEEDS_ACTION if issues else EducationEvaluationStatus.COMPLIANT
    )

    return EducationEvaluationResult(
        status=status,
        target_employee_ids=target_ids,
        issues=issues,
    )
