from app.paper import evaluate_paper_management
from app.paper_schemas import PaperControl, PaperEvaluationStatus, PaperMediaStatus


def make_control(**overrides):
    defaults = dict(
        id=1,
        name="紙媒体の保管・持出し・廃棄管理",
        lock_check_required=True,
        take_out_rule_required=True,
        disposal_check_required=True,
        approval_required=True,
    )
    defaults.update(overrides)
    return PaperControl(**defaults)


def make_status(**overrides):
    defaults = dict(
        id=1,
        control_id=1,
        handled_personal_information=["従業員人事ファイル（紙）"],
        storage_location="鍵付きキャビネット",
        storage_locked=True,
        take_out_rule="持出し台帳に記録する。",
        disposal_method="溶解処理",
        disposal_confirmed=True,
        approved=True,
    )
    defaults.update(overrides)
    return PaperMediaStatus(**defaults)


def test_fully_managed_status_is_compliant():
    result = evaluate_paper_management(make_control(), make_status())

    assert result.status == PaperEvaluationStatus.COMPLIANT
    assert result.issues == []


def test_unlocked_storage_triggers_pap001():
    status = make_status(storage_locked=False)

    result = evaluate_paper_management(make_control(), status)

    assert result.status == PaperEvaluationStatus.NEEDS_ACTION
    assert any(issue.rule_id == "PAP-001" for issue in result.issues)


def test_missing_take_out_rule_triggers_pap002():
    status = make_status(take_out_rule=None)

    result = evaluate_paper_management(make_control(), status)

    assert result.status == PaperEvaluationStatus.NEEDS_ACTION
    assert any(issue.rule_id == "PAP-002" for issue in result.issues)


def test_missing_disposal_confirmation_triggers_pap003():
    status = make_status(disposal_confirmed=False)

    result = evaluate_paper_management(make_control(), status)

    assert result.status == PaperEvaluationStatus.NEEDS_ACTION
    assert any(issue.rule_id == "PAP-003" for issue in result.issues)


def test_missing_approval_triggers_pap004():
    status = make_status(approved=False)

    result = evaluate_paper_management(make_control(), status)

    assert result.status == PaperEvaluationStatus.NEEDS_ACTION
    assert any(issue.rule_id == "PAP-004" for issue in result.issues)


def test_becomes_compliant_after_resolving_all_issues():
    control = make_control()
    status = make_status(
        storage_locked=False, take_out_rule=None, disposal_confirmed=False, approved=False
    )

    first_result = evaluate_paper_management(control, status)
    assert first_result.status == PaperEvaluationStatus.NEEDS_ACTION
    rule_ids = {issue.rule_id for issue in first_result.issues}
    assert {"PAP-001", "PAP-002", "PAP-003", "PAP-004"} <= rule_ids

    fixed_status = make_status()
    second_result = evaluate_paper_management(control, fixed_status)
    assert second_result.status == PaperEvaluationStatus.COMPLIANT
    assert second_result.issues == []
