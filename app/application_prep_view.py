"""Pマーク新規申請準備の森→木UI。"""

from __future__ import annotations

from html import escape

from app import company_profile
from app.application_prep import evaluate_application_prep
from app.application_prep_schemas import ApplicationPreparationState, ApplicationPrerequisites


def _checked(value: bool) -> str:
    return " checked" if value else ""


def _selected(current: str | None, value: str) -> str:
    return " selected" if current == value else ""


def _current_step(state: ApplicationPreparationState, prerequisites: ApplicationPrerequisites) -> int:
    result = evaluate_application_prep(state, prerequisites)
    if not result.destination_complete:
        return 1
    if not result.prerequisites_complete or not result.forms_complete:
        return 2
    if not result.submission_data_complete:
        return 3
    if not result.final_review_complete:
        return 4
    return 5


def _step_label(number: int, current: int, complete: bool, name: str) -> str:
    if complete:
        status = "完了"
    elif number == current:
        status = "現在"
    else:
        status = "未完了"
    return f"<li><strong>{number}. {escape(name)}</strong>　{status}</li>"


def _prerequisite_list(prerequisites: ApplicationPrerequisites) -> str:
    rows = (
        ("会社・PMS基本情報", prerequisites.company_profile_ready),
        ("PMS文書", prerequisites.pms_documents_ready),
        ("採用管理策の運用記録", prerequisites.operations_ready),
        ("内部監査・是正・マネジメントレビュー", prerequisites.pms_review_ready),
    )
    return "".join(
        f"<li>{escape(name)}：<strong>{'準備完了' if ready else '未完了'}</strong></li>"
        for name, ready in rows
    )


def _destination_form(state: ApplicationPreparationState) -> str:
    jipdec_value = ""
    if state.uses_jipdec_forms is True:
        jipdec_value = "yes"
    elif state.uses_jipdec_forms is False:
        jipdec_value = "no"

    return f"""
    <form method="post" action="/application-prep/destination">
      <p><label>申請先の審査機関<br>
        <input name="examining_body_name" value="{escape(state.examining_body_name or '')}" required
               placeholder="例：JIPDEC または指定審査機関名" style="width:30em;max-width:100%;">
      </label></p>
      <p><label>申請方法<br>
        <select name="application_method" required>
          <option value="">選択してください</option>
          <option value="online"{_selected(state.application_method, 'online')}>オンライン</option>
          <option value="mail"{_selected(state.application_method, 'mail')}>郵送・持参</option>
          <option value="other"{_selected(state.application_method, 'other')}>その他（審査機関指定）</option>
        </select>
      </label></p>
      <p><label>使用する新規申請様式<br>
        <select name="uses_jipdec_forms" required>
          <option value="">選択してください</option>
          <option value="yes"{' selected' if jipdec_value == 'yes' else ''}>JIPDECの新規申請様式</option>
          <option value="no"{' selected' if jipdec_value == 'no' else ''}>JIPDEC以外の指定審査機関の様式</option>
        </select>
      </label></p>
      <p class="hint">申請先は業種・本社所在地等に応じて確認し、審査機関が確定してから記録してください。</p>
      <button type="submit">申請先・方法を記録</button>
    </form>
    """


def _forms_form(state: ApplicationPreparationState) -> str:
    if state.uses_jipdec_forms is True:
        return f"""
        <p>JIPDECの新規申請について、現在の申請様式4〜8を個別に確認します。</p>
        <form method="post" action="/application-prep/forms">
          <label><input type="checkbox" name="business_overview_prepared" value="yes"{_checked(state.business_overview_prepared)}> 申請様式4：個人情報を取扱う業務の概要</label><br>
          <label><input type="checkbox" name="office_list_prepared" value="yes"{_checked(state.office_list_prepared)}> 申請様式5：すべての事業所の所在地及び業務内容</label><br>
          <label><input type="checkbox" name="pms_document_list_prepared" value="yes"{_checked(state.pms_document_list_prepared)}> 申請様式6：PMS文書の一覧</label><br>
          <label><input type="checkbox" name="education_summary_prepared" value="yes"{_checked(state.education_summary_prepared)}> 申請様式7：教育実施サマリー</label><br>
          <label><input type="checkbox" name="audit_mr_summary_prepared" value="yes"{_checked(state.audit_mr_summary_prepared)}> 申請様式8：内部監査・マネジメントレビュー実施サマリー</label>
          <p><button type="submit">申請様式の準備状況を記録</button></p>
        </form>
        """
    return f"""
    <p>JIPDEC以外の指定審査機関は、各審査機関が指定する申請方法・申請様式を確認してください。</p>
    <form method="post" action="/application-prep/forms">
      <label><input type="checkbox" name="other_form_set_prepared" value="yes"{_checked(state.other_form_set_prepared)}> 申請先が指定する新規申請様式一式を確認・準備した</label>
      <p><button type="submit">申請様式の準備状況を記録</button></p>
    </form>
    """


