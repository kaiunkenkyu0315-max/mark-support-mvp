"""教育管理MVPで扱う最小データモデル。

事実データ（Company / Employee / TrainingControl / TrainingPlan / TrainingRecord）と、
評価結果（EducationIssue / EducationEvaluationResult）を分離して定義する。

事実データそのものには「不足」「問題あり」といった評価情報を持たせない。
評価情報は必ず評価結果側のモデルとして表現する。
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class EmployeeRole(str, Enum):
    EXECUTIVE = "executive"
    PRIVACY_MANAGER = "privacy_manager"
    PMARK_STAFF = "pmark_staff"
    GENERAL_EMPLOYEE = "general_employee"


class EmployeeStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class TrainingFrequency(str, Enum):
    ANNUAL = "annual"


class ComprehensionResult(str, Enum):
    """理解度確認の結果。

    TrainingRecord.comprehension_result が None の場合は「未登録」を表し、
    ここに定義された結果が登録されている状態とは区別する。
    """

    PASSED = "passed"
    FAILED = "failed"


class Company(BaseModel):
    id: int
    name: str
    fiscal_year: int


class Employee(BaseModel):
    id: int
    name: str
    role: EmployeeRole
    status: EmployeeStatus


class TrainingControl(BaseModel):
    """教育管理策の実施ルール（事実データ）。

    「この管理策を採用したかどうか」の正式な判断はここでは持たない。
    採用可否の正本は setup 側の ControlSuggestion（control_id="education"）の
    status であり、ここには採用済みであることを前提とした実施ルール
    （頻度・対象者・必須項目）のみを持つ。
    """

    id: int
    name: str
    frequency: TrainingFrequency
    target_roles: list[EmployeeRole]
    comprehension_required: bool
    material_evidence_required: bool
    approval_required: bool


class TrainingPlan(BaseModel):
    """教育管理策に基づく、年度ごとの実施計画・実施結果（事実データ）。

    MVP初期版では教材証跡と承認をboolで保持していたが、実運用で説明できる
    記録に近づけるため、実施日・方法・教材名・実施責任者・理解度確認方法・
    承認者・承認日も保持する。既存boolは判定互換のため残す。
    """

    id: int
    title: str
    fiscal_year: int
    control_id: int
    execution_date: str | None = None
    delivery_method: str | None = None
    material_name: str | None = None
    instructor_name: str | None = None
    comprehension_method: str | None = None
    material_evidence_registered: bool
    approved: bool
    approved_by: str | None = None
    approved_at: str | None = None


class TrainingRecord(BaseModel):
    """従業者ごとの受講記録（事実データ）。

    completed_on は受講済みという事実の根拠となる日付を保持する。
    comprehension_result が None の場合は「未登録」であり、
    「登録されていて結果が不良」という状態とは区別する。
    """

    employee_id: int
    completed: bool
    completed_on: str | None = None
    comprehension_result: ComprehensionResult | None = None


class EducationEvaluationStatus(str, Enum):
    COMPLIANT = "適合"
    NEEDS_ACTION = "要対応"


class EducationIssue(BaseModel):
    """評価によって検出された個々の不足事項。"""

    rule_id: str
    message: str
    employee_ids: list[int] = []


class EducationEvaluationResult(BaseModel):
    """教育管理策の評価結果。"""

    status: EducationEvaluationStatus
    target_employee_ids: list[int]
    issues: list[EducationIssue] = []
