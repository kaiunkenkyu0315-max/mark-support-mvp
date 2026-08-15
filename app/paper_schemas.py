"""紙媒体管理MVPで扱う最小データモデル。

事実データ（PaperControl / PaperMediaStatus）と、評価結果（PaperIssue /
PaperEvaluationResult）を分離して定義する。事実データそのものには「不足」
「問題あり」といった評価情報を持たせない。評価情報は必ず評価結果側の
モデルとして表現する。

委託先管理・教育管理のモデルと異なり、対象は「個々の委託先・従業者」ではなく
「紙媒体の保管・持出し・廃棄」という一つの業務プロセスであるため、
対象一覧（複数件）ではなく単一の実施状況として表現する。
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class PaperControl(BaseModel):
    """紙媒体管理策の実施ルール（事実データ）。

    「この管理策を採用したかどうか」の正式な判断はここでは持たない。
    採用可否の正本は setup 側の ControlSuggestion（control_id="paper_management"）の
    status であり、ここには採用済みであることを前提とした実施ルール
    （施錠管理・持出しルール・廃棄確認・承認の要否）のみを持つ。
    """

    id: int
    name: str
    lock_check_required: bool = True
    take_out_rule_required: bool = True
    disposal_check_required: bool = True
    approval_required: bool = True


class PaperMediaStatus(BaseModel):
    """紙媒体の保管・持出し・廃棄の実施状況（事実データ）。

    storage_location・disposal_method が None（空）の場合は「未登録」を表す。
    storage_locked・disposal_confirmed・approved は、確認・実施済みかどうかを表す
    bool（実施ルールとしての要否は PaperControl 側が持つ）。
    """

    id: int
    control_id: int
    handled_personal_information: list[str] = []
    """紙媒体で取り扱っている個人情報の名称一覧（表示用の事実データ）。"""
    storage_location: str | None = None
    storage_locked: bool = False
    take_out_rule: str | None = None
    disposal_method: str | None = None
    disposal_confirmed: bool = False
    approved: bool = False


class PaperEvaluationStatus(str, Enum):
    COMPLIANT = "適合"
    NEEDS_ACTION = "要対応"


class PaperIssue(BaseModel):
    """評価によって検出された個々の不足事項。"""

    rule_id: str
    message: str


class PaperEvaluationResult(BaseModel):
    """紙媒体管理策の評価結果。"""

    status: PaperEvaluationStatus
    issues: list[PaperIssue] = []
