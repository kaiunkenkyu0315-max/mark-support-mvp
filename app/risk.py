"""確認済み個人情報・業務回答から、リスク候補を導出し評価する推論ロジック。

事実（QuestionnaireAnswers・confirmedなPersonalInformationCandidate）→
リスク候補生成 → （利用者確認は上位層が行う）→ 簡易評価、という流れを
純粋関数として実装する。FastAPI/HTTP・UI表示には依存しない。

「高リスク」は事故発生・法令違反・Pマーク取得可否を意味しない。
あくまで優先的に対策を検討すべきリスクという扱いにとどめる。

既存の管理策推薦ロジック（app.intake.recommend_controls）は変更しない。
確認済みリスクに基づく提示理由の補足は、表示専用のヘルパー関数として
ここに追加する。
"""

from __future__ import annotations

from app.intake_schemas import (
    PersonalInformationCandidate,
    PersonalInformationCandidateStatus,
    QuestionnaireAnswers,
)
from app.risk_schemas import RiskCandidate, RiskCandidateStatus, RiskEvaluation, RiskLevel

# 影響度・発生可能性は1〜3の3段階（1=低 / 2=中 / 3=高）。
IMPACT_LOW, IMPACT_MEDIUM, IMPACT_HIGH = 1, 2, 3
LIKELIHOOD_LOW, LIKELIHOOD_MEDIUM, LIKELIHOOD_HIGH = 1, 2, 3

# risk_score = impact × likelihood の分類しきい値。
# impact・likelihoodとも1〜3なので、取り得るscoreは {1,2,3,4,6,9} のみ
# （5,7,8は組み合わせ上出現しない）。低=1〜2、中=3〜5、高=6〜9とする。
_LOW_SCORE_MAX = 2
_MEDIUM_SCORE_MAX = 5

# 既存2管理策と、それぞれが関連するリスクIDの対応。
# 「今回まだ対応管理策を本格実装しない」リスク（不正アクセス・紙媒体紛失）は含めない。
CONTROL_RELATED_RISK_IDS: dict[str, list[str]] = {
    "education": ["RISK-004", "RISK-005"],
    "vendor_management": ["RISK-003"],
}


def calculate_risk_level(impact: int, likelihood: int) -> RiskLevel:
    """impact × likelihood から、優先度の目安となるリスクレベルを算出する。"""

    score = impact * likelihood
    if score <= _LOW_SCORE_MAX:
        return RiskLevel.LOW
    if score <= _MEDIUM_SCORE_MAX:
        return RiskLevel.MEDIUM
    return RiskLevel.HIGH


def evaluate_risk(candidate: RiskCandidate) -> RiskEvaluation:
    """リスク候補の現在の impact/likelihood から評価結果を算出する。"""

    score = candidate.impact * candidate.likelihood
    return RiskEvaluation(
        risk_id=candidate.risk_id,
        score=score,
        level=calculate_risk_level(candidate.impact, candidate.likelihood),
    )


def _confirmed(
    personal_information: list[PersonalInformationCandidate],
) -> list[PersonalInformationCandidate]:
    return [
        candidate
        for candidate in personal_information
        if candidate.status == PersonalInformationCandidateStatus.CONFIRMED
    ]


