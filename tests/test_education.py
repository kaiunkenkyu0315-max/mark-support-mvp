from app.education import evaluate_training
from app.schemas import (
    ComprehensionResult,
    EducationEvaluationStatus,
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


def make_control(**overrides):
    defaults = dict(
        id=1,
        name="年次教育",
        adopted=True,
        frequency=TrainingFrequency.ANNUAL,
        target_roles=ALL_ROLES,
        comprehension_required=True,
        material_evidence_required=True,
        approval_required=True,
    )
    defaults.update(overrides)
    return TrainingControl(**defaults)


def make_plan(**overrides):
    defaults = dict(
        id=1,
        title="2026年度教育",
        fiscal_year=2026,
        control_id=1,
        material_evidence_registered=True,
        approved=True,
    )
    defaults.update(overrides)
    return TrainingPlan(**defaults)


def make_employees(count, role=EmployeeRole.GENERAL_EMPLOYEE, status=EmployeeStatus.ACTIVE):
    return [
        Employee(id=i, name=f"従業員{i}", role=role, status=status) for i in range(1, count + 1)
    ]


def make_completed_records(employee_ids, comprehension_result=ComprehensionResult.PASSED):
    return [
        TrainingRecord(
            employee_id=employee_id,
            completed=True,
            comprehension_result=comprehension_result,
        )
        for employee_id in employee_ids
    ]


def test_case1_all_completed_is_compliant():
    employees = make_employees(50)
    records = make_completed_records([e.id for e in employees])
    control = make_control()
    plan = make_plan()

    result = evaluate_training(employees, control, plan, records)

    assert result.status == EducationEvaluationStatus.COMPLIANT
    assert result.issues == []


def test_case2_two_of_fifty_not_completed():
    employees = make_employees(50)
    completed_ids = [e.id for e in employees[:48]]
    not_completed_ids = [e.id for e in employees[48:]]
    records = make_completed_records(completed_ids)
    control = make_control()
    plan = make_plan()

    result = evaluate_training(employees, control, plan, records)

    assert result.status == EducationEvaluationStatus.NEEDS_ACTION
    edu003 = next(issue for issue in result.issues if issue.rule_id == "EDU-003")
    assert len(edu003.employee_ids) == 2
    assert set(edu003.employee_ids) == set(not_completed_ids)


def test_case3_comprehension_missing():
    employees = make_employees(3)
    records = [
        TrainingRecord(
            employee_id=1, completed=True, comprehension_result=ComprehensionResult.PASSED
        ),
        TrainingRecord(employee_id=2, completed=True, comprehension_result=None),
        TrainingRecord(
            employee_id=3, completed=True, comprehension_result=ComprehensionResult.PASSED
        ),
    ]
    control = make_control()
    plan = make_plan()

    result = evaluate_training(employees, control, plan, records)

    assert result.status == EducationEvaluationStatus.NEEDS_ACTION
    edu006 = next(issue for issue in result.issues if issue.rule_id == "EDU-006")
    assert edu006.employee_ids == [2]


def test_case4_material_evidence_missing():
    employees = make_employees(3)
    records = make_completed_records([e.id for e in employees])
    control = make_control()
    plan = make_plan(material_evidence_registered=False)

    result = evaluate_training(employees, control, plan, records)

    assert result.status == EducationEvaluationStatus.NEEDS_ACTION
    assert any(issue.rule_id == "EDU-008" for issue in result.issues)


def test_case5_not_approved():
    employees = make_employees(3)
    records = make_completed_records([e.id for e in employees])
    control = make_control()
    plan = make_plan(approved=False)

    result = evaluate_training(employees, control, plan, records)

    assert result.status == EducationEvaluationStatus.NEEDS_ACTION
    assert any(issue.rule_id == "EDU-009" for issue in result.issues)


def test_case6_inactive_employee_is_excluded():
    active_employee = Employee(
        id=1, name="在籍者", role=EmployeeRole.GENERAL_EMPLOYEE, status=EmployeeStatus.ACTIVE
    )
    inactive_employee = Employee(
        id=2, name="退職者", role=EmployeeRole.GENERAL_EMPLOYEE, status=EmployeeStatus.INACTIVE
    )
    employees = [active_employee, inactive_employee]
    # inactive_employee には受講記録がない。
    records = make_completed_records([1])
    control = make_control()
    plan = make_plan()

    result = evaluate_training(employees, control, plan, records)

    assert result.status == EducationEvaluationStatus.COMPLIANT
    assert 2 not in result.target_employee_ids


def test_case7_role_not_in_target_roles_is_excluded():
    target_employee = Employee(
        id=1, name="対象者", role=EmployeeRole.GENERAL_EMPLOYEE, status=EmployeeStatus.ACTIVE
    )
    out_of_scope_employee = Employee(
        id=2, name="対象外", role=EmployeeRole.EXECUTIVE, status=EmployeeStatus.ACTIVE
    )
    employees = [target_employee, out_of_scope_employee]
    # out_of_scope_employee には受講記録がない。
    records = make_completed_records([1])
    control = make_control(target_roles=[EmployeeRole.GENERAL_EMPLOYEE])
    plan = make_plan()

    result = evaluate_training(employees, control, plan, records)

    assert result.status == EducationEvaluationStatus.COMPLIANT
    assert 2 not in result.target_employee_ids


def test_case8_becomes_compliant_after_resolving_all_issues():
    employees = make_employees(2)
    records = [
        TrainingRecord(employee_id=1, completed=False, comprehension_result=None),
        TrainingRecord(employee_id=2, completed=True, comprehension_result=None),
    ]
    control = make_control()
    plan = make_plan(material_evidence_registered=False, approved=False)

    first_result = evaluate_training(employees, control, plan, records)

    assert first_result.status == EducationEvaluationStatus.NEEDS_ACTION
    rule_ids = {issue.rule_id for issue in first_result.issues}
    assert rule_ids == {"EDU-003", "EDU-006", "EDU-008", "EDU-009"}

    fixed_records = [
        TrainingRecord(
            employee_id=1, completed=True, comprehension_result=ComprehensionResult.PASSED
        ),
        TrainingRecord(
            employee_id=2, completed=True, comprehension_result=ComprehensionResult.PASSED
        ),
    ]
    fixed_plan = make_plan(material_evidence_registered=True, approved=True)

    second_result = evaluate_training(employees, control, fixed_plan, fixed_records)

    assert second_result.status == EducationEvaluationStatus.COMPLIANT
    assert second_result.issues == []
