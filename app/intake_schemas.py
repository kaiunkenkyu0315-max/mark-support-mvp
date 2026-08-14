"""業務ヒアリング〜管理策候補提示（intakeフロー）で扱う最小データモデル。

Pマーク準備の上流工程として、次の段階を明確に分離して表現する。

1. 利用者が回答した事実         → QuestionnaireAnswers
2. システムが推定した個人情報候補 → PersonalInformationCandidate（status=candidate）
3. 利用者が確認した個人情報       → PersonalInformationCandidate（status=confirmed）
4. システムが提示した管理策候補   → ControlSuggestion（status=suggested）
5. 利用者が採用した管理策         → ControlSuggestion（status=adopted）

「候補」と「確定」、「推奨」と「採用」を混同しない。システムが候補・推奨を
生成しただけでは、個人情報も管理策も確定・採用済みにはならない。
利用者による確認・採用操作を経て初めて status が変化する。
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class QuestionnaireAnswers(BaseModel):
    """業務ヒアリングへの回答（事実）。

    各項目は、利用者がまだ回答していない間は None（未回答）を取り得る。
    None は「いいえ」ではなく「まだ分からない・未回答」を意味する。
    """

    has_employees: bool | None = None
    recruits_people: bool | None = None
    manages_customer_contacts: bool | None = None
    receives_inquiries: bool | None = None
    outsources_personal_data_processing: bool | None = None
    uses_external_cloud_services: bool | None = None
    stores_personal_data_on_paper: bool | None = None
    allows_remote_access: bool | None = None


class PersonalInformationCandidateStatus(str, Enum):
    CANDIDATE = "candidate"
    CONFIRMED = "confirmed"
    EXCLUDED = "excluded"


class PersonalInformationCandidate(BaseModel):
    """個人情報の候補。

    システムが業務ヒアリングの回答から生成した時点では status=candidate
    であり、これを企業の正式な個人情報として扱ってはならない。
    利用者が確認して初めて status=confirmed になる。

    source_key は、この候補がどの回答項目（QuestionnaireAnswers のフィールド名）
    から生成されたかを表す安定した識別子で、回答変更時の再計算で
    同一の候補を突き合わせるために使う。
    """

    id: int
    name: str
    subject_type: str
    purpose: str
    reason: str
    source_key: str
    outsourced: bool = False
    status: PersonalInformationCandidateStatus = PersonalInformationCandidateStatus.CANDIDATE
    needs_review: bool = False
    """回答変更により前提が変わったため、利用者による再確認が望ましい状態。"""


class ControlDecisionStatus(str, Enum):
    SUGGESTED = "suggested"
    ADOPTED = "adopted"
    NOT_APPLICABLE = "not_applicable"


class ControlSuggestion(BaseModel):
    """管理策候補と、それに対する利用者の採用判断。

    システムが提示した時点では status=suggested であり、これを企業の
    採用済み管理策として扱ってはならない。利用者が採用操作をして初めて
    status=adopted になる。非適用の場合は理由を保持する。
    """

    control_id: str
    name: str
    reason: str
    status: ControlDecisionStatus = ControlDecisionStatus.SUGGESTED
    non_applicable_reason: str | None = None
    link_url: str | None = None
    needs_review: bool = False
    """回答変更により前提が変わったため、利用者による再確認が望ましい状態。"""