def _submission_data_form(state: ApplicationPreparationState) -> str:
    online_row = ""
    if state.application_method == "online":
        online_row = f"""
        <p><label><input type="checkbox" name="online_account_ready" value="yes"{_checked(state.online_account_ready is True)}> オンライン申請に使用するアカウントを準備した</label></p>
        """
    return f"""
    <form method="post" action="/application-prep/submission-data">
      <p><label><input type="checkbox" name="pms_document_bundle_prepared" value="yes"{_checked(state.pms_document_bundle_prepared)}> 提出するPMS文書一式の電子データを準備した</label></p>
      {online_row}
      <button type="submit">提出データの準備状況を記録</button>
    </form>
    """


def _final_review_form(state: ApplicationPreparationState) -> str:
    profile = company_profile.get_state()
    reviewer = (
        state.final_reviewed_by
        or profile.application_contact_name
        or profile.privacy_manager_name
        or "Pマーク担当者"
    )
    return f"""
    <form method="post" action="/application-prep/final-review">
      <p><label>最終確認者<br><input name="final_reviewed_by" value="{escape(reviewer)}" required></label></p>
      <p><label>最終確認日<br><input type="date" name="final_reviewed_at" value="{escape(state.final_reviewed_at or '')}" required></label></p>
      <p><label><input type="checkbox" name="submission_ready_confirmed" value="yes"{_checked(state.submission_ready_confirmed)} required> 申請先・申請様式・PMS文書・運用記録を確認し、提出準備が整っていることを確認した</label></p>
      <button type="submit">最終確認を記録</button>
    </form>
    """


def render_application_prep_page(
    state: ApplicationPreparationState,
    prerequisites: ApplicationPrerequisites,
    *,
    flash: str | None = None,
) -> str:
    result = evaluate_application_prep(state, prerequisites)
    current = _current_step(state, prerequisites)

    completed = [
        result.destination_complete,
        result.prerequisites_complete and result.forms_complete,
        result.submission_data_complete,
        result.final_review_complete,
    ]
    progress = sum(1 for value in completed if value)

    step_names = ("申請先・方法", "申請書類・前提確認", "提出データ・アカウント", "最終確認")
    steps_html = "".join(
        _step_label(index, current, completed[index - 1], name)
        for index, name in enumerate(step_names, start=1)
    )

    if current == 1:
        action_html = _destination_form(state)
    elif current == 2:
        action_html = f"""
        <h3>既存PMSから確認できる前提</h3>
        <ul>{_prerequisite_list(prerequisites)}</ul>
        <p class="hint">未完了項目は元の管理画面で記録を整えてください。ここで同じ内容を再入力する必要はありません。</p>
        <h3>申請様式の準備</h3>
        {_forms_form(state)}
        """
    elif current == 3:
        action_html = _submission_data_form(state)
    elif current == 4:
        action_html = _final_review_form(state)
    else:
        action_html = """
        <div class="complete-box">
          <h3>申請提出前の準備確認が完了しました</h3>
          <p>この画面は付与適格性を保証するものではありません。実際の提出時は、選択した審査機関の最新案内・様式を確認してください。</p>
        </div>
        """

    issue_items = "".join(f"<li>{escape(issue.message)}</li>" for issue in result.issues)
    flash_html = f'<p class="flash">{escape(flash)}</p>' if flash else ""

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <title>Pマーク申請準備</title>
  <style>
    body {{ font-family:sans-serif; margin:2rem; line-height:1.6; max-width:1000px; }}
    .workflow {{ border:1px solid #bbb; padding:1rem; border-radius:4px; }}
    .workflow ul {{ list-style:none; padding:0; }}
    .workflow li {{ margin:.35rem 0; }}
    .current-box {{ background:#fff8ef; border-left:4px solid #d9822b; padding:1rem; margin:1rem 0; }}
    .complete-box {{ background:#eefaf0; border-left:4px solid #0a7a0a; padding:1rem; }}
    .issues {{ background:#fff4f4; padding:1rem; }}
    .hint {{ color:#666; font-size:.9em; }}
    .flash {{ background:#eef5ff; padding:.75rem 1rem; }}
    input, select {{ padding:.35rem; margin-top:.25rem; }}
  </style>
</head>
<body>
  <p><a href="/">← トップへ戻る</a></p>
  <h1>Pマーク申請準備</h1>
  <p>申請先の確定から提出前の最終確認までを、既存のPMS記録とつなげて確認します。</p>
  {flash_html}

  <section class="workflow">
    <h2>申請準備の全体工程</h2>
    <p><strong>全体進捗：{progress} / 4 工程 完了</strong></p>
    <ul>{steps_html}</ul>
    <p><strong>現在地：{'全工程完了' if current == 5 else f'{current}. {step_names[current - 1]}'}</strong></p>
  </section>

  <section class="current-box">
    <h2>今やること　{0 if current == 5 else 1}件</h2>
    {action_html}
  </section>

  <section>
    <h2>現在の不足</h2>
    {'<p>不足はありません。</p>' if not issue_items else f'<ul class="issues">{issue_items}</ul>'}
  </section>
</body>
</html>
"""
