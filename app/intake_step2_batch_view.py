"""STEP2 個人情報確認の一括回答UI。

既存の setup ページ描画を土台にしつつ、STEP2だけを
「候補ごとの個別ボタン」から「はい／いいえの一括保存」へ置き換える。
MVPの既存画面構造を大きく崩さず、入力負荷と画面リロード回数を減らすための薄い表示層。
"""

from __future__ import annotations

from html import escape

from app.intake_schemas import PersonalInformationCandidateStatus
from app.intake_demo_state import IntakeDemoState
from app.intake_view import render_setup_page

_STEP2_START = '<section class="step" id="step2">'
_STEP2_END = "</section>"


def _checked(candidate_status: PersonalInformationCandidateStatus, expected: str, needs_review: bool) -> str:
    if needs_review:
        return ""
    if expected == "yes" and candidate_status == PersonalInformationCandidateStatus.CONFIRMED:
        return " checked"
    if expected == "no" and candidate_status == PersonalInformationCandidateStatus.EXCLUDED:
        return " checked"
    return ""


def _render_candidate_question(candidate) -> str:
    field_name = f"candidate_{candidate.id}"
    yes_checked = _checked(candidate.status, "yes", candidate.needs_review)
    no_checked = _checked(candidate.status, "no", candidate.needs_review)
    review_note = (
        '<p class="needs-review">⚠ 業務回答が変更されたため、もう一度確認してください。</p>'
        if candidate.needs_review
        else ""
    )
    return f"""
    <div class="question candidate-batch-question">
      <p>{escape(candidate.name)}を取り扱っていますか？</p>
      <p class="question-help">候補となった理由：{escape(candidate.reason)}</p>
      {review_note}
      <label><input type="radio" name="{field_name}" value="yes" required{yes_checked}> はい</label>
      <label><input type="radio" name="{field_name}" value="no" required{no_checked}> いいえ</label>
    </div>
    """


def render_step2_batch_section(state: IntakeDemoState) -> str:
    if not state.answers_submitted:
        body = "<p>STEP1に回答すると、ここで個人情報候補を確認できるようになります。</p>"
    elif not state.candidates:
        body = "<p>現在の回答からは、確認が必要な個人情報候補はありません。</p>"
    else:
        questions = "".join(_render_candidate_question(candidate) for candidate in state.candidates)
        body = f"""
        <form method="post" action="/setup/candidates/decide" style="display:block;">
          {questions}
          <button type="submit">回答を保存して次へ</button>
        </form>
        """

    return f"""
    <section class="step" id="step2">
      <h2>STEP 2　個人情報確認</h2>
      <p>業務回答から候補を表示しています。実際に取り扱っているかを「はい／いいえ」で回答し、最後にまとめて保存してください。</p>
      {body}
      <p class="back-to-top"><a href="#setup-top">↑ 初期設定の先頭へ戻る</a></p>
    </section>
    """


def render_setup_page_with_batch_step2(state: IntakeDemoState) -> str:
    """既存 setup ページのSTEP2だけを一括回答UIへ差し替える。"""

    html = render_setup_page(state)
    start = html.find(_STEP2_START)
    if start == -1:
        return html
    end = html.find(_STEP2_END, start)
    if end == -1:
        return html
    end += len(_STEP2_END)
    return html[:start] + render_step2_batch_section(state) + html[end:]
