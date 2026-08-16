"""教育管理MVPのデモ用インメモリ状態。

会社名・従業者数・対象年度は app.company_profile を共通の正本として参照する。
教育管理側では、その会社情報を前提に従業者・教育計画・教育記録のデモ状態を構築する。
ブラウザからの操作はインメモリ状態のみを変更し、DBは使用しない。

事実データ（Employee / TrainingRecord 等）に評価情報は持たせない。
ここで行うのは事実データの登録・更新のみであり、適合／要対応の判定は
app.education.evaluate_training が行う。
"""

from __future__ import annotations

from dataclasses import dataclass

from app import company_profile
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

# 50名の既定デモでは従来どおり、49・50を未受講、46〜48を理解度未登録にする。
NOT_COMPLETED_EMPLOYEE_IDS = {49, 50}
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


def _employee_role(employee_id: int) -> EmployeeRole:
    if employee_id == 1:
        return EmployeeRole.EXECUTIVE
    if employee_id == 2:
        return EmployeeRole.PRIVACY_MANAGER
    if employee_id == 3:
        return EmployeeRole.PMARK_STAFF
    return EmployeeRole.GENERAL_EMPLOYEE


def _employee_name(employee_id: int) -> str:
    if employee_id == 1:
        return "代表 花子"
    if employee_id == 2:
        return "個人情報保護 次郎"
    if employee_id == 3:
        return "Pマーク 担当子"
    return f"一般従業員{employee_id:02d}"


def _build_employees(employee_count: int) -> list[Employee]:
    return [
        Employee(
            id=employee_id,
            name=_employee_name(employee_id),
            role=_employee_role(employee_id),
            status=EmployeeStatus.ACTIVE,
        )
        for employee_id in range(1, employee_count + 1)
    ]


def _demo_issue_employee_ids(employee_count: int) -> tuple[set[int], set[int]]:
    """任意人数でも教育の不足検知を確認できるよう、末尾側にデモ不足を配置する。"""

    if employee_count == 50:
        return NOT_COMPLETED_EMPLOYEE_IDS, MISSING_COMPREHENSION_EMPLOYEE_IDS

    not_completed_count = min(2, employee_count)
    not_completed = set(range(employee_count - not_completed_count + 1, employee_count + 1))

    remaining = employee_count - not_completed_count
    missing_count = min(3, remaining)
    missing_start = remaining - missing_count + 1
    missing_comprehension = (
        set(range(missing_start, remaining + 1)) if missing_count > 0 else set()
    )
    return not_completed, missing_comprehension


def _build_records(employee_count: int) -> list[TrainingRecord]:
    not_completed_ids, missing_comprehension_ids = _demo_issue_employee_ids(employee_count)
    records: list[TrainingRecord] = []
    for employee_id in range(1, employee_count + 1):
        if employee_id in not_completed_ids:
            records.append(TrainingRecord(employee_id=employee_id, completed=False))
        elif employee_id in missing_comprehension_ids:
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
    """現在の共通会社情報から、教育管理のデモ初期状態を構築する。"""

    profile = company_profile.get_state()
    company = Company(id=1, name=profile.name, fiscal_year=profile.fiscal_year)
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
        title=f"{profile.fiscal_year}年度 個人情報保護教育計画",
        fiscal_year=profile.fiscal_year,
        control_id=1,
        material_evidence_registered=False,
        approved=False,
    )
    return EducationDemoState(
        company=company,
        employees=_build_employees(profile.employee_count),
        control=control,
        plan=plan,
        records=_build_records(profile.employee_count),
    )


_state: EducationDemoState = build_initial_state()


def _matches_company_profile(state: EducationDemoState) -> bool:
    profile = company_profile.get_state()
    return (
        state.company.name == profile.name
        and state.company.fiscal_year == profile.fiscal_year
        and len(state.employees) == profile.employee_count
    )


def get_state() -> EducationDemoState:
    """現在の教育状態を取得する。会社情報が変わっていれば再構築して追随する。"""

    global _state
    if not _matches_company_profile(_state):
        _state = build_initial_state()
    return _state


def reset_state() -> EducationDemoState:
    """現在の共通会社情報を前提に、教育デモ状態を初期化する。"""

    global _state
    _state = build_initial_state()
    return _state


def complete_all_trainings() -> None:
    """未受講の従業者をすべて受講済みにする（操作1）。"""

    state = get_state()
    for record in state.records:
        if not record.completed:
            record.completed = True


def register_missing_comprehension(
    result: ComprehensionResult = ComprehensionResult.PASSED,
) -> None:
    """理解度確認が未登録の受講済み記録に、簡易値を登録する（操作2）。"""

    state = get_state()
    for record in state.records:
        if record.completed and record.comprehension_result is None:
            record.comprehension_result = result


def register_material_evidence() -> None:
    """教材証跡を登録済みにする（操作3）。"""

    get_state().plan.material_evidence_registered = True


def approve_plan() -> None:
    """実施結果を承認済みにする（操作4）。"""

    get_state().plan.approved = True
