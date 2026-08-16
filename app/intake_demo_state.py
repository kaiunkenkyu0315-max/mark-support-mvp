"""intakeフロー（業務ヒアリング〜管理策候補提示〜簡易リスクアセスメント）の
デモ用インメモリ状態。

サーバー起動時は「未回答」状態で始まる。利用者がSTEP1の質問に回答して
保存すると、候補生成ロジック（app.intake, app.risk）を実行して個人情報候補・
リスク候補・管理策候補を用意する。ブラウザからの「回答保存」「確認」「採用」
「非適用」「評価変更」「台帳項目入力」操作は、このモジュールが保持する
インメモリ状態のみを変更する。DBは使用せず、サーバー再起動で未回答の初期状態に戻る。

事実（QuestionnaireAnswers）・候補（status=candidate/suggested）・
確定（status=confirmed/adopted/not_applicable）を混同しない。
候補・推奨を生成するだけでは確定・採用済みにはしない。
"""

from __future__ import annotations

from dataclasses import dataclass

from app.intake import (
    is_ledger_complete,
    merge_candidates_after_answers_change,
    merge_control_suggestions,
    recommend_controls,
)
from app.intake_schemas import (
    ControlDecisionStatus,
    ControlSuggestion,
    PersonalInformationCandidate,
    PersonalInformationCandidateStatus,
    QuestionnaireAnswers,
    SetupStatus,
)
from app.risk import merge_risk_candidates_after_change, recommend_controls_from_confirmed_risks
from app.risk_schemas import RiskCandidate, RiskCandidateStatus

# 業務ヒアリングの質問文（利用者向け表示用・フォームのfield名と対応）。
QUESTIONS: list[tuple[str, str]] = [
    ("has_employees", "従業員がいますか？"),
    ("recruits_people", "採用活動を行っていますか？"),
    ("manages_customer_contacts", "顧客や取引先担当者の情報を管理していますか？"),
    ("receives_inquiries", "Webサイト等から問い合わせを受け付けていますか？"),
    (
        "outsources_personal_data_processing",
        "個人情報を扱う業務を外部へ委託していますか？",
    ),
    (
        "uses_external_cloud_services",
        "採用管理・顧客管理・勤怠管理等で外部クラウドサービスを利用していますか？",
    ),
    ("stores_personal_data_on_paper", "紙で個人情報を保管していますか？"),
    ("allows_remote_access", "在宅勤務または社外から個人情報へアクセスしますか？"),
]

# impact/likelihoodが取り得る範囲（1=低〜3=高）。
_EVALUATION_MIN = 1
_EVALUATION_MAX = 3


@dataclass
class IntakeDemoState:
    answers: QuestionnaireAnswers
    answers_submitted: bool
    candidates: list[PersonalInformationCandidate]
    risks: list[RiskCandidate]
    control_suggestions: list[ControlSuggestion]


def build_initial_state() -> IntakeDemoState:
    """デモの初期状態（未回答・候補なし）を構築する。"""

    return IntakeDemoState(
        answers=QuestionnaireAnswers(),
        answers_submitted=False,
        candidates=[],
        risks=[],
        control_suggestions=[],
    )


_state: IntakeDemoState = build_initial_state()


def get_state() -> IntakeDemoState:
    """現在のデモ状態を取得する。"""

    return _state


def reset_state() -> IntakeDemoState:
    """デモ状態を未回答の初期状態へ戻す（個人情報・リスク・管理策の状態も含む）。"""

    global _state
    _state = build_initial_state()
    return _state


