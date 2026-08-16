"""初期設定画面の補助UI。

- STEP0: 会社・PMS基本情報を共通データとして入力
- STEP1: STEP0で確定した事実は再入力させない
- STEP2: 個人情報候補を「はい／いいえ」で一括回答
- STEP3: 個人情報台帳を1件ずつ開く段階表示

既存の setup ページ描画を土台にし、MVPの構造を大きく崩さずに
入力負荷と同時表示情報量を減らす。
"""

from __future__ import annotations

import re
from html import escape

from app import company_profile
from app.company_profile_view import render_company_section as _render_shared_company_section
from app.intake_demo_state import IntakeDemoState
from app.intake_schemas import PersonalInformationCandidateStatus
from app.intake_view import render_setup_page

_STEP1_START = '<section class="step" id="step1">'
_STEP2_START = '<section class="step" id="step2">'
_STEP2_END = "</section>"

_EXTRA_STYLE = """
<style>
  #step0 .company-form {
    display: block;
    max-width: 34rem;
  }
  #step0 .company-form-field {
    margin: 0 0 0.8rem;
  }
  #step0 .company-form-field label {
    display: block;
    font-weight: bold;
    margin-bottom: 0.15rem;
  }
  #step0 .company-form-field input {
    box-sizing: border-box;
    width: min(28rem, 95%);
    padding: 0.3rem 0.4rem;
  }
  #step0 .company-profile-status {
    font-size: 0.9rem;
    color: #555;
  }
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


def _render_company_section() -> str:
    """旧STEP0描画（互換用）。通常画面では company_profile_view を使用する。"""
    profile = company_profile.get_state()
    status = "保存済み" if profile.configured else "未保存（現在はデモ初期値）"
    return f"""
    <section class="step" id="step0">
      <h2>STEP 0　会社情報</h2>
      <p>ここで登録した会社情報を、教育管理など各機能で共通利用します。同じ情報を機能ごとに入力する必要はありません。</p>
      <p class="company-profile-status">会社情報の状態：{status}</p>
      <form method="post" action="/setup/company" class="company-form">
        <div class="company-form-field">
          <label for="company-name">会社名</label>
          <input id="company-name" type="text" name="name" value="{escape(profile.name)}" required>
        </div>
        <div class="company-form-field">
          <label for="employee-count">従業者数</label>
          <input id="employee-count" type="number" name="employee_count" min="1" max="9999"
                 value="{profile.employee_count}" required>
          <p class="question-help">役員・従業員など、個人情報保護教育の対象となる人のおおよその人数を入力してください。</p>
        </div>
        <div class="company-form-field">
          <label for="fiscal-year">対象年度</label>
          <input id="fiscal-year" type="number" name="fiscal_year" min="2000" max="2100"
                 value="{profile.fiscal_year}" required>
        </div>
        <button type="submit">会社情報を保存して次へ</button>
      </form>
      <p class="back-to-top"><a href="#setup-top">↑ 初期設定の先頭へ戻る</a></p>
    </section>
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


def _inject_step0(html: str) -> str:
    """工程ナビゲーションとSTEP1の直前に会社・PMS基本情報を追加する。"""

    step0_nav = '<li><a href="#step0">STEP0 会社・PMS基本情報</a></li>'
    html = html.replace('<ol class="stepper">', f'<ol class="stepper">{step0_nav}', 1)
    html = html.replace(_STEP1_START, _render_shared_company_section() + "\n" + _STEP1_START, 1)
    return html


def _replace_employee_question_with_company_fact(html: str) -> str:
    """STEP0保存後は従業者の有無を再質問せず、共通情報からの自動反映として表示する。"""

    profile = company_profile.get_state()
    if not profile.configured:
        return html

    pattern = (
        r'\s*<div class="question">\s*'
        r'<p>従業員がいますか？</p>.*?'
        r'name="has_employees".*?'
        r'</div>'
    )
    replacement = f"""
        <div class="question company-derived-fact">
          <p>従業者数：{profile.employee_count}名</p>
          <p class="question-help">STEP0の会社情報から自動反映しています。この項目はここでは再入力不要です。</p>
        </div>
    """
    return re.sub(pattern, replacement, html, count=1, flags=re.DOTALL)


def _add_progressive_disclosure(html: str) -> str:
    if "</head>" in html:
        html = html.replace("</head>", _EXTRA_STYLE + "\n</head>", 1)
    if "</body>" in html:
        html = html.replace("</body>", _STEP3_SCRIPT + "\n</body>", 1)
    return html


def render_setup_page_with_batch_step2(state: IntakeDemoState) -> str:
    """会社・PMS基本情報・重複排除・STEP2一括回答・STEP3段階表示を統合する。"""

    html = _inject_step0(render_setup_page(state))
    html = _replace_employee_question_with_company_fact(html)
    start = html.find(_STEP2_START)
    if start != -1:
        end = html.find(_STEP2_END, start)
        if end != -1:
            end += len(_STEP2_END)
            html = html[:start] + render_step2_batch_section(state) + html[end:]
    return _add_progressive_disclosure(html)
