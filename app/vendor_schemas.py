"""委託先管理MVPで扱う最小データモデル。

事実データ（Vendor / VendorControl / VendorAssessment / VendorContractStatus）と、
評価結果（VendorIssue / VendorEvaluationResult）を分離して定義する。

事実データそのものには「不足」「問題あり」といった評価情報を持たせない。
評価情報は必ず評価結果側のモデルとして表現する。

教育管理のモデル（app.schemas）と設計思想は共通だが、対象領域（従業者×年次活動 と
外部事業者×初回評価・定期評価・契約確認）が異なるため、モデル自体は独立させている。
"""

from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel


class AssessmentFrequency(str, Enum):
    ANNUAL = "annual"


class AssessmentResult(str, Enum):
    """委託先評価の結果。

    VendorAssessment.assessment_result が None の場合は「未評価」を表し、
    ここに定義された結果が登録されている状態とは区別する。
    """

    PASSED = "passed"
    FAILED = "failed"


class Vendor(BaseModel):
    id: int
    name: str
    service_description: str
    handles_personal_data: bool
    active: bool


class VendorControl(BaseModel):
    """委託先管理策の実施ルール（事実データ）。

    「この管理策を採用したかどうか」の正式な判断はここでは持たない。
    採用可否の正本は setup 側の ControlSuggestion（control_id="vendor_management"）の
    status であり、ここには採用済みであることを前提とした実施ルール
    （初回評価・契約確認・定期評価の要否と頻度）のみを持つ。
    """

    id: int
    name: str
    initial_assessment_required: bool
    contract_check_required: bool
    periodic_assessment_required: bool
    assessment_frequency: AssessmentFrequency


class VendorAssessment(BaseModel):
    """委託先ごとの評価記録（事実データ）。

    初回評価と定期評価を同じ委託先に紐づく別の事実として保持する。
    既存MVPとの互換性のため initial_assessment_completed は残すが、
    画面からの新規登録では評価日・評価者・方法・結果・証跡も記録する。
    """

    vendor_id: int

    # 初回評価
    initial_assessment_completed: bool
    initial_assessment_date: date | None = None
    initial_assessment_result: AssessmentResult | None = None
    initial_assessment_by: str | None = None
    initial_assessment_method: str | None = None
    initial_assessment_evidence: str | None = None

    # 定期評価
    latest_assessment_date: date | None = None
    next_assessment_due: date | None = None
    assessment_result: AssessmentResult | None = None
    periodic_assessment_by: str | None = None
    periodic_assessment_method: str | None = None
    periodic_assessment_evidence: str | None = None


class VendorContractStatus(BaseModel):
    """委託先ごとの契約確認記録（事実データ）。"""

    vendor_id: int
    contract_confirmed: bool
    confirmed_on: date | None = None
    confirmed_by: str | None = None
    contract_reference: str | None = None


class VendorEvaluationStatus(str, Enum):
    COMPLIANT = "適合"
    NEEDS_ACTION = "要対応"


class VendorIssue(BaseModel):
    """評価によって検出された個々の不足事項。"""

    rule_id: str
    message: str
    vendor_ids: list[int] = []


class VendorEvaluationResult(BaseModel):
    """委託先管理策の評価結果。"""

    status: VendorEvaluationStatus
    target_vendor_ids: list[int]
    issues: list[VendorIssue] = []
