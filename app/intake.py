"""業務ヒアリングから、個人情報候補・管理策候補を導出する推論ロジック。

事実（QuestionnaireAnswers）→ 個人情報候補生成 → （利用者確認は上位層が行う）
→ 管理策候補生成、という流れの「候補生成」部分を純粋関数として実装する。

FastAPIやHTTP処理・UI表示には依存しない。ここで生成される候補は
あくまで提案であり、利用者が確認・採用して初めて確定する。
本モジュール自身は候補を確定・採用済みにはしない
（生成される候補の status は常に candidate / suggested）。

回答が変更された場合の再計算（merge_*）も、事実→候補という同じ原則に従う。
利用者がすでに確認・採用した判断は、回答変更だけで勝手に消さない。
"""

from __future__ import annotations

from app.intake_schemas import (
    ControlDecisionStatus,
    ControlSuggestion,
    PersonalInformationCandidate,
    PersonalInformationCandidateStatus,
    QuestionnaireAnswers,
)


def derive_personal_information_candidates(
    answers: QuestionnaireAnswers,
) -> list[PersonalInformationCandidate]:
    """業務ヒアリングの回答から、個人情報の候補を導出する。"""

    candidates: list[PersonalInformationCandidate] = []
    next_id = 1

    def add(
        source_key: str,
        name: str,
        subject_type: str,
        purpose: str,
        reason: str,
        outsourced: bool = False,
    ) -> None:
        nonlocal next_id
        candidates.append(
            PersonalInformationCandidate(
                id=next_id,
                name=name,
                subject_type=subject_type,
                purpose=purpose,
                reason=reason,
                source_key=source_key,
                outsourced=outsourced,
                status=PersonalInformationCandidateStatus.CANDIDATE,
            )
        )
        next_id += 1

    if answers.has_employees:
        add(
            source_key="has_employees",
            name="従業員情報",
            subject_type="従業員",
            purpose="人事・労務管理",
            reason="従業員がいると回答されたため",
        )

    if answers.recruits_people:
        add(
            source_key="recruits_people",
            name="採用応募者情報",
            subject_type="採用応募者",
            purpose="採用選考",
            reason="採用活動を行っていると回答されたため",
        )

    if answers.manages_customer_contacts:
        add(
            source_key="manages_customer_contacts",
            name="顧客・取引先担当者情報",
            subject_type="顧客・取引先担当者",
            purpose="営業・契約管理",
            reason="顧客や取引先担当者の情報を管理していると回答されたため",
        )

    if answers.receives_inquiries:
        add(
            source_key="receives_inquiries",
            name="問い合わせ者情報",
            subject_type="問い合わせ者",
            purpose="問い合わせ対応",
            reason="Webサイト等から問い合わせを受け付けていると回答されたため",
        )

    if answers.outsources_personal_data_processing:
        add(
            source_key="outsources_personal_data_processing",
            name="委託業務で取り扱う従業員情報",
            subject_type="従業員",
            purpose="給与計算等の委託業務の遂行",
            reason="給与計算など個人情報を扱う業務を外部委託していると回答されたため",
            outsourced=True,
        )

    return candidates


def recommend_controls(answers: QuestionnaireAnswers) -> list[ControlSuggestion]:
    """業務ヒアリングの回答から、管理策候補を導出する。

    今回のMVPで扱う管理策は、既存の教育管理・委託先管理の2つに限定する。
    """

    suggestions: list[ControlSuggestion] = []

    if answers.has_employees:
        suggestions.append(
            ControlSuggestion(
                control_id="education",
                name="個人情報保護教育",
                reason=(
                    "従業者が個人情報を取り扱う可能性があるため、"
                    "組織として個人情報保護に関するルールや対応方法を周知・教育する必要があります。"
                ),
                link_url="/education",
            )
        )

    if answers.outsources_personal_data_processing:
        suggestions.append(
            ControlSuggestion(
                control_id="vendor_management",
                name="委託先管理",
                reason=(
                    "個人情報を取り扱う業務を外部事業者へ委託しているため、"
                    "委託先の評価・契約確認・継続的な管理が必要になります。"
                ),
                link_url="/vendors",
            )
        )

    return suggestions


def merge_candidates_after_answers_change(
    previous_candidates: list[PersonalInformationCandidate],
    answers: QuestionnaireAnswers,
) -> list[PersonalInformationCandidate]:
    """回答変更後、個人情報候補を再計算する。

    引き続き成立する候補（source_keyが一致）は、利用者がすでに行った
    確認・除外の判断をそのまま維持する。回答変更で前提が失われた候補は、
    未確認（candidate）のままなら取り下げるが、利用者がすでに確認・除外して
    いた場合は判断を消さず、needs_review=True（要再確認）として残す。
    新たに該当するようになった項目は、新規候補として追加する。
    """

    fresh_candidates = derive_personal_information_candidates(answers)
    fresh_keys = {candidate.source_key for candidate in fresh_candidates}
    previous_by_key = {candidate.source_key: candidate for candidate in previous_candidates}

    merged: list[PersonalInformationCandidate] = []

    for fresh_candidate in fresh_candidates:
        previous = previous_by_key.get(fresh_candidate.source_key)
        if previous is None:
            merged.append(fresh_candidate)
        else:
            merged.append(
                fresh_candidate.model_copy(
                    update={"status": previous.status, "needs_review": False}
                )
            )

    for previous in previous_candidates:
        if previous.source_key in fresh_keys:
            continue
        if previous.status == PersonalInformationCandidateStatus.CANDIDATE:
            continue
        merged.append(previous.model_copy(update={"needs_review": True}))

    for index, candidate in enumerate(merged, start=1):
        candidate.id = index

    return merged


def merge_control_suggestions_after_answers_change(
    previous_suggestions: list[ControlSuggestion],
    answers: QuestionnaireAnswers,
) -> list[ControlSuggestion]:
    """回答変更後、管理策候補を再計算する。

    考え方は merge_candidates_after_answers_change と同じ。
    control_id が引き続き提示される場合は、利用者の採用・非適用判断を維持する。
    前提が失われても、すでに採用・非適用と判断されていたものは判断を消さず
    needs_review=True として残す。
    """

    fresh_suggestions = recommend_controls(answers)
    fresh_ids = {suggestion.control_id for suggestion in fresh_suggestions}
    previous_by_id = {suggestion.control_id: suggestion for suggestion in previous_suggestions}

    merged: list[ControlSuggestion] = []

    for fresh_suggestion in fresh_suggestions:
        previous = previous_by_id.get(fresh_suggestion.control_id)
        if previous is None:
            merged.append(fresh_suggestion)
        else:
            merged.append(
                fresh_suggestion.model_copy(
                    update={
                        "status": previous.status,
                        "non_applicable_reason": previous.non_applicable_reason,
                        "needs_review": False,
                    }
                )
            )

    for previous in previous_suggestions:
        if previous.control_id in fresh_ids:
            continue
        if previous.status == ControlDecisionStatus.SUGGESTED:
            continue
        merged.append(previous.model_copy(update={"needs_review": True}))

    return merged
