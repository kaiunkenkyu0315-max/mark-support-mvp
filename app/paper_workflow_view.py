"""紙媒体管理画面を「全体工程 → 現在地 → 今やる1件 → 記録入力」に整える。"""

from __future__ import annotations

from html import escape

from app import company_profile
from app.paper_demo_state import PaperDemoState
from app.paper_schemas import PaperEvaluationResult


def _has_issue(result: PaperEvaluationResult, rule_id: str) -> bool:
    return any(issue.rule_id == rule_id for issue in result.issues)


def _step_complete(result: PaperEvaluationResult, step: int) -> bool:
    step1 = not _has_issue(result, "PAP-001")
    step2 = step1 and not _has_issue(result, "PAP-002")
    step3 = step2 and not _has_issue(result, "PAP-003")
    step4 = step3 and not _has_issue(result, "PAP-004")
    return {1: step1, 2: step2, 3: step3, 4: step4}[step]


def _current_step(result: PaperEvaluationResult) -> int | None:
    for step in (1, 2, 3, 4):
        if not _step_complete(result, step):
            return step
    return None


def _step_label(result: PaperEvaluationResult, step: int) -> str:
    if _step_complete(result, step):
        return "完了"
    if _current_step(result) == step:
        return "対応中 ← 現在"
    return "未完了"


def _manager_default() -> str:
    profile = company_profile.get_state()
    return (
        profile.application_contact_name
        or profile.privacy_manager_name
        or profile.application_contact_department_role
        or "Pマーク担当者"
    )


def _approver_default() -> str:
    profile = company_profile.get_state()
    return profile.privacy_manager_name or "個人情報保護管理者"


def _render_overview(state: PaperDemoState, result: PaperEvaluationResult) -> str:
    completed_steps = sum(1 for step in (1, 2, 3, 4) if _step_complete(result, step))
    current = _current_step(result)
    current_label = {
        1: "1. 保管・施錠確認",
        2: "2. 持出しルール",
        3: "3. 廃棄確認",
        4: "4. 実施結果の承認",
        None: "全工程完了",
    }[current]
    status = state.status

    return f"""
    <section class="paper-workflow-overview" style="border:1px solid #ccc; padding:16px; border-radius:4px; margin:24px 0;">
      <h2 style="margin-top:0;">紙媒体管理の全体工程</h2>
      <p>まず全体像と現在地を確認し、下で現在の1工程だけ対応します。</p>
      <p><strong>全体進捗：{completed_steps} / 4 工程 完了</strong></p>
      <ol style="padding-left:1.5rem;">
        <li style="margin-bottom:8px;"><strong>保管・施錠確認</strong> — {"確認済み" if status.storage_locked else "未確認"}　<strong>{_step_label(result, 1)}</strong></li>
        <li style="margin-bottom:8px;"><strong>持出しルール</strong> — {"設定済み" if (status.take_out_rule or "").strip() else "未設定"}　<strong>{_step_label(result, 2)}</strong></li>
        <li style="margin-bottom:8px;"><strong>廃棄確認</strong> — {"実施済み" if status.disposal_confirmed else "未実施"}　<strong>{_step_label(result, 3)}</strong></li>
        <li><strong>実施結果の承認</strong> — {"承認済み" if status.approved else "未承認"}　<strong>{_step_label(result, 4)}</strong></li>
      </ol>
      <p><strong>現在地：{current_label}</strong></p>
    </section>
    """


def _render_focused_todo(result: PaperEvaluationResult) -> str:
    current = _current_step(result)
    if current is None:
        message = "対応が必要な項目はありません。紙媒体管理は完了しています。"
        return f"""
        <section class="focused-todo" style="margin:18px 0;">
          <h2>今やること</h2>
          <p style="color:#167c3a;"><strong>{message}</strong></p>
        </section>
        """

    messages = {
        1: "紙媒体の保管場所と施錠状況を確認し、確認記録を残してください。",
        2: "紙媒体を社外へ持ち出す場合のルールを設定し、記録してください。",
        3: "不要になった紙媒体の廃棄方法と実施結果を確認し、証跡を残してください。",
        4: "個人情報保護管理者が紙媒体管理の実施結果を確認し、承認してください。",
    }
    return f"""
    <section class="focused-todo" style="margin:18px 0; padding:12px 16px; background:#fff8ef; border-left:4px solid #d9822b;">
      <h2 style="margin-top:0;">今やること <span style="font-size:0.8em; font-weight:normal;">1件</span></h2>
      <p><strong>{escape(messages[current])}</strong></p>
    </section>
    """


