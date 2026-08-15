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


def complete_missing_account_reviews() -> None:
    """未確認のアカウントを、すべて確認済み（必要）にする（操作1）。"""

    for account in _state.accounts:
        if account.review_status == AccountReviewStatus.PENDING:
            account.review_status = AccountReviewStatus.CONFIRMED
            account.necessary = True


def remove_unnecessary_accounts() -> None:
    """不要と判定済みで未削除のアカウントを、すべて削除済みにする（操作2）。"""

    for account in _state.accounts:
        if account.necessary is False and not account.removed:
            account.removed = True


def complete_review_cycle() -> None:
    """権限レビューを実施済みにする（操作3）。"""

    _state.cycle.review_completed = True


def approve_review_cycle() -> None:
    """実施結果を承認済みにする（操作4）。"""

    _state.cycle.approved = True
