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
    """委託先管理策そのものの設定内容（事実データ）。"""

    id: int
    name: str
    adopted: bool
    initial_assessment_required: bool
    contract_check_required: bool
    periodic_assessment_required: bool
    assessment_frequency: AssessmentFrequency


class VendorAssessment(BaseModel):
    """委託先ごとの評価状況（事実データ）。

    latest_assessment_date が None の場合は「評価未実施」であり、
    「実施済みだが不合格」という状態とは区別する。
    """

    vendor_id: int
    initial_assessment_completed: bool
    latest_assessment_date: date | None = None
    next_assessment_due: date | None = None
    assessment_result: AssessmentResult | None = None


class VendorContractStatus(BaseModel):
    """委託先ごとの契約確認状況（事実データ）。"""

    vendor_id: int
    contract_confirmed: bool


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
