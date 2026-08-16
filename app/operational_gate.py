"""採用済み管理策だけを運用画面で扱うための共通ゲート。

管理策の採用可否は初期設定側の ControlSuggestion.status を正本とする。
未提示・採用判断待ち・非適用の管理策については、各運用モジュール固有の
評価結果（要対応／適合）や更新操作を利用者へ見せない・実行しない。
"""

from __future__ import annotations

from html import escape

from app import intake_demo_state
from app.control_status import is_adopted, operational_status
from app.intake import find_control_suggestion
from app.intake_schemas import ControlSuggestion


def get_control_suggestion(control_id: str) -> ControlSuggestion | None:
    """初期設定側の管理策判断を取得する。"""

    return find_control_suggestion(
        intake_demo_state.get_state().control_suggestions,
        control_id,
    )


def operational_control_is_adopted(control_id: str) -> bool:
    """指定管理策が運用対象（採用済み）かを返す。"""

    return is_adopted(get_control_suggestion(control_id))


def render_inactive_operation_page(*, title: str, control_id: str) -> str:
    """未採用管理策の運用画面で表示する中立的な案内ページ。"""

    suggestion = get_control_suggestion(control_id)
    label, css_class, note = operational_status(suggestion, has_issues=False)

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <title>{escape(title)}</title>
  <style>
    body {{ font-family: sans-serif; margin: 2rem; line-height: 1.6; max-width: 900px; }}
    .operation-gate {{
      margin-top: 1rem; padding: 1rem 1.25rem; background: #f5f5f5;
      border-left: 4px solid #888;
    }}
    .status-badge {{
      display: inline-block; padding: 0.2rem 0.6rem; border-radius: 4px;
      background: #666; color: #fff;
    }}
    .status-badge.needs-action {{ background: #b30000; }}
    .status-badge.compliant {{ background: #0a7a0a; }}
  </style>
</head>
<body>
  <p><a href="/">&laquo; トップへ戻る</a></p>
  <h1>{escape(title)}</h1>
  <div class="operation-gate">
    <p>状態：<span class="status-badge {escape(css_class)}">{escape(label)}</span></p>
    <p><strong>現在、この管理策は運用対象ではありません。</strong></p>
    <p>{escape(note)}</p>
    <p>運用を開始する場合は、初期設定で管理策の必要性を確認し、採用判断を行ってください。</p>
    <p><a href="/setup#step5">初期設定の管理策確認へ</a></p>
  </div>
</body>
</html>
"""
