"""紙媒体管理MVPのデモ用インメモリ状態。

サーバー起動時に固定のデモデータを構築する。ブラウザからの操作はこのモジュールが
保持するインメモリ状態のみを変更し、DBは使用しない。サーバー再起動で初期状態に戻る。

事実データ（PaperMediaStatus）に評価情報は持たせない。ここで行うのは事実データの
登録・更新のみであり、適合／要対応の判定は app.paper.evaluate_paper_management が行う。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

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
    """デモの初期状態（意図的に不足を残した状態）を構築する。"""

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
    return _state


def reset_state() -> PaperDemoState:
    global _state
    _state = build_initial_state()
    return _state


def confirm_storage_lock(
    *,
    locked: bool = True,
    checked_on: str | None = None,
    checked_by: str | None = None,
    check_method: str | None = None,
    evidence: str | None = None,
    storage_location: str | None = None,
) -> None:
    """施錠管理の確認結果と説明可能な記録を保存する。"""

    status = _state.status
    status.storage_locked = locked
    if storage_location is not None:
        status.storage_location = storage_location.strip() or status.storage_location
    status.storage_lock_checked_on = checked_on or date.today().isoformat()
    status.storage_lock_checked_by = (checked_by or "Pマーク担当者").strip()
    status.storage_lock_check_method = (check_method or "現地確認").strip()
    status.storage_lock_evidence = (evidence or "保管場所施錠確認記録").strip()


def define_take_out_rule(
    *,
    rule: str | None = None,
    defined_on: str | None = None,
    defined_by: str | None = None,
) -> None:
    """紙媒体の持出しルールと設定記録を保存する。"""

    status = _state.status
    status.take_out_rule = (
        rule or "持出し台帳に記録のうえ、責任者の許可を得て持ち出す。"
    ).strip()
    status.take_out_rule_defined_on = defined_on or date.today().isoformat()
    status.take_out_rule_defined_by = (defined_by or "Pマーク担当者").strip()


def confirm_disposal(
    *,
    confirmed: bool = True,
    confirmed_on: str | None = None,
    confirmed_by: str | None = None,
    evidence: str | None = None,
    disposal_method: str | None = None,
) -> None:
    """廃棄方法の確認結果と証跡情報を保存する。"""

    status = _state.status
    status.disposal_confirmed = confirmed
    if disposal_method is not None:
        status.disposal_method = disposal_method.strip() or status.disposal_method
    status.disposal_confirmed_on = confirmed_on or date.today().isoformat()
    status.disposal_confirmed_by = (confirmed_by or "Pマーク担当者").strip()
    status.disposal_evidence = (evidence or "紙媒体廃棄確認記録").strip()


def approve_status(
    *, approved_by: str | None = None, approved_at: str | None = None
) -> None:
    """紙媒体管理の実施結果について承認事実を保存する。"""

    _state.status.approved = True
    _state.status.approved_by = (approved_by or "個人情報保護管理者").strip()
    _state.status.approved_at = approved_at or date.today().isoformat()
