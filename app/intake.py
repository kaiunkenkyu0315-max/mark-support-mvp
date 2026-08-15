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

# 台帳必須項目（confirmedな個人情報について、これらがすべて入力されて初めて
# 台帳としての記載が完了したと見なす）。文字列項目とtri-state（bool | None）項目は
# 「入力済み」の判定方法が異なるため分けて管理する。
LEDGER_REQUIRED_TEXT_FIELDS: tuple[str, ...] = (
    "name",
    "subject_type",
    "purpose",
    "acquisition_method",
    "storage_method",
    "storage_location",
    "retention_period",
    "disposal_method",
    "responsible_role",
)
LEDGER_REQUIRED_BOOL_FIELDS: tuple[str, ...] = ("outsourced", "third_party_provided")

# 台帳フォームで利用者が入力する項目のうち、回答変更後の再計算（merge）でも
# 維持すべきもの。name/subject_type/purposeは業務ヒアリングの回答から
# 再導出されるためここには含めない。
LEDGER_EDITABLE_FIELDS: tuple[str, ...] = LEDGER_REQUIRED_TEXT_FIELDS[3:] + LEDGER_REQUIRED_BOOL_FIELDS

# 管理策の採用状態（ControlDecisionStatus）の表示用ラベル。
# 「管理策を採用したかどうか」の正式な判断はsetup（ControlSuggestion.status）を
# 正とする。education・vendors等の運用画面や文書生成は、このラベルおよび
# find_control_suggestion() を介して採用状態を参照し、独自の採用判断を持たない。
CONTROL_STATUS_LABELS: dict[ControlDecisionStatus, str] = {
    ControlDecisionStatus.SUGGESTED: "未採用（候補）",
    ControlDecisionStatus.ADOPTED: "採用済み",
    ControlDecisionStatus.NOT_APPLICABLE: "非適用",
}

# 台帳必須項目のUI表示用ラベル。
LEDGER_FIELD_LABELS: dict[str, str] = {
    "name": "個人情報名称",
    "subject_type": "対象本人の区分",
    "purpose": "利用目的",
    "acquisition_method": "取得方法",
    "storage_method": "保管方法",
    "storage_location": "保管場所",
    "outsourced": "外部委託の有無",
    "third_party_provided": "第三者提供の有無",
    "retention_period": "保管期間",
    "disposal_method": "廃棄方法",
    "responsible_role": "管理担当者（役割）",
}


def missing_ledger_fields(candidate: PersonalInformationCandidate) -> list[str]:
    """1件の個人情報について、未入力の台帳必須項目のフィールド名一覧を返す。

    confirmedでない候補は、すべての台帳必須項目を未入力として扱う。
    """

    if candidate.status != PersonalInformationCandidateStatus.CONFIRMED:
        return [*LEDGER_REQUIRED_TEXT_FIELDS, *LEDGER_REQUIRED_BOOL_FIELDS]
    missing = [
        field
        for field in LEDGER_REQUIRED_TEXT_FIELDS
        if not (getattr(candidate, field) or "").strip()
    ]
    missing += [field for field in LEDGER_REQUIRED_BOOL_FIELDS if getattr(candidate, field) is None]
    return missing


def find_control_suggestion(
    control_suggestions: list[ControlSuggestion], control_id: str
) -> ControlSuggestion | None:
    """control_idに対応するControlSuggestionを取得する。

    採用可否の正式な判断（adopted / not_applicable）を参照する唯一の入口として、
    education・vendors・documents等はこの関数を介して setup の判断を参照する。
    該当するControlSuggestionがまだ存在しない（=setupでまだ回答・提示されていない）
    場合はNoneを返す。
    """

    return next(
        (suggestion for suggestion in control_suggestions if suggestion.control_id == control_id),
        None,
    )


def is_ledger_entry_complete(candidate: PersonalInformationCandidate) -> bool:
    """1件の個人情報について、台帳必須項目がすべて入力済みかどうか。

    confirmed（取り扱っていると確認済み）でない候補は、そもそも台帳に
    記載する対象ではないため、常にFalseとする。
    """

    if candidate.status != PersonalInformationCandidateStatus.CONFIRMED:
        return False
    return not missing_ledger_fields(candidate)


def is_ledger_complete(candidates: list[PersonalInformationCandidate]) -> bool:
    """確認済み個人情報すべてについて、台帳必須項目が入力済みかどうか。

    確認済みの個人情報が1件もない場合は、記載すべき対象がないためTrueとする。
    """

    confirmed = [
        candidate
        for candidate in candidates
        if candidate.status == PersonalInformationCandidateStatus.CONFIRMED
    ]
    return all(is_ledger_entry_complete(candidate) for candidate in confirmed)


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
        outsourced: bool | None = None,
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
    確認・除外の判断、および入力済みの台帳必須項目をそのまま維持する。
    回答変更で前提が失われた候補は、未確認（candidate）のままなら取り下げるが、
    利用者がすでに確認・除外していた場合は判断を消さず、needs_review=True
    （要再確認）として残す。新たに該当するようになった項目は、新規候補として追加する。
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
                    update={
                        "status": previous.status,
                        "needs_review": False,
                        **{field: getattr(previous, field) for field in LEDGER_EDITABLE_FIELDS},
                    }
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