def get_setup_status(state: IntakeDemoState) -> SetupStatus:
    """初期設定全体の進捗状態を判定する。

    NOT_STARTED：回答が一度も保存されていない。
    IN_PROGRESS：回答済みだが、以下のいずれかが残っている。
      - 未確認（candidate）のままの個人情報候補・リスク候補
      - 確認済みリスクの評価が未確認
      - 未採用・非適用のいずれも判断していない管理策候補（suggested）
      - 台帳必須項目が未入力の確認済み個人情報
      - needs_review=True の項目（個人情報候補・リスク候補・管理策候補いずれか）
    COMPLETE：回答済みで、上記がすべて解消されている。
    """

    if not state.answers_submitted:
        return SetupStatus.NOT_STARTED

    unresolved_candidates = any(
        candidate.status == PersonalInformationCandidateStatus.CANDIDATE
        or candidate.needs_review
        for candidate in state.candidates
    )
    unresolved_risks = any(
        risk.status == RiskCandidateStatus.CANDIDATE
        or risk.needs_review
        or (
            risk.status == RiskCandidateStatus.CONFIRMED
            and not risk.evaluation_reviewed
        )
        for risk in state.risks
    )
    unresolved_controls = any(
        suggestion.status == ControlDecisionStatus.SUGGESTED or suggestion.needs_review
        for suggestion in state.control_suggestions
    )
    ledger_incomplete = not is_ledger_complete(state.candidates)

    if unresolved_candidates or unresolved_risks or unresolved_controls or ledger_incomplete:
        return SetupStatus.IN_PROGRESS
    return SetupStatus.COMPLETE


def _recalculate_control_suggestions() -> None:
    """管理策候補を再計算する。

    候補生成の根拠は、業務ヒアリングの回答（recommend_controls）と、
    確認済みリスク（recommend_controls_from_confirmed_risks）の2系統がある。
    どちらも「候補を提示する」ところまでであり、採用可否の判断（正本）は
    利用者操作を経て初めて確定する（merge_control_suggestions が、
    既存の採用・非適用判断を維持したまま統合する）。
    """

    fresh_suggestions = recommend_controls(_state.answers) + recommend_controls_from_confirmed_risks(
        _state.risks
    )
    _state.control_suggestions = merge_control_suggestions(
        _state.control_suggestions, fresh_suggestions
    )


def _recalculate_risks() -> None:
    _state.risks = merge_risk_candidates_after_change(
        _state.risks, _state.answers, _state.candidates
    )
    # RISK-001/RISK-002等、確認済みリスクを根拠に提示する管理策候補があるため、
    # リスク再計算のたびに管理策候補も合わせて再計算する。
    _recalculate_control_suggestions()


def submit_answers(answers: QuestionnaireAnswers) -> None:
    """業務ヒアリングの回答を保存し、個人情報候補・リスク候補・管理策候補を再計算する。

    既存の確認・採用・非適用の判断は、回答変更後も前提が成立する限り維持する。
    """

    _state.answers = answers
    _state.answers_submitted = True
    _state.candidates = merge_candidates_after_answers_change(_state.candidates, answers)
    _recalculate_risks()


def confirm_candidate(candidate_id: int) -> None:
    """個人情報候補について「取り扱っている」と利用者が確認する。"""

    for candidate in _state.candidates:
        if candidate.id == candidate_id:
            candidate.status = PersonalInformationCandidateStatus.CONFIRMED
            candidate.needs_review = False
    _recalculate_risks()


def exclude_candidate(candidate_id: int) -> None:
    """個人情報候補について「該当しない」と利用者が判断する。"""

    for candidate in _state.candidates:
        if candidate.id == candidate_id:
            candidate.status = PersonalInformationCandidateStatus.EXCLUDED
            candidate.needs_review = False
    _recalculate_risks()


def decide_candidates(decisions: dict[int, bool]) -> None:
    """個人情報候補の「はい／いいえ」を一括で保存する。

    True は取り扱っている（confirmed）、False は取り扱っていない（excluded）。
    複数件を更新した後にリスク・管理策候補を1回だけ再計算し、STEP2の一括入力で
    候補件数分の再計算が走らないようにする。
    """

    for candidate in _state.candidates:
        if candidate.id not in decisions:
            continue
        candidate.status = (
            PersonalInformationCandidateStatus.CONFIRMED
            if decisions[candidate.id]
            else PersonalInformationCandidateStatus.EXCLUDED
        )
        candidate.needs_review = False
    _recalculate_risks()


