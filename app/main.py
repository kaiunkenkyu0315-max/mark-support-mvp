from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app import (
    access_control_demo_state,
    application_prep_demo_state,
    demo_state,
    intake_demo_state,
    paper_demo_state,
    pms_review_demo_state,
    vendor_demo_state,
)
from app.access_control import evaluate_access_control
from app.access_control_routes import router as access_control_router
from app.application_prep import evaluate_application_prep
from app.application_prep_context import build_application_prerequisites
from app.application_prep_routes import router as application_prep_router
from app.dashboard import TodoItem, build_dashboard_data
from app.dashboard_application_plan import enhance_dashboard_with_application_plan
from app.dashboard_plan import focus_dashboard_todos
from app.dashboard_view import render_dashboard_page
from app.dev_routes import router as dev_router
from app.document_routes import get_current_documents
from app.document_routes import router as document_router
from app.education import evaluate_training
from app.education_routes import router as education_router
from app.intake_routes import router as intake_router
from app.paper import evaluate_paper_management
from app.paper_routes import router as paper_router
from app.pms_review import evaluate_pms_review
from app.pms_review_routes import router as pms_review_router
from app.setup_progress import get_effective_setup_status
from app.vendor_routes import router as vendor_router
from app.vendors import evaluate_vendors

APP_NAME = "Pマーク取得・運用支援ツール MVP"

app = FastAPI(title=APP_NAME)
app.include_router(intake_router)
app.include_router(education_router)
app.include_router(vendor_router)
app.include_router(access_control_router)
app.include_router(paper_router)
app.include_router(pms_review_router)
app.include_router(application_prep_router)
app.include_router(document_router)
app.include_router(dev_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    """管理者ダッシュボード（トップページ）。"""

    intake_state = intake_demo_state.get_state()
    setup_status = get_effective_setup_status(intake_state)

    education_state = demo_state.get_state()
    education_result = evaluate_training(
        education_state.employees,
        education_state.control,
        education_state.plan,
        education_state.records,
    )

    vendor_state = vendor_demo_state.get_state()
    vendor_result = evaluate_vendors(
        vendor_state.vendors,
        vendor_state.control,
        vendor_state.assessments,
        vendor_state.contracts,
    )

    access_control_state = access_control_demo_state.get_state()
    access_control_result = evaluate_access_control(
        access_control_state.accounts,
        access_control_state.control,
        access_control_state.cycle,
    )

    paper_state = paper_demo_state.get_state()
    paper_result = evaluate_paper_management(paper_state.control, paper_state.status)
    pms_review_result = evaluate_pms_review(pms_review_demo_state.get_state())

    documents = get_current_documents()

    dashboard_data = build_dashboard_data(
        setup_status=setup_status,
        candidates=intake_state.candidates,
        risks=intake_state.risks,
        control_suggestions=intake_state.control_suggestions,
        documents=documents,
        education_result=education_result,
        vendor_result=vendor_result,
        access_control_result=access_control_result,
        paper_result=paper_result,
    )

    application_prerequisites = build_application_prerequisites()
    application_result = evaluate_application_prep(
        application_prep_demo_state.get_state(),
        application_prerequisites,
    )

    if setup_status.value == "in_progress" and not intake_state.answers_submitted:
        dashboard_data.todo_items = [
            TodoItem(
                area="業務情報",
                message="会社・PMS基本情報は保存済みです。次に業務情報へ回答してください。",
                link="/setup#step1",
            )
        ]

    adopted_areas = [area for area in dashboard_data.operational_areas if area.adopted]
    operations_complete = bool(adopted_areas) and all(
        area.css_class == "compliant" for area in adopted_areas
    )
    if (
        setup_status.value == "complete"
        and dashboard_data.documents_draft_count == 0
        and operations_complete
        and not pms_review_result.complete
    ):
        current_issue = next(
            (issue for issue in pms_review_result.issues if issue.rule_id != "MR-001"),
            None,
        )
        if current_issue is None:
            current_issue = next(iter(pms_review_result.issues), None)
        dashboard_data.todo_items.append(
            TodoItem(
                area="PMS評価・改善",
                message=(
                    current_issue.message
                    if current_issue
                    else "内部監査・是正・マネジメントレビューを確認してください。"
                ),
                link="/pms-review",
            )
        )

    if application_prerequisites.complete and not application_result.complete:
        current_issue = next(iter(application_result.issues), None)
        dashboard_data.todo_items.append(
            TodoItem(
                area="申請準備",
                message=(
                    current_issue.message
                    if current_issue
                    else "申請資格・申請先・申請書類・提出データを確認してください。"
                ),
                link="/application-prep",
            )
        )

    focus_dashboard_todos(dashboard_data)

    html = render_dashboard_page(APP_NAME, dashboard_data)
    return enhance_dashboard_with_application_plan(
        html,
        dashboard_data,
        pms_review_result,
        application_result,
    )