def _render_storage_form(state: PaperDemoState) -> str:
    status = state.status
    manager = escape(_manager_default())
    location = escape(status.storage_location or "")
    return f"""
    <section id="paper-record" style="border:1px solid #ddd; padding:14px; margin:18px 0;">
      <h2 style="margin-top:0;">1. 保管・施錠確認記録</h2>
      <p>紙媒体の実際の保管場所と施錠運用を確認します。結果は自動選択しません。</p>
      <form method="post" action="/paper/actions/confirm-storage-lock" style="display:block;">
        <label>保管場所 <input type="text" name="storage_location" value="{location}" required></label><br><br>
        <label>確認結果
          <select name="locked" required>
            <option value="" selected disabled>選択してください</option>
            <option value="yes">施錠可能で、施錠運用を確認した</option>
            <option value="no">施錠できない、または施錠運用を確認できない</option>
          </select>
        </label><br><br>
        <label>確認日 <input type="date" name="checked_on" required></label><br><br>
        <label>確認者 <input type="text" name="checked_by" value="{manager}" required></label><br><br>
        <label>確認方法
          <select name="check_method" required>
            <option value="現地確認" selected>現地確認</option>
            <option value="写真・設備情報確認">写真・設備情報確認</option>
            <option value="管理担当者へのヒアリング">管理担当者へのヒアリング</option>
          </select>
        </label><br><br>
        <label>証跡名 <input type="text" name="evidence" value="保管場所施錠確認記録" required></label><br><br>
        <button type="submit">施錠確認記録を保存して次へ</button>
      </form>
    </section>
    """


def _render_takeout_form() -> str:
    manager = escape(_manager_default())
    default_rule = "持出し台帳に記録のうえ、責任者の許可を得て持ち出す。"
    return f"""
    <section id="paper-record" style="border:1px solid #ddd; padding:14px; margin:18px 0;">
      <h2 style="margin-top:0;">2. 持出しルール設定</h2>
      <p>持出し時の許可と記録方法を、実際に運用できる内容で定めます。</p>
      <form method="post" action="/paper/actions/define-take-out-rule" style="display:block;">
        <label>持出しルール<br>
          <textarea name="rule" rows="3" cols="70" required>{escape(default_rule)}</textarea>
        </label><br><br>
        <label>設定日 <input type="date" name="defined_on" required></label><br><br>
        <label>設定者 <input type="text" name="defined_by" value="{manager}" required></label><br><br>
        <button type="submit">持出しルールを保存して次へ</button>
      </form>
    </section>
    """


def _render_disposal_form(state: PaperDemoState) -> str:
    status = state.status
    manager = escape(_manager_default())
    method = escape(status.disposal_method or "")
    return f"""
    <section id="paper-record" style="border:1px solid #ddd; padding:14px; margin:18px 0;">
      <h2 style="margin-top:0;">3. 廃棄確認記録</h2>
      <p>廃棄方法と実施結果を確認します。廃棄済みを自動選択しません。</p>
      <form method="post" action="/paper/actions/confirm-disposal" style="display:block;">
        <label>廃棄方法 <input type="text" name="disposal_method" value="{method}" required></label><br><br>
        <label>確認結果
          <select name="confirmed" required>
            <option value="" selected disabled>選択してください</option>
            <option value="yes">定めた方法で廃棄したことを確認した</option>
            <option value="no">廃棄を確認できていない</option>
          </select>
        </label><br><br>
        <label>確認日 <input type="date" name="confirmed_on" required></label><br><br>
        <label>確認者 <input type="text" name="confirmed_by" value="{manager}" required></label><br><br>
        <label>証跡名 <input type="text" name="evidence" value="紙媒体廃棄確認記録" required></label><br><br>
        <button type="submit">廃棄確認記録を保存して次へ</button>
      </form>
    </section>
    """


def _render_approval_form() -> str:
    approver = escape(_approver_default())
    return f"""
    <section id="paper-record" style="border:1px solid #ddd; padding:14px; margin:18px 0;">
      <h2 style="margin-top:0;">4. 実施結果の承認</h2>
      <p>個人情報保護管理者が保管・持出し・廃棄の実施結果を確認して承認します。</p>
      <form method="post" action="/paper/actions/approve" style="display:block;">
        <label>承認者 <input type="text" name="approved_by" value="{approver}" required></label><br><br>
        <label>承認日 <input type="date" name="approved_at" required></label><br><br>
        <button type="submit">承認記録を保存して完了</button>
      </form>
    </section>
    """


def _render_current_form(state: PaperDemoState, result: PaperEvaluationResult) -> str:
    current = _current_step(result)
    if current == 1:
        return _render_storage_form(state)
    if current == 2:
        return _render_takeout_form()
    if current == 3:
        return _render_disposal_form(state)
    if current == 4:
        return _render_approval_form()
    return """
    <section id="paper-record" style="margin:18px 0;">
      <h2>紙媒体管理記録</h2>
      <p>必要な紙媒体管理記録は登録済みです。</p>
    </section>
    """


def render_paper_workflow(state: PaperDemoState, result: PaperEvaluationResult) -> str:
    return _render_overview(state, result) + _render_focused_todo(result) + _render_current_form(state, result)


def enhance_paper_page(html: str, state: PaperDemoState, result: PaperEvaluationResult) -> str:
    """従来の全件ToDoを、全体工程＋現在工程の記録入力へ置き換える。"""

    workflow = render_paper_workflow(state, result)
    todo_start = html.find('<section class="todo">')
    if todo_start >= 0:
        todo_end = html.find("</section>", todo_start)
        if todo_end >= 0:
            todo_end += len("</section>")
            return html[:todo_start] + workflow + html[todo_end:]

    marker = '<details class="detail">'
    if marker in html:
        return html.replace(marker, workflow + marker, 1)
    return html.replace("</h1>", "</h1>" + workflow, 1)