def update_ledger_entry(
    candidate_id: int,
    *,
    acquisition_method: str,
    storage_method: str,
    storage_location: str,
    outsourced: bool | None,
    third_party_provided: bool | None,
    retention_period: str,
    disposal_method: str,
    responsible_role: str,
) -> None:
    """確認済み個人情報について、台帳必須項目を保存する。

    文字列項目は空欄をNone（未入力）として扱う。outsourced・third_party_provided は
    bool | None（tri-state）のまま渡されたとおりに保存し、False（なし）と
    None（未回答）を区別する。
    """

    for candidate in _state.candidates:
        if candidate.id == candidate_id:
            candidate.acquisition_method = acquisition_method.strip() or None
            candidate.storage_method = storage_method.strip() or None
            candidate.storage_location = storage_location.strip() or None
            candidate.outsourced = outsourced
            candidate.third_party_provided = third_party_provided
            candidate.retention_period = retention_period.strip() or None
            candidate.disposal_method = disposal_method.strip() or None
            candidate.responsible_role = responsible_role.strip() or None


def confirm_risk(risk_candidate_id: int) -> None:
    """リスク候補について、利用者が「該当する」と確認する（既存互換用）。

    旧UI・既存テストとの互換性のため、この個別操作では現在の初期評価も確認済みとして扱う。
    通常UIでは decide_risks() → update_risk_evaluations() の2段階を使用する。
    """

    for risk in _state.risks:
        if risk.id == risk_candidate_id:
            risk.status = RiskCandidateStatus.CONFIRMED
            risk.needs_review = False
            risk.evaluation_reviewed = True
    _recalculate_control_suggestions()


def exclude_risk(risk_candidate_id: int) -> None:
    """リスク候補について「該当しない」と利用者が判断する。"""

    for risk in _state.risks:
        if risk.id == risk_candidate_id:
            risk.status = RiskCandidateStatus.EXCLUDED
            risk.needs_review = False
            risk.evaluation_reviewed = False
    _recalculate_control_suggestions()


def decide_risks(decisions: dict[int, bool]) -> None:
    """STEP4前半のリスク該当／非該当判断をまとめて保存する。

    True は confirmed、False は excluded。confirmedにしたリスクは、システム初期案の
    impact/likelihoodを保持するが、利用者が次画面で評価を確認するまでは
    evaluation_reviewed=False とする。
    """

    for risk in _state.risks:
        if risk.id not in decisions:
            continue
        if decisions[risk.id]:
            risk.status = RiskCandidateStatus.CONFIRMED
            risk.evaluation_reviewed = False
        else:
            risk.status = RiskCandidateStatus.EXCLUDED
            risk.evaluation_reviewed = False
        risk.needs_review = False
    _recalculate_control_suggestions()


def update_risk_evaluation(risk_candidate_id: int, impact: int, likelihood: int) -> None:
    """confirmedなリスクの影響度・発生可能性を利用者が確認・保存する。"""

    impact = max(_EVALUATION_MIN, min(_EVALUATION_MAX, impact))
    likelihood = max(_EVALUATION_MIN, min(_EVALUATION_MAX, likelihood))
    for risk in _state.risks:
        if risk.id == risk_candidate_id and risk.status == RiskCandidateStatus.CONFIRMED:
            risk.impact = impact
            risk.likelihood = likelihood
            risk.evaluation_reviewed = True


def update_risk_evaluations(evaluations: dict[int, tuple[int, int]]) -> None:
    """STEP4後半のconfirmedリスク評価をまとめて確認・保存する。"""

    for risk in _state.risks:
        if risk.status != RiskCandidateStatus.CONFIRMED or risk.id not in evaluations:
            continue
        impact, likelihood = evaluations[risk.id]
        risk.impact = max(_EVALUATION_MIN, min(_EVALUATION_MAX, impact))
        risk.likelihood = max(_EVALUATION_MIN, min(_EVALUATION_MAX, likelihood))
        risk.evaluation_reviewed = True


def adopt_control(control_id: str) -> None:
    """管理策候補を利用者が採用する。"""

    for suggestion in _state.control_suggestions:
        if suggestion.control_id == control_id:
            suggestion.status = ControlDecisionStatus.ADOPTED
            suggestion.non_applicable_reason = None
            suggestion.needs_review = False


def mark_control_not_applicable(control_id: str, reason: str) -> None:
    """管理策候補を利用者が非適用と判断する。理由を保持する。"""

    for suggestion in _state.control_suggestions:
        if suggestion.control_id == control_id:
            suggestion.status = ControlDecisionStatus.NOT_APPLICABLE
            suggestion.non_applicable_reason = reason
            suggestion.needs_review = False
