"""管理者ダッシュボード（トップページ）向けの集約ロジック。

新しい汎用のタスク管理・状態管理は行わない。既存の各モジュールが返す評価結果
（app.intake / app.risk / app.education / app.vendors / app.access_control /
app.paper / app.documents）を、そのまま集約して返すだけとする。

FastAPIやHTML描画には依存しない、純粋な集約処理として実装する
（HTML化は app.dashboard_view が担う）。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.control_status import is_adopted, operational_status
from app.document_schemas import Document, DocumentStatus
from app.intake import find_control_suggestion, is_ledger_entry_complete
from app.intake_schemas import (
    ControlDecisionStatus,
    ControlSuggestion,
    PersonalInformationCandidate,
    PersonalInformationCandidateStatus,
    SetupStatus,
)
from app.risk import evaluate_risk
from app.risk_schemas import RiskCandidate, RiskCandidateStatus, RiskLevel
from app.schemas import EducationEvaluationResult
from app.access_control_schemas import AccessEvaluationResult
from app.paper_schemas import PaperEvaluationResult
from app.vendor_schemas import VendorEvaluationResult

# 運用状況セクションで扱う4管理策の定義（control_id, 表示名, 遷移先URL）。
# 「新しい管理策を増やす」対象ではなく、既存4モジュールを一覧化するための定義。
OPERATIONAL_AREAS: tuple[tuple[str, str, str], ...] = (
    ("education", "教育管理", "/education"),
    ("vendor_management", "委託先管理", "/vendors"),
    ("access_control", "アクセス権限管理", "/access-control"),
    ("paper_management", "紙媒体管理", "/paper"),
)


@dataclass
class TodoItem:
    """「今やること」1件分。既存の評価結果（issue等）をそのまま参照する。"""

    area: str
    message: str
    link: str


@dataclass
class OperationalAreaSummary:
    control_id: str
    name: str
    link: str
    label: str
    css_class: str
    note: str
    adopted: bool


@dataclass
class DashboardData:
    setup_status: SetupStatus
    personal_information_confirmed_count: int
    personal_information_incomplete_count: int
    risk_confirmed_count: int
    risk_high_count: int
    risk_medium_count: int
    risk_low_count: int
    controls_adopted_count: int
    controls_not_applicable_count: int
    controls_needs_review_count: int
    documents_ready_count: int
    documents_draft_count: int
    documents_not_applicable_count: int
    operational_areas: list[OperationalAreaSummary] = field(default_factory=list)
    todo_items: list[TodoItem] = field(default_factory=list)

    @property
    def todo_count(self) -> int:
        return len(self.todo_items)


def _personal_information_summary(
    candidates: list[PersonalInformationCandidate],
) -> tuple[int, int]:
    confirmed = [
        candidate
        for candidate in candidates
        if candidate.status == PersonalInformationCandidateStatus.CONFIRMED
    ]
    incomplete = [
        candidate for candidate in confirmed if not is_ledger_entry_complete(candidate)
    ]
    return len(confirmed), len(incomplete)


def _risk_summary(risks: list[RiskCandidate]) -> tuple[int, int, int, int]:
    confirmed = [risk for risk in risks if risk.status == RiskCandidateStatus.CONFIRMED]
    levels = [evaluate_risk(risk).level for risk in confirmed]
    return (
        len(confirmed),
        levels.count(RiskLevel.HIGH),
        levels.count(RiskLevel.MEDIUM),
        levels.count(RiskLevel.LOW),
    )


def _controls_summary(control_suggestions: list[ControlSuggestion]) -> tuple[int, int, int]:
    adopted = sum(
        1 for s in control_suggestions if s.status == ControlDecisionStatus.ADOPTED
    )
    not_applicable = sum(
        1 for s in control_suggestions if s.status == ControlDecisionStatus.NOT_APPLICABLE
    )
    needs_review = sum(
        1 for s in control_suggestions if s.status == ControlDecisionStatus.SUGGESTED
    )
    return adopted, not_applicable, needs_review


def _documents_summary(documents: list[Document]) -> tuple[int, int, int]:
    ready = sum(1 for d in documents if d.status == DocumentStatus.READY)
    draft = sum(1 for d in documents if d.status == DocumentStatus.DRAFT)
    not_applicable = sum(1 for d in documents if d.status == DocumentStatus.NOT_APPLICABLE)
    return ready, draft, not_applicable


def _setup_todo_items(
    setup_status: SetupStatus,
    candidates: list[PersonalInformationCandidate],
    risks: list[RiskCandidate],
    control_suggestions: list[ControlSuggestion],
) -> list[TodoItem]:
    """初期設定の現在地に応じて、次に行う1工程だけを案内する。"""

    if setup_status == SetupStatus.NOT_STARTED:
        return [
            TodoItem(
                area="初期設定",
                message="まだ回答が保存されていません。業務についての質問に回答してください。",
                link="/setup#step1",
            )
        ]
    if setup_status != SetupStatus.IN_PROGRESS:
        return []

    unresolved_candidates = [
        candidate
        for candidate in candidates
        if candidate.status == PersonalInformationCandidateStatus.CANDIDATE
        or candidate.needs_review
    ]
    if unresolved_candidates:
        return [
            TodoItem(
                area="個人情報",
                message="個人情報候補を確認してください。取り扱っている情報は確認し、該当しないものは除外してください。",
                link="/setup#step2",
            )
        ]

    incomplete_ledger_entries = [
        candidate
        for candidate in candidates
        if candidate.status == PersonalInformationCandidateStatus.CONFIRMED
        and not is_ledger_entry_complete(candidate)
    ]
    if incomplete_ledger_entries:
        return [
            TodoItem(
                area="個人情報台帳",
                message="確認済みの個人情報について、取得方法・保管場所・保存期間などの台帳項目を入力してください。",
                link="/setup#step3",
            )
        ]

    unresolved_risks = [
        risk
        for risk in risks
        if risk.status == RiskCandidateStatus.CANDIDATE or risk.needs_review
    ]
    if unresolved_risks:
        return [
            TodoItem(
                area="リスク",
                message="リスク候補を確認してください。該当するリスクは確認し、該当しないものは除外してください。",
                link="/setup#step4",
            )
        ]

    unresolved_controls = [
        suggestion
        for suggestion in control_suggestions
        if suggestion.status == ControlDecisionStatus.SUGGESTED
        or suggestion.needs_review
    ]
    if unresolved_controls:
        return [
            TodoItem(
                area="管理策",
                message="提示された管理策について、採用するか非適用とするかを判断してください。",
                link="/setup#step5",
            )
        ]

    # SetupStatus.IN_PROGRESSで上記に該当しない場合の安全側フォールバック。
    return [
        TodoItem(
            area="初期設定",
            message="初期設定に未完了の項目があります。内容を確認してください。",
            link="/setup",
        )
    ]


def _operational_todo_items(
    control_id: str,
    name: str,
    link: str,
    suggestion: ControlSuggestion | None,
    issue_messages: list[str],
) -> list[TodoItem]:
    """採用済み（adopted）の管理策についてのみ、不足事項をtodoとして返す。

    未採用（suggested/not_applicable/未提示）の管理策は、実際の不足の有無に
    関わらずtodoを生成しない——「未採用の管理策を要対応と表示しない」を
    ダッシュボードの集計でも守るため。
    """

    if not is_adopted(suggestion):
        return []
    return [TodoItem(area=name, message=message, link=link) for message in issue_messages]


def _setup_not_started_operational_status() -> tuple[str, str, str]:
    """初期設定が未着手のときに、運用状況の各エリアへ一律で使う状態。"""

    return (
        "初期設定待ち",
        "not-started",
        "初期設定がまだ始まっていないため、この管理策が対象になるかどうかまだ判断できません。まず初期設定を開始してください。",
    )


def _document_todo_items(documents: list[Document]) -> list[TodoItem]:
    items: list[TodoItem] = []
    for document in documents:
        if document.status != DocumentStatus.DRAFT:
            continue
        items.append(
            TodoItem(
                area="文書",
                message=f"{document.title}の入力が不足しています。",
                link=f"/documents/{document.document_id}",
            )
        )
    return items


def build_dashboard_data(
    *,
    setup_status: SetupStatus,
    candidates: list[PersonalInformationCandidate],
    risks: list[RiskCandidate],
    control_suggestions: list[ControlSuggestion],
    documents: list[Document],
    education_result: EducationEvaluationResult,
    vendor_result: VendorEvaluationResult,
    access_control_result: AccessEvaluationResult,
    paper_result: PaperEvaluationResult,
) -> DashboardData:
    """既存の各評価結果から、ダッシュボード表示用データを組み立てる。"""

    pi_confirmed, pi_incomplete = _personal_information_summary(candidates)
    risk_confirmed, risk_high, risk_medium, risk_low = _risk_summary(risks)
    controls_adopted, controls_not_applicable, controls_needs_review = _controls_summary(
        control_suggestions
    )
    documents_ready, documents_draft, documents_not_applicable = _documents_summary(documents)

    results_by_control_id = {
        "education": education_result,
        "vendor_management": vendor_result,
        "access_control": access_control_result,
        "paper_management": paper_result,
    }

    operational_areas: list[OperationalAreaSummary] = []
    todo_items: list[TodoItem] = list(
        _setup_todo_items(setup_status, candidates, risks, control_suggestions)
    )

    for control_id, name, link in OPERATIONAL_AREAS:
        suggestion = find_control_suggestion(control_suggestions, control_id)
        result = results_by_control_id[control_id]
        if setup_status == SetupStatus.NOT_STARTED:
            label, css_class, note = _setup_not_started_operational_status()
        else:
            label, css_class, note = operational_status(suggestion, has_issues=bool(result.issues))
        operational_areas.append(
            OperationalAreaSummary(
                control_id=control_id,
                name=name,
                link=link,
                label=label,
                css_class=css_class,
                note=note,
                adopted=is_adopted(suggestion),
            )
        )
        issue_messages = [issue.message for issue in result.issues]
        todo_items.extend(
            _operational_todo_items(control_id, name, link, suggestion, issue_messages)
        )

    if setup_status != SetupStatus.NOT_STARTED and pi_confirmed > 0:
        # 個人情報を1件も確認していない段階では、台帳文書の「情報不足」はまだ
        # 対応可能な文書課題ではない。個人情報確認後に初めて文書todoへ出す。
        todo_items.extend(_document_todo_items(documents))

    return DashboardData(
        setup_status=setup_status,
        personal_information_confirmed_count=pi_confirmed,
        personal_information_incomplete_count=pi_incomplete,
        risk_confirmed_count=risk_confirmed,
        risk_high_count=risk_high,
        risk_medium_count=risk_medium,
        risk_low_count=risk_low,
        controls_adopted_count=controls_adopted,
        controls_not_applicable_count=controls_not_applicable,
        controls_needs_review_count=controls_needs_review,
        documents_ready_count=documents_ready,
        documents_draft_count=documents_draft,
        documents_not_applicable_count=documents_not_applicable,
        operational_areas=operational_areas,
        todo_items=todo_items,
    )
