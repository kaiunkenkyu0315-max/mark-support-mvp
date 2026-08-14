# mark-support-mvp

中小企業向けPマーク取得・運用支援ツールのMVP

現在は開発基盤のみを構築した段階です。業務機能はまだ実装していません。

## 構成

* Python 3.12
* FastAPI
* Uvicorn
* Pydantic
* pytest
* GitHub Codespaces / devcontainer

## 起動

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

起動後、ブラウザで `http://localhost:8000/` にアクセスするとトップページが、
`http://localhost:8000/health` にアクセスするとヘルスチェック用のJSONが表示されます。

## テスト

```bash
python3 -m pytest -q
```

## Codespaces

GitHub Codespacesでリポジトリを開くと、`.devcontainer/devcontainer.json` の設定に従って
Python 3.12環境が構築され、`requirements.txt` が自動でインストールされます。
ポート8000がフォワードされるため、起動後はブラウザからそのままアクセスできます。

## 現在のMVP方針

現段階では、FastAPIアプリの起動・動作確認・テストができる最小限の開発基盤のみを用意しています。
業務機能（教育管理、従業者管理、管理策管理など）はまだ実装していません。

次の実装対象は「教育管理」機能です。
