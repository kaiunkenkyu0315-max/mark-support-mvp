"""紙媒体管理MVPのデモ用インメモリ状態。

サーバー起動時に固定のデモデータを構築する。ブラウザからの操作はこのモジュールが
保持するインメモリ状態のみを変更し、DBは使用しない。サーバー再起動で初期状態に戻る。

事実データ（PaperMediaStatus）に評価情報は持たせない。ここで行うのは事実データの
登録・更新のみであり、適合／要対応の判定は app.paper.evaluate_paper_management が行う。
"""

from __future__ import annotations

from dataclasses import dataclass

from app.paper_schemas import PaperControl, PaperMediaStatus

# 紙媒体管理に関する標準規程条項のプレビュー（今回のMVPでは全文書生成はしない）。
POLICY_CLAUSES = [
    "個人情報が記載された紙媒体は、施錠可能な場所に保管する。",
    "紙媒体を持ち出す場合は、あらかじめ定めたルールに従う。",
    "不要になった紙媒体は、復元できない方法で廃棄し、廃棄結果を確認する。",
]


@dataclass
class PaperDemoState:
    control: PaperControl
    status: PaperMediaStatus


def build_initial_state() -> PaperDemoState:
    """デモの初期状態（意図的に不足を残した状態）を構築する。

    保管場所・廃棄方法は登録済みだが、施錠管理・持出しルール・廃棄確認・承認が
    未対応のままとする。
    """

    control = PaperControl(
        id=1,
        name="紙媒体の保管・持出し・廃棄管理",
        lock_check_required=True,
        take_out_rule_required=True,
        disposal_check_required=True,
        approval_required=True,
    )
    status = PaperMediaStatus(
        id=1,
        control_id=1,
        handled_personal_information=["従業員人事ファイル（紙）", "顧客・取引先名簿（紙）"],
        storage_location="鍵付きキャビネット（総務部内）",
        storage_locked=False,
        take_out_rule=None,
        disposal_method="溶解処理業者による溶解処理",
        disposal_confirmed=False,
        approved=False,
    )
    return PaperDemoState(control=control, status=status)


_state: PaperDemoState = build_initial_state()


def get_state() -> PaperDemoState:
    """現在のデモ状態を取得する。"""

    return _state


def reset_state() -> PaperDemoState:
    """デモ状態を初期状態へ戻す。"""

    global _state
    _state = build_initial_state()
    return _state


def confirm_storage_lock() -> None:
    """保管場所の施錠管理を確認済みにする（操作1）。"""

    _state.status.storage_locked = True


def define_take_out_rule() -> None:
    """持出しルールを設定する（操作2）。"""

    _state.status.take_out_rule = "持出し台帳に記録のうえ、責任者の許可を得て持ち出す。"


def confirm_disposal() -> None:
    """廃棄確認を実施済みにする（操作3）。"""

    _state.status.disposal_confirmed = True


def approve_status() -> None:
    """実施結果を承認済みにする（操作4）。"""

    _state.status.approved = True
