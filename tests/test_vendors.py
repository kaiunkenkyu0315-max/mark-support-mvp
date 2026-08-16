from datetime import date, timedelta

from app.vendor_schemas import (
    AssessmentFrequency,
    AssessmentResult,
    Vendor,
    VendorAssessment,
    VendorContractStatus,
    VendorControl,
    VendorEvaluationStatus,
)
from app.vendors import evaluate_vendors

TODAY = date(2026, 1, 1)


def make_control(**overrides):
    defaults = dict(
        id=1,
        name="委託先管理",
        initial_assessment_required=True,
        contract_check_required=True,
        periodic_assessment_required=True,
        assessment_frequency=AssessmentFrequency.ANNUAL,
    )
    defaults.update(overrides)
    return VendorControl(**defaults)


def make_vendor(vendor_id, handles_personal_data=True, active=True, name=None):
    return Vendor(
        id=vendor_id,
        name=name or f"委託先{vendor_id}",
        service_description="サービス",
        handles_personal_data=handles_personal_data,
        active=active,
    )


def make_valid_assessment(vendor_id, today=TODAY):
    return VendorAssessment(
        vendor_id=vendor_id,
        initial_assessment_completed=True,
        latest_assessment_date=today - timedelta(days=10),
        next_assessment_due=today + timedelta(days=300),
        assessment_result=AssessmentResult.PASSED,
    )


def make_contract(vendor_id, confirmed=True):
    return VendorContractStatus(vendor_id=vendor_id, contract_confirmed=confirmed)


def test_case1_fully_managed_vendor_is_compliant():
    vendors = [make_vendor(1)]
    assessments = [make_valid_assessment(1)]
    contracts = [make_contract(1, confirmed=True)]
    control = make_control()

    result = evaluate_vendors(vendors, control, assessments, contracts, today=TODAY)

    assert result.status == VendorEvaluationStatus.COMPLIANT
    assert result.issues == []


def test_case2_missing_initial_assessment_triggers_ven001():
    vendors = [make_vendor(1)]
    assessments = [VendorAssessment(vendor_id=1, initial_assessment_completed=False)]
    contracts = [make_contract(1, confirmed=True)]
    control = make_control()

    result = evaluate_vendors(vendors, control, assessments, contracts, today=TODAY)

    assert result.status == VendorEvaluationStatus.NEEDS_ACTION
    issue = next(i for i in result.issues if i.rule_id == "VEN-001")
    assert issue.vendor_ids == [1]


def test_case3_missing_contract_confirmation_triggers_ven002():
    vendors = [make_vendor(1)]
    assessments = [make_valid_assessment(1)]
    contracts = [make_contract(1, confirmed=False)]
    control = make_control()

    result = evaluate_vendors(vendors, control, assessments, contracts, today=TODAY)

    assert result.status == VendorEvaluationStatus.NEEDS_ACTION
    issue = next(i for i in result.issues if i.rule_id == "VEN-002")
    assert issue.vendor_ids == [1]


def test_case4_missing_periodic_assessment_triggers_ven004():
    vendors = [make_vendor(1)]
    assessments = [
        VendorAssessment(
            vendor_id=1,
            initial_assessment_completed=True,
            latest_assessment_date=None,
            next_assessment_due=None,
            assessment_result=None,
        )
    ]
    contracts = [make_contract(1, confirmed=True)]
    control = make_control()

    result = evaluate_vendors(vendors, control, assessments, contracts, today=TODAY)

    assert result.status == VendorEvaluationStatus.NEEDS_ACTION
    issue = next(i for i in result.issues if i.rule_id == "VEN-004")
    assert issue.vendor_ids == [1]
    assert not any(i.rule_id == "VEN-001" for i in result.issues)


def test_case5_overdue_next_assessment_triggers_ven006():
    vendors = [make_vendor(1)]
    assessments = [
        VendorAssessment(
            vendor_id=1,
            initial_assessment_completed=True,
            latest_assessment_date=TODAY - timedelta(days=400),
            next_assessment_due=TODAY - timedelta(days=10),
            assessment_result=AssessmentResult.PASSED,
        )
    ]
    contracts = [make_contract(1, confirmed=True)]
    control = make_control()

    result = evaluate_vendors(vendors, control, assessments, contracts, today=TODAY)

    assert result.status == VendorEvaluationStatus.NEEDS_ACTION
    issue = next(i for i in result.issues if i.rule_id == "VEN-006")
    assert issue.vendor_ids == [1]
    assert not any(i.rule_id == "VEN-004" for i in result.issues)


def test_case6_vendor_without_personal_data_is_excluded():
    vendors = [make_vendor(1, handles_personal_data=False)]
    assessments = [VendorAssessment(vendor_id=1, initial_assessment_completed=False)]
    contracts = [make_contract(1, confirmed=False)]
    control = make_control()

    result = evaluate_vendors(vendors, control, assessments, contracts, today=TODAY)

    assert result.status == VendorEvaluationStatus.COMPLIANT
    assert 1 not in result.target_vendor_ids


def test_case7_inactive_vendor_is_excluded():
    vendors = [make_vendor(1, active=False)]
    assessments = [VendorAssessment(vendor_id=1, initial_assessment_completed=False)]
    contracts = [make_contract(1, confirmed=False)]
    control = make_control()

    result = evaluate_vendors(vendors, control, assessments, contracts, today=TODAY)

    assert result.status == VendorEvaluationStatus.COMPLIANT
    assert 1 not in result.target_vendor_ids


def test_case8_becomes_compliant_after_resolving_all_issues():
    vendors = [make_vendor(1)]
    assessments = [VendorAssessment(vendor_id=1, initial_assessment_completed=False)]
    contracts = [make_contract(1, confirmed=False)]
    control = make_control()

    first_result = evaluate_vendors(vendors, control, assessments, contracts, today=TODAY)

    assert first_result.status == VendorEvaluationStatus.NEEDS_ACTION
    rule_ids = {issue.rule_id for issue in first_result.issues}
    assert {"VEN-001", "VEN-002", "VEN-004"} <= rule_ids

    fixed_assessments = [make_valid_assessment(1)]
    fixed_contracts = [make_contract(1, confirmed=True)]

    second_result = evaluate_vendors(vendors, control, fixed_assessments, fixed_contracts, today=TODAY)

    assert second_result.status == VendorEvaluationStatus.COMPLIANT
    assert second_result.issues == []


def test_failed_initial_assessment_triggers_ven003():
    vendors = [make_vendor(1)]
    assessments = [
        VendorAssessment(
            vendor_id=1,
            initial_assessment_completed=True,
            initial_assessment_date=TODAY,
            initial_assessment_result=AssessmentResult.FAILED,
            latest_assessment_date=TODAY - timedelta(days=10),
            next_assessment_due=TODAY + timedelta(days=300),
            assessment_result=AssessmentResult.PASSED,
        )
    ]
    contracts = [make_contract(1, confirmed=True)]
    control = make_control()

    result = evaluate_vendors(vendors, control, assessments, contracts, today=TODAY)

    assert result.status == VendorEvaluationStatus.NEEDS_ACTION
    issue = next(i for i in result.issues if i.rule_id == "VEN-003")
    assert issue.vendor_ids == [1]
    assert not any(i.rule_id == "VEN-001" for i in result.issues)
