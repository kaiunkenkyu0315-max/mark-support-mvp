from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.education_routes import router as education_router

APP_NAME = "Pマーク取得・運用支援ツール MVP"

app = FastAPI(title=APP_NAME)
app.include_router(education_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <title>{APP_NAME}</title>
</head>
<body>
  <h1>{APP_NAME}</h1>
  <p>現在はプロトタイプ開発中です。</p>
  <p>最初の対象機能は「教育管理」です。</p>
  <p><a href="/education">教育管理デモを見る</a></p>
</body>
</html>
"""
