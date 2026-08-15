"""教育管理MVPのデモ用インメモリ状態。

サーバー起動時に固定のデモデータ（株式会社サンプル・従業者50名）を構築する。
ブラウザからの操作はこのモジュールが保持するインメモリ状態のみを変更し、
DBは使用しない。サーバー再起動で初期状態に戻る。

事実データ（Employee / TrainingRecord 等）に評価情報は持たせない。
ここで行うのは事実データの登録・更新のみであり、適合／要対応の判定は
app.education.evaluate_training が行う。
"""

from __future__ import annotations

from dataclasses import dataclass

from app.schemas import (
    Company,
    ComprehensionResult,
    Employee,
    EmployeeRole,
    EmployeeStatus,
    TrainingControl,
    TrainingFrequency,
    TrainingPlan,
    TrainingRecord,
)

ALL_ROLES = [
    EmployeeRole.EXECUTIVE,
    EmployeeRole.PRIVACY_MANAGER,
    EmployeeRole.PMARK_STAFF,
    EmployeeRole.GENERAL_EMPLOYEE,
]

# 初期デモ状態で、意図的に未受講のままにしておく従業員ID（2名）。
NOT_COMPLETED_EMPLOYEE_IDS = {49, 50}
# 初期デモ状態で、受講済みだが理解度確認が未登録のままの従業員ID（3名）。
MISSING_COMPREHENSION_EMPLOYEE_IDS = {46, 47, 48}

# 教育に関する標準規程条項のプレビュー（今回のMVPでは全文書生成はしない）。
POLICY_CLAUSES = [
    "当社は、個人情報を取り扱う従業者に対し、少なくとも年1回、個人情報保護教育を実施する。",
    "教育責任者は、教育後に理解度を確認し、必要に応じて再教育を実施する。",
    "教育の実施結果、対象者、受講状況等を記録し保存する。",
]


@dataclass
class EducationDemoState:
    company: Company
    employees: list[Employee]
    control: TrainingControl
    plan: TrainingPlan
    records: list[TrainingRecord]


def _build_employees() -> list[Employee]:
    employees = [
        Employee(
            id=1, name="代表 花子", role=EmployeeRole.EXECUTIVE, status=EmployeeStatus.ACTIVE
        ),
        Employee(
            id=2,
            name="個人情報保護 次郎",
            role=EmployeeRole.PRIVACY_MANAGER,
            status=EmployeeStatus.ACTIVE,
        ),
        Employee(
            id=3,
            name="Pマーク 担当子",
            role=EmployeeRole.PMARK_STAFF,
            status=EmployeeStatus.ACTIVE,
        ),
    ]
    employees.extend(
        Employee(
            id=employee_id,
            name=f"一般従業員{employee_id:02d}",
            role=EmployeeRole.GENERAL_EMPLOYEE,
            status=EmployeeStatus.ACTIVE,
        )
        for employee_id in range(4, 51)
    )
    return employees


def _build_records() -> list[TrainingRecord]:
    records = []
    for employee_id in range(1, 51):
        if employee_id in NOT_COMPLETED_EMPLOYEE_IDS:
            records.append(TrainingRecord(employee_id=employee_id, completed=False))
        elif employee_id in MISSING_COMPREHENSION_EMPLOYEE_IDS:
            records.append(TrainingRecord(employee_id=employee_id, completed=True))
        else:
            records.append(
                TrainingRecord(
                    employee_id=employee_id,
                    completed=True,
                    comprehension_result=ComprehensionResult.PASSED,
                )
            )
    return records


def build_initial_state() -> EducationDemoState:
    """デモの初期状態（意図的に不足を残した状態）を構築する。"""

    company = Company(id=1, name="株式会社サンプル", fiscal_year=2026)
    control = TrainingControl(
        id=1,
        name="個人情報保護教育",
        frequency=TrainingFrequency.ANNUAL,
        target_roles=ALL_ROLES,
        comprehension_required=True,
        material_evidence_required=True,
        approval_required=True,
    )
    plan = TrainingPlan(
        id=1,
        title="2026年度 個人情報保護教育計画",
        fiscal_year=2026,
        control_id=1,
        material_evidence_registered=False,
        approved=False,
    )
    return EducationDemoState(
        company=company,
        employees=_build_employees(),
        control=control,
        plan=plan,
        records=_build_records(),
    )


_state: EducationDemoState = build_initial_state()


def get_state() -> EducationDemoState:
    """現在のデモ状態を取得する。"""

    return _state


def reset_state() -> EducationDemoState:
    """デモ状態を初期状態へ戻す。"""

    global _state
    _state = build_initial_state()
    return _state


def complete_all_trainings() -> None:
    """未受講の従業者をすべて受講済みにする（操作1）。"""

    for record in _state.records:
        if not record.completed:
            record.completed = True


def register_missing_comprehension(
    result: ComprehensionResult = ComprehensionResult.PASSED,
) -> None:
    """理解度確認が未登録の受講済み記録に、簡易値を登録する（操作2）。"""

    for record in _state.records:
        if record.completed and record.comprehension_result is None:
            record.comprehension_result = result


def register_material_evidence() -> None:
    """教材証跡を登録済みにする（操作3）。"""

    _state.plan.material_evidence_registered = True


def approve_plan() -> None:
    """実施結果を承認済みにする（操作4）。"""

    _state.plan.approved = True
