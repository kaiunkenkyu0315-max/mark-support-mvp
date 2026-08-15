"""アクセス権限管理の整合性判定ロジック。

事実データ（Account / AccessControl / AccessReviewCycle）に業務ルールを適用し、
評価結果（AccessEvaluationResult）を導出する。FastAPIやHTTP処理には依存しない、
純粋な業務ロジックとして実装する。UI側では判定を行わない。
"""

from __future__ import annotations

from app.access_control_schemas import (
    Account,
    AccessControl,
    AccessEvaluationResult,
    AccessEvaluationStatus,
    AccessIssue,
    AccessReviewCycle,
    AccountReviewStatus,
)


def evaluate_access_control(
    accounts: list[Account],
    control: AccessControl,
    cycle: AccessReviewCycle,
) -> AccessEvaluationResult:
    """アクセス権限管理策に対する実施状況を評価する。

    現在の管理対象は、登録されているアカウントすべてとする。
    """

    target_ids = [account.id for account in accounts]

    issues: list[AccessIssue] = []

    # ACC-001: 対象者に対するアカウント確認不足
    # 要否確認（棚卸し）がまだ済んでいない（pending）アカウントを不足とする。
    unconfirmed_ids = [
        account.id for account in accounts if account.review_status == AccountReviewStatus.PENDING
    ]
    if unconfirmed_ids:
        issues.append(
            AccessIssue(
                rule_id="ACC-001",
                message=f"アカウント確認が未実施の対象者が{len(unconfirmed_ids)}名います。",
                account_ids=unconfirmed_ids,
            )
        )

    # ACC-002: 不要アカウントが残存
    # 確認済みで「不要」と判定されたにもかかわらず、まだ削除されていないアカウントを不足とする。
    unnecessary_ids = [
        account.id for account in accounts if account.necessary is False and not account.removed
    ]
    if unnecessary_ids:
        issues.append(
            AccessIssue(
                rule_id="ACC-002",
                message=f"削除されていない不要アカウントが{len(unnecessary_ids)}件あります。",
                account_ids=unnecessary_ids,
            )
        )

    # ACC-003: 権限レビュー未実施
    if control.review_required and not cycle.review_completed:
        issues.append(
            AccessIssue(
                rule_id="ACC-003",
                message="権限レビューが未実施です。",
            )
        )

    # ACC-004: 実施結果未承認
    if control.approval_required and not cycle.approved:
        issues.append(
            AccessIssue(
                rule_id="ACC-004",
                message="実施結果が未承認です。",
            )
        )

    status = (
        AccessEvaluationStatus.NEEDS_ACTION if issues else AccessEvaluationStatus.COMPLIANT
    )

    return AccessEvaluationResult(
        status=status,
        target_account_ids=target_ids,
        issues=issues,
    )
