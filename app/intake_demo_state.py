"""intakeフロー（業務ヒアリング〜管理策候補提示）のデモ用インメモリ状態。

サーバー起動時は「未回答」状態で始まる。利用者がSTEP1の質問に回答して
保存すると、候補生成ロジック（app.intake）を実行して個人情報候補・
管理策候補を用意する。ブラウザからの「回答保存」「確認」「採用」「非適用」
操作は、このモジュールが保持するインメモリ状態のみを変更する。
DBは使用せず、サーバー再起動で未回答の初期状態に戻る。

事実（QuestionnaireAnswers）・候補（status=candidate/suggested）・
確定（status=confirmed/adopted/not_applicable）を混同しない。
候補・推奨を生成するだけでは確定・採用済みにはしない。
"""

from __future__ import annotations

from dataclasses import dataclass

from app.intake import (
    merge_candidates_after_answers_change,
    merge_control_suggestions_after_answers_change,
)
from app.intake_schemas import (
    ControlDecisionStatus,
    ControlSuggestion,
    PersonalInformationCandidate,
    PersonalInformationCandidateStatus,
    QuestionnaireAnswers,
)

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


@dataclass
class IntakeDemoState:
    answers: QuestionnaireAnswers
    answers_submitted: bool
    candidates: list[PersonalInformationCandidate]
    control_suggestions: list[ControlSuggestion]


def build_initial_state() -> IntakeDemoState:
    """デモの初期状態（未回答・候補なし）を構築する。"""

    return IntakeDemoState(
        answers=QuestionnaireAnswers(),
        answers_submitted=False,
        candidates=[],
        control_suggestions=[],
    )


_state: IntakeDemoState = build_initial_state()


def get_state() -> IntakeDemoState:
    """現在のデモ状態を取得する。"""

    return _state


def reset_state() -> IntakeDemoState:
    """デモ状態を未回答の初期状態へ戻す。"""

    global _state
    _state = build_initial_state()
    return _state


def is_setup_complete(state: IntakeDemoState) -> bool:
    """初期設定が完了した状態と見なせるかどうか。

    回答が一度も保存されていない場合は未完了。回答済みでも、
    まだ採用・非適用のいずれも判断していない管理策候補が残っていれば未完了とする。
    """

    if not state.answers_submitted:
        return False
    return not any(
        suggestion.status == ControlDecisionStatus.SUGGESTED
        for suggestion in state.control_suggestions
    )


def submit_answers(answers: QuestionnaireAnswers) -> None:
    """業務ヒアリングの回答を保存し、個人情報候補・管理策候補を再計算する。

    既存の確認・採用・非適用の判断は、回答変更後も前提が成立する限り維持する。
    """

    _state.answers = answers
    _state.answers_submitted = True
    _state.candidates = merge_candidates_after_answers_change(_state.candidates, answers)
    _state.control_suggestions = merge_control_suggestions_after_answers_change(
        _state.control_suggestions, answers
    )


def confirm_candidate(candidate_id: int) -> None:
    """個人情報候補について「取り扱っている」と利用者が確認する。"""

    for candidate in _state.candidates:
        if candidate.id == candidate_id:
            candidate.status = PersonalInformationCandidateStatus.CONFIRMED
            candidate.needs_review = False


def exclude_candidate(candidate_id: int) -> None:
    """個人情報候補について「該当しない」と利用者が判断する。"""

    for candidate in _state.candidates:
        if candidate.id == candidate_id:
            candidate.status = PersonalInformationCandidateStatus.EXCLUDED
            candidate.needs_review = False


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
