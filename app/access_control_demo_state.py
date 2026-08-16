"""アクセス権限管理MVPのデモ用インメモリ状態。

サーバー起動時に固定のデモデータ（対象アカウント50件）を構築する。
ブラウザからの操作はこのモジュールが保持するインメモリ状態のみを変更し、
DBは使用しない。サーバー再起動で初期状態に戻る。

事実データ（Account / AccessReviewCycle 等）に評価情報は持たせない。
ここで行うのは事実データの登録・更新のみであり、適合／要対応の判定は
app.access_control.evaluate_access_control が行う。
"""

from __future__ import annotations

from dataclasses import dataclass

from app.access_control_schemas import (
    Account,
    AccessControl,
    AccessReviewCycle,
    AccountReviewStatus,
)

# アクセス権限管理に関する標準規程条項のプレビュー（今回のMVPでは全文書生成はしない）。
POLICY_CLAUSES = [
    "業務上必要な範囲でのみ、利用者アカウント・アクセス権限を付与する。",
    "退職・異動等によりアクセスが不要になった場合、速やかにアカウントを削除する。",
    "定期的に、付与されているアクセス権限が適切かどうかをレビューする。",
]

TARGET_ACCOUNT_COUNT = 50
UNCONFIRMED_COUNT = 2
UNNECESSARY_COUNT = 1


@dataclass
class AccessControlDemoState:
    accounts: list[Account]
    control: AccessControl
    cycle: AccessReviewCycle


def _build_accounts() -> list[Account]:
    """固定デモ状態を構築する（意図的に不足を残す）。

    対象50名のうち48名は確認済み（うち1名は不要と判明・未削除）、
    残り2名は未確認のままとする。
    """

    accounts: list[Account] = []
    confirmed_count = TARGET_ACCOUNT_COUNT - UNCONFIRMED_COUNT

    for index in range(1, TARGET_ACCOUNT_COUNT + 1):
        if index <= confirmed_count:
            is_unnecessary = index <= UNNECESSARY_COUNT
            accounts.append(
                Account(
                    id=index,
                    user_name=f"利用者{index:03d}",
                    department="営業部" if index % 2 == 0 else "総務部",
                    review_status=AccountReviewStatus.CONFIRMED,
                    necessary=not is_unnecessary,
                    removed=False,
                )
            )
        else:
            accounts.append(
                Account(
                    id=index,
                    user_name=f"利用者{index:03d}",
                    department="営業部" if index % 2 == 0 else "総務部",
                    review_status=AccountReviewStatus.PENDING,
                    necessary=None,
                    removed=False,
                )
            )

    return accounts


def build_initial_state() -> AccessControlDemoState:
    """デモの初期状態（意図的に不足を残した状態）を構築する。"""

    control = AccessControl(
        id=1,
        name="アクセス権限管理",
        review_required=True,
        approval_required=True,
    )
    cycle = AccessReviewCycle(
        id=1,
        control_id=1,
        review_completed=False,
        approved=False,
    )
    return AccessControlDemoState(
        accounts=_build_accounts(),
        control=control,
        cycle=cycle,
    )


_state: AccessControlDemoState = build_initial_state()


def get_state() -> AccessControlDemoState:
    """現在のデモ状態を取得する。"""

    return _state


def reset_state() -> AccessControlDemoState:
    """デモ状態を初期状態へ戻す。"""

    global _state
    _state = build_initial_state()
    return _state


def complete_missing_account_reviews(
    *,
    reviewed_on: str | None = None,
    reviewed_by: str | None = None,
    review_method: str | None = None,
    decisions: dict[int, bool] | None = None,
) -> None:
    """未確認アカウントの要否確認事実を登録する。

    decisions が省略された旧デモ操作は後方互換のため全件「必要」とする。
    通常UIでは未確認アカウントごとの要否判断を渡す。
    """

    default_date = reviewed_on or "2026-04-01"
    default_reviewer = (reviewed_by or "Pマーク担当者").strip()
    default_method = (review_method or "所属・在籍情報との照合").strip()

    for account in _state.accounts:
        if account.review_status != AccountReviewStatus.PENDING:
            continue
        if decisions is not None and account.id not in decisions:
            continue
        account.review_status = AccountReviewStatus.CONFIRMED
        account.necessary = decisions.get(account.id, True) if decisions is not None else True
        account.reviewed_on = default_date
        account.reviewed_by = default_reviewer
        account.review_method = default_method


def remove_unnecessary_accounts(
    *,
    removal_date: str | None = None,
    removed_by: str | None = None,
    removal_evidence: str | None = None,
) -> None:
    """不要と判定済みで未削除のアカウントについて削除記録を登録する。"""

    default_date = removal_date or "2026-04-02"
    default_operator = (removed_by or "システム管理担当者").strip()
    default_evidence = (removal_evidence or "アカウント削除記録").strip()

    for account in _state.accounts:
        if account.necessary is False and not account.removed:
            account.removed = True
            account.removal_date = default_date
            account.removed_by = default_operator
            account.removal_evidence = default_evidence


def complete_review_cycle(
    *,
    review_date: str | None = None,
    reviewer_name: str | None = None,
    review_method: str | None = None,
    review_evidence: str | None = None,
) -> None:
    """権限レビューの実施記録を登録する。"""

    _state.cycle.review_completed = True
    _state.cycle.review_date = review_date or "2026-04-03"
    _state.cycle.reviewer_name = (reviewer_name or "Pマーク担当者").strip()
    _state.cycle.review_method = (review_method or "権限一覧との照合").strip()
    _state.cycle.review_evidence = (review_evidence or "アクセス権限レビュー記録").strip()


def approve_review_cycle(
    *,
    approved_by: str | None = None,
    approved_at: str | None = None,
) -> None:
    """権限レビュー結果の承認記録を登録する。"""

    _state.cycle.approved = True
    _state.cycle.approved_by = (approved_by or "個人情報保護管理者").strip()
    _state.cycle.approved_at = approved_at or "2026-04-04"