def derive_risk_candidates(
    answers: QuestionnaireAnswers,
    personal_information: list[PersonalInformationCandidate],
) -> list[RiskCandidate]:
    """業務回答・確認済み個人情報から、リスク候補を導出する。

    confirmedになっていない個人情報候補は、ここでは確定した業務実態として
    扱わない（=リスク候補生成の根拠にしない）。
    """

    confirmed = _confirmed(personal_information)
    candidates: list[RiskCandidate] = []
    next_id = 1

    def add(
        risk_id: str,
        name: str,
        description: str,
        reason: str,
        related: list[str],
        suggested_impact: int,
        suggested_likelihood: int,
    ) -> None:
        nonlocal next_id
        candidates.append(
            RiskCandidate(
                id=next_id,
                risk_id=risk_id,
                name=name,
                description=description,
                reason=reason,
                related_personal_information_keys=related,
                status=RiskCandidateStatus.CANDIDATE,
                suggested_impact=suggested_impact,
                suggested_likelihood=suggested_likelihood,
                impact=suggested_impact,
                likelihood=suggested_likelihood,
            )
        )
        next_id += 1

    if answers.uses_external_cloud_services or answers.allows_remote_access:
        add(
            risk_id="RISK-001",
            name="不正アクセス",
            description=(
                "外部サービスや社外からのアクセスにより、認証情報の漏えい、"
                "不正ログイン等によって個人情報へ不正アクセスされる可能性があります。"
            ),
            reason="外部クラウドサービスの利用、または社外からのアクセスがあると回答されたため",
            related=[],
            suggested_impact=IMPACT_HIGH,
            suggested_likelihood=LIKELIHOOD_MEDIUM,
        )

    if answers.stores_personal_data_on_paper:
        add(
            risk_id="RISK-002",
            name="紙媒体の紛失・盗難",
            description="紙媒体の持ち出し、保管、廃棄等の過程で紛失・盗難が発生する可能性があります。",
            reason="紙で個人情報を保管していると回答されたため",
            related=[],
            suggested_impact=IMPACT_MEDIUM,
            suggested_likelihood=LIKELIHOOD_MEDIUM,
        )

    if answers.outsources_personal_data_processing:
        add(
            risk_id="RISK-003",
            name="委託先での漏えい・不適切な取扱い",
            description=(
                "委託先での誤操作、不正アクセス、不適切な再委託等によって"
                "個人情報が漏えいする可能性があります。"
            ),
            reason="個人情報を扱う外部委託があると回答されたため",
            related=[candidate.source_key for candidate in confirmed if candidate.outsourced],
            suggested_impact=IMPACT_HIGH,
            suggested_likelihood=LIKELIHOOD_MEDIUM,
        )

    if confirmed:
        add(
            risk_id="RISK-004",
            name="誤送信・誤提供",
            description=(
                "メール送信、ファイル共有、帳票交付等の際に誤った相手へ"
                "個人情報を送付・提供する可能性があります。"
            ),
            reason="確認済みの個人情報を日常業務で利用しているため",
            related=[candidate.source_key for candidate in confirmed],
            suggested_impact=IMPACT_MEDIUM,
            suggested_likelihood=LIKELIHOOD_HIGH,
        )

    if answers.has_employees and confirmed:
        add(
            risk_id="RISK-005",
            name="内部者による不適切な取扱い",
            description="個人情報を取り扱う従業者による誤操作、ルール違反、不正持ち出し等が発生する可能性があります。",
            reason="従業員がいると回答され、確認済みの個人情報が存在するため",
            related=[candidate.source_key for candidate in confirmed],
            suggested_impact=IMPACT_MEDIUM,
            suggested_likelihood=LIKELIHOOD_MEDIUM,
        )

    return candidates


def merge_risk_candidates_after_change(
    previous_risks: list[RiskCandidate],
    answers: QuestionnaireAnswers,
    personal_information: list[PersonalInformationCandidate],
) -> list[RiskCandidate]:
    """回答・確認済み個人情報の変更後、リスク候補を再計算する。

    考え方は app.intake の merge_* と同じ。risk_id が引き続き該当する場合は、
    利用者の確認・除外判断と impact/likelihood をそのまま維持する。
    前提が失われても、すでに確認・除外済みだった場合は判断を消さず
    needs_review=True（要再確認）として残す。未確認のまま前提を失った候補は
    取り下げる。
    """

    fresh_risks = derive_risk_candidates(answers, personal_information)
    fresh_ids = {risk.risk_id for risk in fresh_risks}
    previous_by_id = {risk.risk_id: risk for risk in previous_risks}

    merged: list[RiskCandidate] = []

    for fresh_risk in fresh_risks:
        previous = previous_by_id.get(fresh_risk.risk_id)
        if previous is None:
            merged.append(fresh_risk)
        else:
            merged.append(
                fresh_risk.model_copy(
                    update={
                        "status": previous.status,
                        "impact": previous.impact,
                        "likelihood": previous.likelihood,
                        "needs_review": False,
                    }
                )
            )

    for previous in previous_risks:
        if previous.risk_id in fresh_ids:
            continue
        if previous.status == RiskCandidateStatus.CANDIDATE:
            continue
        merged.append(previous.model_copy(update={"needs_review": True}))

    for index, risk in enumerate(merged, start=1):
        risk.id = index

    return merged


def confirmed_risk_reasons_for_control(control_id: str, risks: list[RiskCandidate]) -> list[str]:
    """確認済みリスクに基づく、管理策候補への補足理由（表示用）を返す。

    既存の recommend_controls() が返す提示理由（1文）は変更せず、
    ここで追加の補足理由だけを別途返す。呼び出し側（表示層）が
    両者を組み合わせて表示する。status=confirmed 以外のリスクは、
    渡されたリストに含まれていてもここで除外する。
    """

    related_risk_ids = CONTROL_RELATED_RISK_IDS.get(control_id, [])
    return [
        f"{risk.name}リスクが確認されています。"
        for risk in risks
        if risk.risk_id in related_risk_ids and risk.status == RiskCandidateStatus.CONFIRMED
    ]
