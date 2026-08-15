from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app import access_control_demo_state, demo_state, intake_demo_state, paper_demo_state, vendor_demo_state
from app.access_control import evaluate_access_control
from app.access_control_routes import router as access_control_router
from app.access_control_schemas import AccessEvaluationStatus
from app.document_routes import get_current_documents
from app.document_routes import router as document_router
from app.document_schemas import DocumentStatus
from app.education import evaluate_training
from app.education_routes import router as education_router
from app.intake import find_control_suggestion
from app.intake_routes import router as intake_router
from app.intake_schemas import ControlDecisionStatus, SetupStatus
from app.paper import evaluate_paper_management
from app.paper_routes import router as paper_router
from app.paper_schemas import PaperEvaluationStatus
from app.schemas import EducationEvaluationStatus
from app.vendor_routes import router as vendor_router
from app.vendor_schemas import VendorEvaluationStatus
from app.vendors import evaluate_vendors

SETUP_STATUS_LABELS = {
    SetupStatus.NOT_STARTED: "未着手",
    SetupStatus.IN_PROGRESS: "設定中",
    SetupStatus.COMPLETE: "完了",
}

SETUP_STATUS_CSS_CLASS = {
    SetupStatus.NOT_STARTED: "not-started",
    SetupStatus.IN_PROGRESS: "needs-action",
    SetupStatus.COMPLETE: "compliant",
}

APP_NAME = "Pマーク取得・運用支援ツール MVP"

app = FastAPI(title=APP_NAME)
app.include_router(intake_router)
app.include_router(education_router)
app.include_router(vendor_router)
app.include_router(access_control_router)
app.include_router(paper_router)
app.include_router(document_router)


def _adoption_gated_status_badge(
    control_id: str,
    control_suggestions,
    compliant: bool,
) -> tuple[str, str]:
    """未採用の管理策を「運用中」であるかのように表示しないための共通処理。

    採用可否の正本（setupのControlSuggestion.status）を確認し、adoptedでなければ
    運用状況（適合／要対応）を表示せず、「未採用」の中立なバッジを返す。
    adoptedの場合のみ、実際の運用評価結果（compliant/要対応）を返す。
    """

    suggestion = find_control_suggestion(control_suggestions, control_id)
    if suggestion is None or suggestion.status != ControlDecisionStatus.ADOPTED:
        return "未採用", "not-started"
    if compliant:
        return "適合", "compliant"
    return "要対応", "needs-action"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    intake_state = intake_demo_state.get_state()
    setup_status = intake_demo_state.get_setup_status(intake_state)
    setup_status_label = SETUP_STATUS_LABELS[setup_status]
    setup_status_class = SETUP_STATUS_CSS_CLASS[setup_status]

    education_state = demo_state.get_state()
    education_result = evaluate_training(
        education_state.employees,
        education_state.control,
        education_state.plan,
        education_state.records,
    )
    education_status_class = (
        "compliant"
        if education_result.status == EducationEvaluationStatus.COMPLIANT
        else "needs-action"
    )

    vendor_state = vendor_demo_state.get_state()
    vendor_result = evaluate_vendors(
        vendor_state.vendors,
        vendor_state.control,
        vendor_state.assessments,
        vendor_state.contracts,
    )
    vendor_status_class = (
        "compliant" if vendor_result.status == VendorEvaluationStatus.COMPLIANT else "needs-action"
    )

    control_suggestions = intake_state.control_suggestions

    access_control_state = access_control_demo_state.get_state()
    access_control_result = evaluate_access_control(
        access_control_state.accounts, access_control_state.control, access_control_state.cycle
    )
    access_control_status_label, access_control_status_class = _adoption_gated_status_badge(
        "access_control",
        control_suggestions,
        access_control_result.status == AccessEvaluationStatus.COMPLIANT,
    )

    paper_state = paper_demo_state.get_state()
    paper_result = evaluate_paper_management(paper_state.control, paper_state.status)
    paper_status_label, paper_status_class = _adoption_gated_status_badge(
        "paper_management",
        control_suggestions,
        paper_result.status == PaperEvaluationStatus.COMPLIANT,
    )

    documents = get_current_documents()
    documents_needs_action = any(document.status == DocumentStatus.DRAFT for document in documents)
    documents_status_label = "情報不足あり" if documents_needs_action else "準備完了"
    documents_status_class = "needs-action" if documents_needs_action else "compliant"

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <title>{APP_NAME}</title>
  <style>
    body {{ font-family: sans-serif; margin: 2rem; line-height: 1.6; max-width: 700px; }}
    .control-card {{ border: 1px solid #ccc; border-radius: 4px; padding: 1rem; margin-bottom: 1rem; }}
    .control-card h3 {{ margin-top: 0; }}
    .status-badge {{ display: inline-block; padding: 0.2rem 0.6rem; border-radius: 4px; }}
    .status-badge.needs-action {{ background: #b30000; color: #fff; }}
    .status-badge.compliant {{ background: #0a7a0a; color: #fff; }}
    .status-badge.not-started {{ background: #666; color: #fff; }}
  </style>
</head>
<body>
  <h1>{APP_NAME}</h1>
  <p>現在はプロトタイプ開発中です。</p>

  <h2>Pマーク準備状況</h2>

  <div class="control-card">
    <h3>初期設定</h3>
    <p>業務ヒアリング・個人情報の確認・リスク確認・管理策の採用判断をまとめて行います。</p>
    <p>状態：<span class="status-badge {setup_status_class}">{setup_status_label}</span></p>
    <p><a href="/setup">確認する</a></p>
  </div>

  <div class="control-card">
    <h3>教育管理</h3>
    <p>状態：<span class="status-badge {education_status_class}">{education_result.status.value}</span></p>
    <p><a href="/education">確認する</a></p>
  </div>

  <div class="control-card">
    <h3>委託先管理</h3>
    <p>状態：<span class="status-badge {vendor_status_class}">{vendor_result.status.value}</span></p>
    <p><a href="/vendors">確認する</a></p>
  </div>

  <div class="control-card">
    <h3>アクセス権限管理</h3>
    <p>状態：<span class="status-badge {access_control_status_class}">{access_control_status_label}</span></p>
    <p><a href="/access-control">確認する</a></p>
  </div>

  <div class="control-card">
    <h3>紙媒体管理</h3>
    <p>状態：<span class="status-badge {paper_status_class}">{paper_status_label}</span></p>
    <p><a href="/paper">確認する</a></p>
  </div>

  <div class="control-card">
    <h3>文書</h3>
    <p>個人情報管理台帳・教育手順・委託先管理手順など、管理策に対応する運用文書を確認します。</p>
    <p>状態：<span class="status-badge {documents_status_class}">{documents_status_label}</span></p>
    <p><a href="/documents">確認する</a></p>
  </div>
</body>
</html>
"""
