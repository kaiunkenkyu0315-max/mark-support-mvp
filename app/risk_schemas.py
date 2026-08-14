"""簡易リスクアセスメントで扱う最小データモデル。

事実（業務回答・確認済み個人情報）→ リスク候補生成 → 利用者確認 → 簡易評価
という段階を明確に分離する。

1. リスク候補（status=candidate）はシステムが機械的に提示したものであり、
   企業が確定したリスクではない。利用者が確認して初めて status=confirmed
   になる。
2. impact/likelihood は、システムが提示する初期値（suggested_impact/
   suggested_likelihood）と、利用者が確定した値（impact/likelihood）を
   区別する。値そのものは同じ整数だが、意味が異なることを常に意識する。
3. 「高リスク（score/level=高）」は、事故発生・法令違反・Pマーク取得可否を
   意味しない。あくまで「優先的に対策を検討すべきリスク」という扱いに
   とどめる。UI・文言でもこの前提を崩さない。
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class RiskCandidateStatus(str, Enum):
    CANDIDATE = "candidate"
    CONFIRMED = "confirmed"
    EXCLUDED = "excluded"


class RiskLevel(str, Enum):
    LOW = "低"
    MEDIUM = "中"
    HIGH = "高"


class RiskCandidate(BaseModel):
    """リスクの候補。

    risk_id（例："RISK-003"）は、回答変更時の再計算で同一のリスクを
    突き合わせるための安定した識別子。id は画面上の操作用の一時的な番号。

    related_personal_information_keys は、関連する confirmed 個人情報の
    PersonalInformationCandidate.source_key の一覧（個人情報側のidは
    回答変更のたびに振り直されるため、安定したsource_keyで参照する）。
    """

    id: int
    risk_id: str
    name: str
    description: str
    reason: str
    related_personal_information_keys: list[str] = []
    status: RiskCandidateStatus = RiskCandidateStatus.CANDIDATE
    suggested_impact: int
    suggested_likelihood: int
    impact: int
    likelihood: int
    needs_review: bool = False
    """回答・確認済み個人情報の変化により前提が変わったため、再確認が望ましい状態。"""


class RiskEvaluation(BaseModel):
    """リスク評価結果（impact × likelihood から算出）。

    事実モデル（RiskCandidate）へ評価結果を埋め込みすぎないよう、
    score/level はここでは保存せず、app.risk.evaluate_risk() が
    都度その場で算出した結果を表すためだけに使う。
    """

    risk_id: str
    score: int
    level: RiskLevel
