"""委託先管理MVPのデモ用インメモリ状態。

サーバー起動時に固定のデモデータ（委託先3社）を構築する。
ブラウザからの操作はこのモジュールが保持するインメモリ状態のみを変更し、
DBは使用しない。サーバー再起動で初期状態に戻る。

事実データ（Vendor / VendorAssessment 等）に評価情報は持たせない。
ここで行うのは事実データの登録・更新のみであり、適合／要対応の判定は
app.vendors.evaluate_vendors が行う。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from app.vendor_schemas import (
    AssessmentFrequency,
    AssessmentResult,
    Vendor,
    VendorAssessment,
    VendorContractStatus,
    VendorControl,
)

# 委託先管理に関する標準規程条項のプレビュー（今回のMVPでは全文書生成はしない）。
POLICY_CLAUSES = [
    "個人情報を取り扱う業務を委託する場合、委託先の適格性を確認する。",
    "委託先との契約等に必要な個人情報保護上の事項を定める。",
    "委託期間中、必要に応じて委託先の取扱状況を確認する。",
]

VENDOR_SALARY = 1
VENDOR_RECRUITING = 2
VENDOR_DISPOSAL = 3

# 定期評価を実施済みとする際、次回評価期限を何日後に設定するか（年1回想定）。
_NEXT_ASSESSMENT_INTERVAL_DAYS = 365


@dataclass
class VendorDemoState:
    vendors: list[Vendor]
    control: VendorControl
    assessments: list[VendorAssessment]
    contracts: list[VendorContractStatus]


def _build_vendors() -> list[Vendor]:
    return [
        Vendor(
            id=VENDOR_SALARY,
            name="給与計算会社",
            service_description="給与計算",
            handles_personal_data=True,
            active=True,
        ),
        Vendor(
            id=VENDOR_RECRUITING,
            name="採用管理クラウド",
            service_description="採用管理",
            handles_personal_data=True,
            active=True,
        ),
        Vendor(
            id=VENDOR_DISPOSAL,
            name="機密文書廃棄会社",
            service_description="機密文書廃棄",
            handles_personal_data=True,
            active=True,
        ),
    ]


def _build_assessments(today: date) -> list[VendorAssessment]:
    valid_last = today - timedelta(days=90)
    valid_next = today + timedelta(days=275)
    initial_date = today - timedelta(days=400)
    return [
        # 給与計算会社：初回評価済み、定期評価も有効。
        VendorAssessment(
            vendor_id=VENDOR_SALARY,
            initial_assessment_completed=True,
            initial_assessment_date=initial_date,
            initial_assessment_result=AssessmentResult.PASSED,
            initial_assessment_by="Pマーク担当者",
            initial_assessment_method="チェックリスト",
            initial_assessment_evidence="委託先初回評価票",
            latest_assessment_date=valid_last,
            next_assessment_due=valid_next,
            assessment_result=AssessmentResult.PASSED,
            periodic_assessment_by="Pマーク担当者",
            periodic_assessment_method="チェックリスト",
            periodic_assessment_evidence="委託先定期評価票",
        ),
        # 採用管理クラウド：初回評価済み、定期評価も有効（契約確認のみ未完了）。
        VendorAssessment(
            vendor_id=VENDOR_RECRUITING,
            initial_assessment_completed=True,
            initial_assessment_date=initial_date,
            initial_assessment_result=AssessmentResult.PASSED,
            initial_assessment_by="Pマーク担当者",
            initial_assessment_method="チェックリスト",
            initial_assessment_evidence="委託先初回評価票",
            latest_assessment_date=valid_last,
            next_assessment_due=valid_next,
            assessment_result=AssessmentResult.PASSED,
            periodic_assessment_by="Pマーク担当者",
            periodic_assessment_method="チェックリスト",
            periodic_assessment_evidence="委託先定期評価票",
        ),
        # 機密文書廃棄会社：初回評価未実施、定期評価も未設定・未評価。
        VendorAssessment(
            vendor_id=VENDOR_DISPOSAL,
            initial_assessment_completed=False,
            latest_assessment_date=None,
            next_assessment_due=None,
            assessment_result=None,
        ),
    ]


def _build_contracts(today: date) -> list[VendorContractStatus]:
    confirmed_on = today - timedelta(days=390)
    return [
        VendorContractStatus(
            vendor_id=VENDOR_SALARY,
            contract_confirmed=True,
            confirmed_on=confirmed_on,
            confirmed_by="Pマーク担当者",
            contract_reference="業務委託契約書",
        ),
        VendorContractStatus(vendor_id=VENDOR_RECRUITING, contract_confirmed=False),
        VendorContractStatus(
            vendor_id=VENDOR_DISPOSAL,
            contract_confirmed=True,
            confirmed_on=confirmed_on,
            confirmed_by="Pマーク担当者",
            contract_reference="業務委託契約書",
        ),
    ]


def build_initial_state() -> VendorDemoState:
    """デモの初期状態（意図的に不足を残した状態）を構築する。"""

    today = date.today()
    control = VendorControl(
        id=1,
        name="委託先管理",
        initial_assessment_required=True,
        contract_check_required=True,
        periodic_assessment_required=True,
        assessment_frequency=AssessmentFrequency.ANNUAL,
    )
    return VendorDemoState(
        vendors=_build_vendors(),
        control=control,
        assessments=_build_assessments(today),
        contracts=_build_contracts(today),
    )


_state: VendorDemoState = build_initial_state()


def get_state() -> VendorDemoState:
    """現在のデモ状態を取得する。"""

    return _state


def reset_state() -> VendorDemoState:
    """デモ状態を初期状態へ戻す。"""

    global _state
    _state = build_initial_state()
    return _state


def _parse_date(value: str | date | None, fallback: date) -> date:
    if isinstance(value, date):
        return value
    text = (value or "").strip()
    if not text:
        return fallback
    return date.fromisoformat(text)


def complete_missing_initial_assessments(
    assessment_date: str | date | None = None,
    assessor_name: str | None = None,
    assessment_method: str | None = None,
    evidence_name: str | None = None,
    result: AssessmentResult = AssessmentResult.PASSED,
) -> None:
    """不足・不適格の初回評価について、説明可能な評価記録を登録する。"""

    recorded_on = _parse_date(assessment_date, date.today())
    assessor = (assessor_name or "").strip() or "Pマーク担当者"
    method = (assessment_method or "").strip() or "チェックリスト"
    evidence = (evidence_name or "").strip() or "委託先初回評価票"

    for assessment in _state.assessments:
        if (
            not assessment.initial_assessment_completed
            or assessment.initial_assessment_result == AssessmentResult.FAILED
        ):
            assessment.initial_assessment_completed = True
            assessment.initial_assessment_date = recorded_on
            assessment.initial_assessment_result = result
            assessment.initial_assessment_by = assessor
            assessment.initial_assessment_method = method
            assessment.initial_assessment_evidence = evidence


def confirm_missing_contracts(
    confirmed_on: str | date | None = None,
    confirmed_by: str | None = None,
    contract_reference: str | None = None,
) -> None:
    """未確認の契約について、確認日・確認者・資料名を伴う確認記録を登録する。"""

    recorded_on = _parse_date(confirmed_on, date.today())
    confirmer = (confirmed_by or "").strip() or "Pマーク担当者"
    reference = (contract_reference or "").strip() or "業務委託契約書"

    for contract in _state.contracts:
        if not contract.contract_confirmed:
            contract.contract_confirmed = True
            contract.confirmed_on = recorded_on
            contract.confirmed_by = confirmer
            contract.contract_reference = reference


def complete_missing_periodic_assessments(
    assessment_date: str | date | None = None,
    assessor_name: str | None = None,
    assessment_method: str | None = None,
    evidence_name: str | None = None,
    result: AssessmentResult = AssessmentResult.PASSED,
) -> None:
    """不足・期限超過の定期評価について、説明可能な評価記録を登録する。"""

    recorded_on = _parse_date(assessment_date, date.today())
    next_due = recorded_on + timedelta(days=_NEXT_ASSESSMENT_INTERVAL_DAYS)
    assessor = (assessor_name or "").strip() or "Pマーク担当者"
    method = (assessment_method or "").strip() or "チェックリスト"
    evidence = (evidence_name or "").strip() or "委託先定期評価票"

    for assessment in _state.assessments:
        is_invalid = (
            assessment.latest_assessment_date is None
            or assessment.assessment_result != AssessmentResult.PASSED
        )
        is_overdue = (
            assessment.next_assessment_due is not None
            and assessment.next_assessment_due < date.today()
        )
        if is_invalid or is_overdue:
            assessment.latest_assessment_date = recorded_on
            assessment.next_assessment_due = (
                next_due if result == AssessmentResult.PASSED else None
            )
            assessment.assessment_result = result
            assessment.periodic_assessment_by = assessor
            assessment.periodic_assessment_method = method
            assessment.periodic_assessment_evidence = evidence
