"""管理策・確認済み個人情報から、Pマーク運用文書を組み立てる生成ロジック。

企業情報＋確認済み個人情報＋採用済み管理策＋標準テンプレート（app.document_templates）
から文書を構成する。FastAPIやHTTP処理・UI表示には依存しない、純粋関数として実装する。

事実データ（PersonalInformationCandidate / TrainingControl / VendorControl 等）は
呼び出し側（app.document_routes）が既存のデモ状態から取得して渡す。ここで文書用に
別の事実データを新たに保持・複製することはしない。呼び出しのたびに最新の事実データから
組み立て直すため、元データを変更すれば次回表示時のプレビューにも反映される
（文書のスナップショット保存は今回は行わない）。
"""

from __future__ import annotations

from app.access_control_schemas import AccessControl, AccessReviewCycle
from app.document_schemas import Document, DocumentStatus, DocumentType
from app.document_templates import (
    build_access_control_procedure_sections,
    build_education_procedure_sections,
    build_ledger_sections,
    build_paper_management_procedure_sections,
    build_vendor_procedure_sections,
)
from app.intake import LEDGER_FIELD_LABELS, find_control_suggestion, missing_ledger_fields
from app.intake_schemas import (
    ControlDecisionStatus,
    ControlSuggestion,
    PersonalInformationCandidate,
    PersonalInformationCandidateStatus,
)
from app.paper_schemas import PaperControl, PaperMediaStatus
from app.schemas import Company, TrainingControl, TrainingPlan
from app.vendor_schemas import VendorControl

# 管理策IDに対する表示名。recommend_controls() / recommend_controls_from_confirmed_risks()
# が生成する ControlSuggestion.name と同じ名称を用いる（管理策候補が一度も生成されて
# いない場合の文言表示にも使う）。
CONTROL_NAME_LABELS: dict[str, str] = {
    "education": "個人情報保護教育",
    "vendor_management": "委託先管理",
    "access_control": "アクセス権限管理",
    "paper_management": "紙媒体の保管・持出し・廃棄管理",
}


def _not_adopted_message(control_id: str, suggestion: ControlSuggestion | None) -> str:
    name = CONTROL_NAME_LABELS.get(control_id, control_id)
    if suggestion is None:
        return (
            f"管理策『{name}』がまだ候補として提示されていません"
            "（初期設定で業務情報を回答してください）。"
        )
    if suggestion.status == ControlDecisionStatus.NOT_APPLICABLE:
        reason = suggestion.non_applicable_reason or "理由の記載なし"
        return f"管理策『{name}』は非適用と判断されています（理由：{reason}）。"
    return f"管理策『{name}』はまだ採用されていません（初期設定で採用してください）。"


def _confirmed_candidates(
    candidates: list[PersonalInformationCandidate],
) -> list[PersonalInformationCandidate]:
    return [
        candidate
        for candidate in candidates
        if candidate.status == PersonalInformationCandidateStatus.CONFIRMED
    ]


def _ledger_missing_fields(candidates: list[PersonalInformationCandidate]) -> list[str]:
    """台帳文書として不足している項目を、確認済み個人情報ごとに列挙する。

    既存の app.intake.missing_ledger_fields（台帳必須項目の判定）をそのまま再利用し、
    文書側で別の判定基準を新たに定義しない。
    """

    confirmed = _confirmed_candidates(candidates)
    if not confirmed:
        return ["確認済みの個人情報がありません（初期設定のSTEP3で個人情報を確認してください）"]

    missing: list[str] = []
    for candidate in confirmed:
        fields = missing_ledger_fields(candidate)
        if fields:
            labels = "、".join(LEDGER_FIELD_LABELS.get(field, field) for field in fields)
            missing.append(f"{candidate.name}：{labels}")
    return missing


def build_personal_information_ledger_document(
    company: Company, candidates: list[PersonalInformationCandidate]
) -> Document:
    """confirmedな個人情報から、個人情報管理台帳の文書を組み立てる。

    採用済み管理策の有無にかかわらず、確認済み個人情報があれば生成対象とする
    （台帳は特定の管理策の採用を前提としない）。
    """

    confirmed = _confirmed_candidates(candidates)
    missing_fields = _ledger_missing_fields(candidates)
    status = (
        DocumentStatus.READY if confirmed and not missing_fields else DocumentStatus.DRAFT
    )

    return Document(
        document_id=DocumentType.PERSONAL_INFORMATION_LEDGER.value,
        document_type=DocumentType.PERSONAL_INFORMATION_LEDGER,
        title="個人情報管理台帳",
        related_control_ids=[],
        status=status,
        missing_fields=missing_fields,
        sections=build_ledger_sections(company, confirmed),
    )


def build_education_procedure_document(
    company: Company,
    control_suggestions: list[ControlSuggestion],
    control: TrainingControl,
    plan: TrainingPlan,
) -> Document:
    """教育管理策がadoptedの場合のみ、個人情報保護教育手順の文書を組み立てる。

    adoptedでない場合（未提示／suggested／not_applicable）は、正式な生成対象と
    せず status=NOT_APPLICABLE とする。
    """

    suggestion = find_control_suggestion(control_suggestions, "education")
    if suggestion is None or suggestion.status != ControlDecisionStatus.ADOPTED:
        return Document(
            document_id=DocumentType.EDUCATION_PROCEDURE.value,
            document_type=DocumentType.EDUCATION_PROCEDURE,
            title="個人情報保護教育手順",
            related_control_ids=["education"],
            status=DocumentStatus.NOT_APPLICABLE,
            missing_fields=[_not_adopted_message("education", suggestion)],
            sections=[],
        )

    return Document(
        document_id=DocumentType.EDUCATION_PROCEDURE.value,
        document_type=DocumentType.EDUCATION_PROCEDURE,
        title="個人情報保護教育手順",
        related_control_ids=["education"],
        status=DocumentStatus.READY,
        missing_fields=[],
        sections=build_education_procedure_sections(company, control, plan),
    )


