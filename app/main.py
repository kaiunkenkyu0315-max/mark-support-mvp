from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app import demo_state, intake_demo_state, vendor_demo_state
from app.education import evaluate_training
from app.education_routes import router as education_router
from app.intake_routes import router as intake_router
from app.schemas import EducationEvaluationStatus
from app.vendor_routes import router as vendor_router
from app.vendor_schemas import VendorEvaluationStatus
from app.vendors import evaluate_vendors

APP_NAME = "Pマーク取得・運用支援ツール MVP"

app = FastAPI(title=APP_NAME)
app.include_router(intake_router)
app.include_router(education_router)
app.include_router(vendor_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    intake_state = intake_demo_state.get_state()
    setup_status_label = "完了" if intake_demo_state.is_setup_complete(intake_state) else "設定中"
    setup_status_class = "compliant" if setup_status_label == "完了" else "needs-action"

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
</body>
</html>
"""
