from app.access_control_schemas import (
    Account,
    AccessControl,
    AccessEvaluationStatus,
    AccessReviewCycle,
    AccountReviewStatus,
)
from app.access_control import evaluate_access_control


def make_control(**overrides):
    defaults = dict(id=1, name="アクセス権限管理", review_required=True, approval_required=True)
    defaults.update(overrides)
    return AccessControl(**defaults)


def make_cycle(**overrides):
    defaults = dict(id=1, control_id=1, review_completed=True, approved=True)
    defaults.update(overrides)
    return AccessReviewCycle(**defaults)


def make_account(account_id, **overrides):
    defaults = dict(
        id=account_id,
        user_name=f"利用者{account_id}",
        department="総務部",
        review_status=AccountReviewStatus.CONFIRMED,
        necessary=True,
        removed=False,
    )
    defaults.update(overrides)
    return Account(**defaults)


def test_fully_managed_accounts_are_compliant():
    accounts = [make_account(1), make_account(2)]

    result = evaluate_access_control(accounts, make_control(), make_cycle())

    assert result.status == AccessEvaluationStatus.COMPLIANT
    assert result.issues == []


def test_unconfirmed_account_triggers_acc001():
    accounts = [make_account(1, review_status=AccountReviewStatus.PENDING, necessary=None)]

    result = evaluate_access_control(accounts, make_control(), make_cycle())

    assert result.status == AccessEvaluationStatus.NEEDS_ACTION
    issue = next(i for i in result.issues if i.rule_id == "ACC-001")
    assert issue.account_ids == [1]


def test_unremoved_unnecessary_account_triggers_acc002():
    accounts = [make_account(1, necessary=False, removed=False)]

    result = evaluate_access_control(accounts, make_control(), make_cycle())

    assert result.status == AccessEvaluationStatus.NEEDS_ACTION
    issue = next(i for i in result.issues if i.rule_id == "ACC-002")
    assert issue.account_ids == [1]


def test_removed_unnecessary_account_does_not_trigger_acc002():
    accounts = [make_account(1, necessary=False, removed=True)]

    result = evaluate_access_control(accounts, make_control(), make_cycle())

    assert not any(i.rule_id == "ACC-002" for i in result.issues)


def test_missing_review_triggers_acc003():
    accounts = [make_account(1)]
    cycle = make_cycle(review_completed=False)

    result = evaluate_access_control(accounts, make_control(), cycle)

    assert result.status == AccessEvaluationStatus.NEEDS_ACTION
    assert any(i.rule_id == "ACC-003" for i in result.issues)


def test_missing_approval_triggers_acc004():
    accounts = [make_account(1)]
    cycle = make_cycle(approved=False)

    result = evaluate_access_control(accounts, make_control(), cycle)

    assert result.status == AccessEvaluationStatus.NEEDS_ACTION
    assert any(i.rule_id == "ACC-004" for i in result.issues)


def test_becomes_compliant_after_resolving_all_issues():
    accounts = [
        make_account(1, review_status=AccountReviewStatus.PENDING, necessary=None),
        make_account(2, necessary=False, removed=False),
    ]
    control = make_control()
    cycle = make_cycle(review_completed=False, approved=False)

    first_result = evaluate_access_control(accounts, control, cycle)
    assert first_result.status == AccessEvaluationStatus.NEEDS_ACTION
    rule_ids = {issue.rule_id for issue in first_result.issues}
    assert {"ACC-001", "ACC-002", "ACC-003", "ACC-004"} <= rule_ids

    fixed_accounts = [
        make_account(1, review_status=AccountReviewStatus.CONFIRMED, necessary=True),
        make_account(2, necessary=False, removed=True),
    ]
    fixed_cycle = make_cycle(review_completed=True, approved=True)

    second_result = evaluate_access_control(fixed_accounts, control, fixed_cycle)
    assert second_result.status == AccessEvaluationStatus.COMPLIANT
    assert second_result.issues == []
