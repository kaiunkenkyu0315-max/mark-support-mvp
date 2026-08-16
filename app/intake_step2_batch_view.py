"""STEP2 個人情報確認の一括回答UIと、STEP3の段階表示。

既存の setup ページ描画を土台にしつつ、STEP2を
「候補ごとの個別ボタン」から「はい／いいえの一括保存」へ置き換える。
さらにSTEP3は必要項目を削らず、個人情報ごとの詳細を1件ずつ開く表示にして、
入力負荷ではなく同時に見える情報量を減らす。
"""

from __future__ import annotations

from html import escape

from app.intake_schemas import PersonalInformationCandidateStatus
from app.intake_demo_state import IntakeDemoState
from app.intake_view import render_setup_page

_STEP2_START = '<section class="step" id="step2">'
_STEP2_END = "</section>"

_STEP3_STYLE = """
<style>
  #step3 .candidate-item.ledger-collapsible {
    padding: 0;
    overflow: hidden;
  }
  .ledger-entry-toggle {
    width: 100%;
    box-sizing: border-box;
    padding: 0.8rem 1rem;
    border: 0;
    background: transparent;
    text-align: left;
    cursor: pointer;
    font: inherit;
    font-weight: bold;
  }
  .ledger-entry-toggle:hover { background: #eeeeee; }
  .ledger-entry-toggle::before {
    content: "▶";
    display: inline-block;
    width: 1.2rem;
    font-size: 0.8rem;
  }
  .ledger-collapsible.is-open .ledger-entry-toggle::before { content: "▼"; }
  .ledger-entry-state {
    margin-left: 0.6rem;
    font-size: 0.9rem;
    font-weight: normal;
  }
  .ledger-entry-state.complete { color: #0a7a0a; }
  .ledger-entry-state.incomplete { color: #b30000; }
  .ledger-entry-body {
    display: none;
    padding: 0 1rem 1rem;
  }
  .ledger-collapsible.is-open .ledger-entry-body { display: block; }
</style>
"""

_STEP3_SCRIPT = """
<script>
document.addEventListener("DOMContentLoaded", function () {
  const entries = Array.from(document.querySelectorAll("#step3 .candidate-list > .candidate-item"));
  if (!entries.length) return;

  let firstIncomplete = null;

  entries.forEach(function (entry) {
    const nameNode = entry.querySelector(".candidate-name");
    if (!nameNode) return;

    const isComplete = Boolean(entry.querySelector(".ledger-entry-complete"));
    const statusLabel = isComplete ? "入力済み" : "未入力";

    const originalChildren = Array.from(entry.childNodes);
    const body = document.createElement("div");
    body.className = "ledger-entry-body";
    originalChildren.forEach(function (child) { body.appendChild(child); });

    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "ledger-entry-toggle";
    toggle.setAttribute("aria-expanded", "false");
    toggle.innerHTML = nameNode.textContent +
      '<span class="ledger-entry-state ' + (isComplete ? "complete" : "incomplete") + '">' +
      statusLabel + "</span>";

    entry.classList.add("ledger-collapsible");
    entry.appendChild(toggle);
    entry.appendChild(body);

    if (!isComplete && firstIncomplete === null) firstIncomplete = entry;

    toggle.addEventListener("click", function () {
      const willOpen = !entry.classList.contains("is-open");
      entries.forEach(function (other) {
        other.classList.remove("is-open");
        const otherToggle = other.querySelector(":scope > .ledger-entry-toggle");
        if (otherToggle) otherToggle.setAttribute("aria-expanded", "false");
      });
      if (willOpen) {
        entry.classList.add("is-open");
        toggle.setAttribute("aria-expanded", "true");
      }
    });
  });

  if (firstIncomplete) {
    firstIncomplete.classList.add("is-open");
    const toggle = firstIncomplete.querySelector(":scope > .ledger-entry-toggle");
    if (toggle) toggle.setAttribute("aria-expanded", "true");
  }
});
</script>
"""


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


def _add_step3_progressive_disclosure(html: str) -> str:
    """STEP3の各台帳項目を、ブラウザ側で1件ずつ開く表示にする。"""

    if "</head>" in html:
        html = html.replace("</head>", _STEP3_STYLE + "\n</head>", 1)
    if "</body>" in html:
        html = html.replace("</body>", _STEP3_SCRIPT + "\n</body>", 1)
    return html


def render_setup_page_with_batch_step2(state: IntakeDemoState) -> str:
    """既存 setup ページのSTEP2を一括回答化し、STEP3の見通しを改善する。"""

    html = render_setup_page(state)
    start = html.find(_STEP2_START)
    if start != -1:
        end = html.find(_STEP2_END, start)
        if end != -1:
            end += len(_STEP2_END)
            html = html[:start] + render_step2_batch_section(state) + html[end:]
    return _add_step3_progressive_disclosure(html)
