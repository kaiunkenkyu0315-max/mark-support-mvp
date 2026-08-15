"""Pマーク運用文書の標準テンプレート。

企業情報・確認済み個人情報・採用済み管理策の設定値（事実データ）を、
固定の文書構成（見出し・定型文）に当てはめて本文（DocumentSection の並び）を
組み立てる。ここではAIによる自由作文は行わず、事実データをテンプレートへ
差し込むだけの純粋関数として実装する。FastAPIやHTML表示には依存しない。

事実データそのもの（対象者・頻度・委託有無・保存期間 等）を別の値として
ここで定義し直すことはしない。既存の事実データ（app.schemas /
app.vendor_schemas / app.intake_schemas のモデル）をそのまま参照する。
"""

from __future__ import annotations

from app.access_control_schemas import AccessControl, AccessReviewCycle
from app.document_schemas import DocumentSection, DocumentTable
from app.education import ROLE_LABELS, frequency_label
from app.intake_schemas import PersonalInformationCandidate
from app.paper_schemas import PaperControl, PaperMediaStatus
from app.schemas import Company, TrainingControl, TrainingPlan
from app.vendor_schemas import VendorControl
from app.vendors import assessment_frequency_label

LEDGER_TABLE_HEADERS: tuple[str, ...] = (
    "個人情報名称",
    "本人区分",
    "利用目的",
    "取得方法",
    "保管方法",
    "保管場所",
    "委託有無",
    "第三者提供有無",
    "保存期間",
    "廃棄方法",
    "管理責任者",
)


def _text_or_placeholder(value: str | None) -> str:
    return value if value else "（未入力）"


def _tristate_label(value: bool | None) -> str:
    if value is None:
        return "（未回答）"
    return "あり" if value else "なし"


# ---------------------------------------------------------------------------
# 個人情報管理台帳
# ---------------------------------------------------------------------------


def build_ledger_sections(
    company: Company, confirmed_candidates: list[PersonalInformationCandidate]
) -> list[DocumentSection]:
    """confirmedな個人情報一覧から、台帳文書の本文を組み立てる。"""

    intro = DocumentSection(
        heading="台帳の位置づけ",
        paragraphs=[
            f"{company.name}が取り扱う個人情報のうち、"
            "「取り扱っている」と確認済みのものを一覧化した台帳である。",
        ],
    )

    if not confirmed_candidates:
        return [
            intro,
            DocumentSection(
                heading="個人情報一覧",
                paragraphs=["確認済みの個人情報がありません。"],
            ),
        ]

    rows = [
        [
            candidate.name,
            candidate.subject_type,
            candidate.purpose,
            _text_or_placeholder(candidate.acquisition_method),
            _text_or_placeholder(candidate.storage_method),
            _text_or_placeholder(candidate.storage_location),
            _tristate_label(candidate.outsourced),
            _tristate_label(candidate.third_party_provided),
            _text_or_placeholder(candidate.retention_period),
            _text_or_placeholder(candidate.disposal_method),
            _text_or_placeholder(candidate.responsible_role),
        ]
        for candidate in confirmed_candidates
    ]

    return [
        intro,
        DocumentSection(
            heading="個人情報一覧",
            table=DocumentTable(headers=list(LEDGER_TABLE_HEADERS), rows=rows),
        ),
    ]


# ---------------------------------------------------------------------------
# 個人情報保護教育手順
# ---------------------------------------------------------------------------


def build_education_procedure_sections(
    company: Company, control: TrainingControl, plan: TrainingPlan
) -> list[DocumentSection]:
    """教育管理策の設定値から、教育手順文書の本文を組み立てる。"""

    role_labels = "、".join(ROLE_LABELS.get(role, role.value) for role in control.target_roles)
    frequency = frequency_label(control)

    return [
        DocumentSection(
            heading="目的",
            paragraphs=[
                f"{company.name}は、個人情報を取り扱う従業者に対し、個人情報の適正な取扱いを"
                "徹底することを目的として、個人情報保護教育を実施する。"
            ],
        ),
        DocumentSection(
            heading="対象者",
            paragraphs=[
                f"教育の対象者は、次の役割の従業者とする：{role_labels}。"
                if role_labels
                else "教育の対象者は設定されていません。"
            ],
        ),
        DocumentSection(
            heading="実施頻度",
            paragraphs=[f"少なくとも{frequency}、個人情報保護教育を実施する。"],
        ),
        DocumentSection(
            heading="教育内容",
            paragraphs=[
                "個人情報保護方針及び関連規程の内容",
                "個人情報の取扱いにおける留意事項",
                "情報漏えい等の事故が発生した場合の対応",
            ],
        ),
        DocumentSection(
            heading="理解度確認",
            paragraphs=[
                "教育実施後、対象者の理解度を確認する。"
                if control.comprehension_required
                else "理解度確認は必須としない。"
            ],
        ),
        DocumentSection(
            heading="未受講者対応",
            paragraphs=[
                "未受講者に対しては、個人情報保護管理者が受講を促し、"
                "必要に応じて再度の受講機会を設ける。"
            ],
        ),
        DocumentSection(
            heading="実施記録",
            paragraphs=[
                "教育の実施日、対象者、実施結果等を記録し保存する。"
                + (
                    "教材の実施記録は必須とする。"
                    if control.material_evidence_required
                    else "教材の実施記録は必須としない。"
                )
            ],
        ),
        DocumentSection(
            heading="承認",
            paragraphs=[
                "教育の実施結果は、個人情報保護管理者の承認を得るものとする。"
                if control.approval_required
                else "教育の実施結果について、承認は必須としない。"
            ],
        ),
    ]


