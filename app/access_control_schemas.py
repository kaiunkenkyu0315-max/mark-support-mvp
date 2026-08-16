"""アクセス権限管理MVPで扱う最小データモデル。

事実データ（Account / AccessControl / AccessReviewCycle）と、評価結果
（AccessIssue / AccessEvaluationResult）を分離して定義する。事実データそのものには
「不足」「問題あり」といった評価情報を持たせない。評価情報は必ず評価結果側の
モデルとして表現する。

教育管理・委託先管理のモデル（app.schemas / app.vendor_schemas）と設計思想は共通。
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class AccountReviewStatus(str, Enum):
    """個々のアカウントについて、要否確認（棚卸し）が済んでいるかどうか。"""

    PENDING = "pending"
    CONFIRMED = "confirmed"


class Account(BaseModel):
    """管理対象アカウント（事実データ）。

    review_status が PENDING の間は、まだ要否を確認していないことを表し、
    necessary（要否の確認結果）は None のままとする。CONFIRMED になって初めて
    necessary が True／False を持つ。
    """

    id: int
    user_name: str
    department: str
    review_status: AccountReviewStatus = AccountReviewStatus.PENDING
    necessary: bool | None = None
    """確認済み（CONFIRMED）の場合のみ意味を持つ。Trueなら要（在職・利用中）、
    Falseなら不要（退職・異動等でアクセス不要）。"""
    removed: bool = False
    """necessary=Falseの不要アカウントについて、実際に削除が完了しているか。"""

    # 棚卸し・削除を後から説明するための記録。
    reviewed_on: str | None = None
    reviewed_by: str | None = None
    review_method: str | None = None
    removal_date: str | None = None
    removed_by: str | None = None
    removal_evidence: str | None = None


class AccessControl(BaseModel):
    """アクセス権限管理策の実施ルール（事実データ）。

    「この管理策を採用したかどうか」の正式な判断はここでは持たない。
    採用可否の正本は setup 側の ControlSuggestion（control_id="access_control"）の
    status であり、ここには採用済みであることを前提とした実施ルール
    （権限レビュー・承認の要否）のみを持つ。
    """

    id: int
    name: str
    review_required: bool = True
    approval_required: bool = True


class AccessReviewCycle(BaseModel):
    """直近の権限レビュー実施状況（事実データ）。

    アカウントごとの要否確認（Account.review_status）とは別に、権限の割り当てが
    適切かをまとめて確認する「権限レビュー」自体を実施したかどうかを表す。
    """

    id: int
    control_id: int
    review_completed: bool
    approved: bool

    review_date: str | None = None
    reviewer_name: str | None = None
    review_method: str | None = None
    review_evidence: str | None = None
    approved_by: str | None = None
    approved_at: str | None = None


class AccessEvaluationStatus(str, Enum):
    COMPLIANT = "適合"
    NEEDS_ACTION = "要対応"


class AccessIssue(BaseModel):
    """評価によって検出された個々の不足事項。"""

    rule_id: str
    message: str
    account_ids: list[int] = []


class AccessEvaluationResult(BaseModel):
    """アクセス権限管理策の評価結果。"""

    status: AccessEvaluationStatus
    target_account_ids: list[int]
    issues: list[AccessIssue] = []