def build_vendor_procedure_document(
    company: Company,
    control_suggestions: list[ControlSuggestion],
    control: VendorControl,
) -> Document:
    """委託先管理策がadoptedの場合のみ、委託先管理手順の文書を組み立てる。

    adoptedでない場合（未提示／suggested／not_applicable）は、正式な生成対象と
    せず status=NOT_APPLICABLE とする。
    """

    suggestion = find_control_suggestion(control_suggestions, "vendor_management")
    if suggestion is None or suggestion.status != ControlDecisionStatus.ADOPTED:
        return Document(
            document_id=DocumentType.VENDOR_MANAGEMENT_PROCEDURE.value,
            document_type=DocumentType.VENDOR_MANAGEMENT_PROCEDURE,
            title="委託先管理手順",
            related_control_ids=["vendor_management"],
            status=DocumentStatus.NOT_APPLICABLE,
            missing_fields=[_not_adopted_message("vendor_management", suggestion)],
            sections=[],
        )

    return Document(
        document_id=DocumentType.VENDOR_MANAGEMENT_PROCEDURE.value,
        document_type=DocumentType.VENDOR_MANAGEMENT_PROCEDURE,
        title="委託先管理手順",
        related_control_ids=["vendor_management"],
        status=DocumentStatus.READY,
        missing_fields=[],
        sections=build_vendor_procedure_sections(company, control),
    )


def build_access_control_procedure_document(
    company: Company,
    control_suggestions: list[ControlSuggestion],
    control: AccessControl,
    cycle: AccessReviewCycle,
) -> Document:
    """アクセス権限管理策がadoptedの場合のみ、アクセス権限管理手順の文書を組み立てる。

    adoptedでない場合（未提示／suggested／not_applicable）は、正式な生成対象と
    せず status=NOT_APPLICABLE とする。
    """

    suggestion = find_control_suggestion(control_suggestions, "access_control")
    if suggestion is None or suggestion.status != ControlDecisionStatus.ADOPTED:
        return Document(
            document_id=DocumentType.ACCESS_CONTROL_PROCEDURE.value,
            document_type=DocumentType.ACCESS_CONTROL_PROCEDURE,
            title="アクセス権限管理手順",
            related_control_ids=["access_control"],
            status=DocumentStatus.NOT_APPLICABLE,
            missing_fields=[_not_adopted_message("access_control", suggestion)],
            sections=[],
        )

    return Document(
        document_id=DocumentType.ACCESS_CONTROL_PROCEDURE.value,
        document_type=DocumentType.ACCESS_CONTROL_PROCEDURE,
        title="アクセス権限管理手順",
        related_control_ids=["access_control"],
        status=DocumentStatus.READY,
        missing_fields=[],
        sections=build_access_control_procedure_sections(company, control, cycle),
    )


def build_paper_management_procedure_document(
    company: Company,
    control_suggestions: list[ControlSuggestion],
    control: PaperControl,
    status: PaperMediaStatus,
) -> Document:
    """紙媒体管理策がadoptedの場合のみ、紙媒体管理手順の文書を組み立てる。

    adoptedでない場合（未提示／suggested／not_applicable）は、正式な生成対象と
    せず status=NOT_APPLICABLE とする。
    """

    suggestion = find_control_suggestion(control_suggestions, "paper_management")
    if suggestion is None or suggestion.status != ControlDecisionStatus.ADOPTED:
        return Document(
            document_id=DocumentType.PAPER_MANAGEMENT_PROCEDURE.value,
            document_type=DocumentType.PAPER_MANAGEMENT_PROCEDURE,
            title="紙媒体管理手順",
            related_control_ids=["paper_management"],
            status=DocumentStatus.NOT_APPLICABLE,
            missing_fields=[_not_adopted_message("paper_management", suggestion)],
            sections=[],
        )

    return Document(
        document_id=DocumentType.PAPER_MANAGEMENT_PROCEDURE.value,
        document_type=DocumentType.PAPER_MANAGEMENT_PROCEDURE,
        title="紙媒体管理手順",
        related_control_ids=["paper_management"],
        status=DocumentStatus.READY,
        missing_fields=[],
        sections=build_paper_management_procedure_sections(company, control, status),
    )


def build_all_documents(
    *,
    company: Company,
    candidates: list[PersonalInformationCandidate],
    control_suggestions: list[ControlSuggestion],
    education_control: TrainingControl,
    education_plan: TrainingPlan,
    vendor_control: VendorControl,
    access_control: AccessControl,
    access_review_cycle: AccessReviewCycle,
    paper_control: PaperControl,
    paper_status: PaperMediaStatus,
) -> list[Document]:
    """今回のMVPで扱う5種類の文書をすべて組み立てる。"""

    return [
        build_personal_information_ledger_document(company, candidates),
        build_education_procedure_document(
            company, control_suggestions, education_control, education_plan
        ),
        build_vendor_procedure_document(company, control_suggestions, vendor_control),
        build_access_control_procedure_document(
            company, control_suggestions, access_control, access_review_cycle
        ),
        build_paper_management_procedure_document(
            company, control_suggestions, paper_control, paper_status
        ),
    ]
