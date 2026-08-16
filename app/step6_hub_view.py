"""STEP6を初期設定完了後の運用開始ハブとして表示する。

管理策の採用判断そのものは行わず、既に採用済みの管理策と既存運用画面への
導線を一覧化するだけにする。
"""

from __future__ import annotations

from html import escape

from app.intake_demo_state import IntakeDemoState
from app.intake_schemas import ControlDecisionStatus
from app.setup_step_gating import step6_unlocked


CONTROL_OPERATION_LABELS: dict[str, str] = {
    "education": "教育管理",
    "vendor_management": "委託先管理",
    "access_control": "アクセス権限管理",
    "paper_management": "紙媒体管理",
}


def _replace_step6(html: str, replacement: str) -> str:
    marker = '<section class="step" id="step6">'
    start = html.find(marker)
    if start == -1:
        return html
    end = html.find("</section>", start)
    if end == -1:
        return html
    end += len("</section>")
    return html[:start] + replacement + html[end:]


def _adopted_control_card(suggestion) -> str:
    name = CONTROL_OPERATION_LABELS.get(suggestion.control_id, suggestion.name)
    if suggestion.link_url:
        action = f'<a href="{escape(suggestion.link_url)}">{escape(name)}を開始する</a>'
    else:
        action = "<span>運用画面は今後対応予定です。</span>"

    return f"""
    <li class="operation-launch-item">
      <strong>{escape(suggestion.name)}</strong>
      <p>{action}</p>
    </li>
    """


def render_step6_hub(state: IntakeDemoState) -> str:
    adopted = [
        suggestion
        for suggestion in state.control_suggestions
        if suggestion.status == ControlDecisionStatus.ADOPTED
    ]
    not_applicable_count = sum(
        1
        for suggestion in state.control_suggestions
        if suggestion.status == ControlDecisionStatus.NOT_APPLICABLE
    )

    if adopted:
        cards = "".join(_adopted_control_card(suggestion) for suggestion in adopted)
        operation_body = f"""
        <p>採用した管理策から、運用を開始してください。</p>
        <ul class="operation-launch-list">{cards}</ul>
        """
    else:
        operation_body = (
            "<p>今回の初期設定では、運用画面を持つ管理策は採用されていません。</p>"
        )

    decision_summary = (
        f'<p class="question-help">採用：{len(adopted)}件 ／ '
        f'非適用：{not_applicable_count}件</p>'
    )

    return f"""
    <section class="step" id="step6">
      <h2>STEP 6　運用開始</h2>
      <p><strong>初期設定が完了しました。</strong></p>
      {decision_summary}
      {operation_body}
      <p><a href="/documents">PMS文書を確認する</a></p>
      <p><a href="/">トップで準備・運用状況を確認する</a></p>
      <p class="back-to-top"><a href="#setup-top">↑ 初期設定の先頭へ戻る</a></p>
    </section>
    """


def apply_step6_hub(html: str, state: IntakeDemoState) -> str:
    """STEP6がアンロック済みの場合だけ、完了ハブへ置き換える。"""

    if not step6_unlocked(state):
        return html
    return _replace_step6(html, render_step6_hub(state))