# ---------------------------------------------------------------------------
# 委託先管理手順
# ---------------------------------------------------------------------------


def build_vendor_procedure_sections(
    company: Company, control: VendorControl
) -> list[DocumentSection]:
    """委託先管理策の設定値から、委託先管理手順文書の本文を組み立てる。"""

    frequency = assessment_frequency_label(control)

    return [
        DocumentSection(
            heading="委託先の選定",
            paragraphs=[
                f"{company.name}は、個人情報を取り扱う業務を外部へ委託する場合、"
                "委託先の選定にあたって個人情報保護の観点から適格性を確認する。"
            ],
        ),
        DocumentSection(
            heading="初回評価",
            paragraphs=[
                "委託開始前に、委託先の個人情報保護に関する体制を初回評価として確認する。"
                if control.initial_assessment_required
                else "初回評価は必須としない。"
            ],
        ),
        DocumentSection(
            heading="契約確認",
            paragraphs=[
                "委託契約において、個人情報保護に関する事項が定められていることを確認する。"
                if control.contract_check_required
                else "契約確認は必須としない。"
            ],
        ),
        DocumentSection(
            heading="定期評価",
            paragraphs=[
                f"少なくとも{frequency}、委託先における個人情報の取扱状況を評価する。"
                if control.periodic_assessment_required
                else "定期評価は必須としない。"
            ],
        ),
        DocumentSection(
            heading="評価期限管理",
            paragraphs=[
                "委託先ごとに次回評価期限を管理し、期限を超過した委託先については"
                "速やかに評価を実施する。"
            ],
        ),
        DocumentSection(
            heading="問題があった場合の対応",
            paragraphs=[
                "評価の結果、個人情報の取扱いに問題が確認された委託先については、"
                "改善を求め、改善が認められない場合は委託の見直しを行う。"
            ],
        ),
    ]


# ---------------------------------------------------------------------------
# アクセス権限管理手順
# ---------------------------------------------------------------------------


def build_access_control_procedure_sections(
    company: Company, control: AccessControl, cycle: AccessReviewCycle
) -> list[DocumentSection]:
    """アクセス権限管理策の設定値から、アクセス権限管理手順文書の本文を組み立てる。"""

    return [
        DocumentSection(
            heading="対象",
            paragraphs=[
                f"{company.name}が管理する情報システムの利用者アカウント及び"
                "アクセス権限を対象とする。"
            ],
        ),
        DocumentSection(
            heading="アカウント付与",
            paragraphs=[
                "業務上の必要性を確認したうえで、必要最小限の範囲でアカウント及び"
                "アクセス権限を付与する。"
            ],
        ),
        DocumentSection(
            heading="権限変更",
            paragraphs=[
                "異動等により担当業務が変更になった場合、速やかにアクセス権限の"
                "見直しを行う。"
            ],
        ),
        DocumentSection(
            heading="定期確認",
            paragraphs=[
                "付与されているアカウント及びアクセス権限が適切かどうかを"
                "定期的にレビューする。"
                if control.review_required
                else "権限レビューは必須としない。"
            ],
        ),
        DocumentSection(
            heading="退職・異動時対応",
            paragraphs=[
                "退職・異動等によりアクセスが不要になったアカウントは、"
                "速やかに削除する。"
            ],
        ),
        DocumentSection(
            heading="記録",
            paragraphs=[
                "アカウントの確認・削除、権限レビューの実施結果を記録し保存する。"
                + (
                    "実施結果は承認を得るものとする。"
                    if control.approval_required
                    else "実施結果について、承認は必須としない。"
                )
            ],
        ),
    ]


# ---------------------------------------------------------------------------
# 紙媒体管理手順
# ---------------------------------------------------------------------------


def build_paper_management_procedure_sections(
    company: Company, control: PaperControl, status: PaperMediaStatus
) -> list[DocumentSection]:
    """紙媒体管理策の設定値から、紙媒体管理手順文書の本文を組み立てる。"""

    return [
        DocumentSection(
            heading="保管",
            paragraphs=[
                f"{company.name}は、個人情報が記載された紙媒体を、"
                f"定められた保管場所（{_text_or_placeholder(status.storage_location)}）に保管する。"
            ],
        ),
        DocumentSection(
            heading="施錠",
            paragraphs=[
                "保管場所は施錠可能な場所とし、施錠管理の状況を確認する。"
                if control.lock_check_required
                else "施錠管理の確認は必須としない。"
            ],
        ),
        DocumentSection(
            heading="持出し",
            paragraphs=[
                "紙媒体を持ち出す場合は、定められた持出しルールに従う。"
                if control.take_out_rule_required
                else "持出しルールの設定は必須としない。"
            ],
        ),
        DocumentSection(
            heading="返却",
            paragraphs=[
                "持ち出した紙媒体は、業務終了後速やかに定められた保管場所へ返却する。"
            ],
        ),
        DocumentSection(
            heading="廃棄",
            paragraphs=[
                f"不要になった紙媒体は、定められた廃棄方法"
                f"（{_text_or_placeholder(status.disposal_method)}）により廃棄する。"
                + (
                    "廃棄後は、廃棄が確実に行われたことを確認する。"
                    if control.disposal_check_required
                    else "廃棄確認は必須としない。"
                )
            ],
        ),
        DocumentSection(
            heading="記録",
            paragraphs=[
                "保管・持出し・返却・廃棄の実施状況を記録し保存する。"
                + (
                    "実施結果は承認を得るものとする。"
                    if control.approval_required
                    else "実施結果について、承認は必須としない。"
                )
            ],
        ),
    ]
