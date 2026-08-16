"""内部監査→是正→マネジメントレビューを森→木で表示する画面。"""

from __future__ import annotations

from html import escape

from app import company_profile
from app.pms_review import evaluate_pms_review
from app.pms_review_schemas import PmsReviewEvaluationResult, PmsReviewState


def _value(value: str | None) -> str:
    return escape(value or "")


def _current_step(result: PmsReviewEvaluationResult) -> int | None:
    if not result.audit_complete:
        return 1
    if result.corrective_required and not result.corrective_complete:
        return 2
    if not result.management_review_complete:
        return 3
    return None


def _step_statuses(result: PmsReviewEvaluationResult) -> dict[int, tuple[str, bool]]:
    audit_done = result.audit_complete
    correction_done = result.audit_complete and (
        not result.corrective_required or result.corrective_complete
    )
    review_done = result.management_review_complete
    correction_label = "完了" if result.corrective_complete and result.corrective_required else "対象なし"
    if not audit_done:
        correction_label = "監査結果待ち"
    elif result.corrective_required and not result.corrective_complete:
        correction_label = "対応中"
    return {
        1: ("完了" if audit_done else "未完了", audit_done),
        2: (correction_label, correction_done),
        3: ("完了" if review_done else "未完了", review_done),
    }


def _render_overview(result: PmsReviewEvaluationResult) -> str:
    names = {1: "内部監査", 2: "不適合・是正処置", 3: "マネジメントレビュー"}
    statuses = _step_statuses(result)
    current = _current_step(result)
    completed = sum(1 for _, done in statuses.values() if done)
    rows = []
    for step in range(1, 4):
        label, _done = statuses[step]
        marker = " ← 現在" if current == step else ""
        rows.append(f"<li><strong>{step}. {names[step]}</strong>　{label}{marker}</li>")
    current_text = "全工程完了" if current is None else f"{current}. {names[current]}"
    return f"""
    <section style="border:1px solid #ccc;padding:16px;margin:18px 0;">
      <h2 style="margin-top:0;">PMS評価・改善の全体工程</h2>
      <p>内部監査でPMSの適合性・有効性を確認し、不適合があれば是正したうえで、トップマネジメントが見直します。</p>
      <p><strong>全体進捗：{completed} / 3 工程</strong></p>
      <ol style="line-height:1.9;">{''.join(rows)}</ol>
      <p><strong>現在地：{current_text}</strong></p>
    </section>
    """


def _render_todo(result: PmsReviewEvaluationResult) -> str:
    current = _current_step(result)
    if current is None:
        text = "対応が必要な項目はありません。PMS評価・改善の記録が整っています。"
    elif current == 1:
        text = "内部監査の計画・実施・結果報告を記録してください。"
    elif current == 2:
        text = "監査で確認された不適合について、原因分析・是正処置・有効性確認を記録してください。"
    else:
        text = "監査・是正等を入力情報として、トップマネジメントのレビュー結果を記録してください。"
    count = 0 if current is None else 1
    return f"<section><h2>今やること　{count}件</h2><p><strong>{escape(text)}</strong></p></section>"


def _render_audit_form(state: PmsReviewState) -> str:
    profile = company_profile.get_state()
    audit = state.audit
    purpose = audit.purpose or "PMSが内部規程及びPマーク構築・運用指針に適合し、有効に実施・維持されていることを確認する"
    criteria = audit.criteria or "社内PMS規程、Pマーク構築・運用指針 JIS Q 15001:2023準拠 ver1.0"
    scope = audit.scope or "個人情報を取り扱う全業務、関係従業者、情報システム及び関連するPMS運用"
    auditor = audit.auditor_name or profile.audit_manager_name or "個人情報保護監査責任者"
    return f"""
    <section style="border:1px solid #ddd;padding:14px;margin:18px 0;">
      <h2>1. 内部監査記録</h2>
      <p>監査目的・基準・範囲、監査員の客観性、結果とトップマネジメントへの報告を記録します。</p>
      <form method="post" action="/pms-review/audit">
        <label>監査実施日 <input type="date" name="audit_date" value="{_value(audit.audit_date)}" required></label><br><br>
        <label>監査目的<br><textarea name="purpose" rows="2" cols="80" required>{escape(purpose)}</textarea></label><br><br>
        <label>監査基準<br><textarea name="criteria" rows="2" cols="80" required>{escape(criteria)}</textarea></label><br><br>
        <label>監査範囲<br><textarea name="scope" rows="2" cols="80" required>{escape(scope)}</textarea></label><br><br>
        <label>監査責任者・監査員 <input type="text" name="auditor_name" value="{escape(auditor)}" required></label><br><br>
        <label><input type="checkbox" name="auditor_independence_confirmed" value="yes" required> 監査対象業務からの客観性・公平性を確認した</label><br><br>
        <label>監査結果概要<br><textarea name="result_summary" rows="3" cols="80" required>{_value(audit.result_summary)}</textarea></label><br><br>
        <label>不適合件数 <input type="number" name="nonconformity_count" min="0" value="{'' if audit.nonconformity_count is None else audit.nonconformity_count}" required></label><br><br>
        <label>報告日 <input type="date" name="report_date" value="{_value(audit.report_date)}" required></label><br><br>
        <label><input type="checkbox" name="reported_to_top_management" value="yes" required> 監査結果を管理層・トップマネジメントへ報告した</label><br><br>
        <label>証跡名 <input type="text" name="evidence_name" value="{_value(audit.evidence_name) or '内部監査報告書'}" required></label><br><br>
        <button type="submit">内部監査記録を保存して次へ</button>
      </form>
    </section>
    """


def _render_corrective_form(state: PmsReviewState) -> str:
    profile = company_profile.get_state()
    record = state.corrective_action
    approver = record.approved_by or profile.representative_name or "トップマネジメント"
    return f"""
    <section style="border:1px solid #ddd;padding:14px;margin:18px 0;">
      <h2>2. 不適合・是正処置記録</h2>
      <p>不適合の修正だけで終わらせず、原因を特定し、再発防止の処置と有効性確認まで記録します。</p>
      <form method="post" action="/pms-review/corrective-action">
        <label>不適合の内容<br><textarea name="finding_summary" rows="2" cols="80" required>{_value(record.finding_summary)}</textarea></label><br><br>
        <label>直ちに行った修正・影響への対応<br><textarea name="immediate_action" rows="2" cols="80" required>{_value(record.immediate_action)}</textarea></label><br><br>
        <label>原因分析<br><textarea name="root_cause" rows="2" cols="80" required>{_value(record.root_cause)}</textarea></label><br><br>
        <label>是正処置<br><textarea name="corrective_action" rows="2" cols="80" required>{_value(record.corrective_action)}</textarea></label><br><br>
        <label>実施日 <input type="date" name="implemented_on" value="{_value(record.implemented_on)}" required></label><br><br>
        <label>有効性評価
          <select name="effectiveness_result" required>
            <option value="">選択してください</option>
            <option value="effective"{' selected' if record.effectiveness_result == 'effective' else ''}>有効</option>
            <option value="ineffective"{' selected' if record.effectiveness_result == 'ineffective' else ''}>未有効・追加対応が必要</option>
          </select>
        </label><br><br>
        <label>有効性確認日 <input type="date" name="effectiveness_checked_on" value="{_value(record.effectiveness_checked_on)}" required></label><br><br>
        <label>承認者 <input type="text" name="approved_by" value="{escape(approver)}" required></label><br><br>
        <label>承認日 <input type="date" name="approved_at" value="{_value(record.approved_at)}" required></label><br><br>
        <label>証跡名 <input type="text" name="evidence_name" value="{_value(record.evidence_name) or '是正処置記録'}" required></label><br><br>
        <button type="submit">是正処置記録を保存して次へ</button>
      </form>
    </section>
    """


def _review_input_default(state: PmsReviewState) -> str:
    audit = state.audit
    correction = state.corrective_action
    correction_text = "不適合なし" if (audit.nonconformity_count or 0) == 0 else (
        f"不適合{audit.nonconformity_count}件。是正処置の有効性：{correction.effectiveness_result or '未確認'}"
    )
    return (
        f"内部監査：{audit.result_summary or '記録参照'}\n"
        f"不適合・是正：{correction_text}\n"
        "その他の確認対象：監視・測定結果、個人情報保護目的の達成状況、外部・内部課題の変化、"
        "利害関係者からのフィードバック、リスクアセスメント・リスク対応状況、継続的改善の機会"
    )


def _render_review_form(state: PmsReviewState) -> str:
    profile = company_profile.get_state()
    review = state.management_review
    top_manager = review.top_management_name or profile.representative_name or "代表者"
    input_summary = review.input_summary or _review_input_default(state)
    return f"""
    <section style="border:1px solid #ddd;padding:14px;margin:18px 0;">
      <h2>3. マネジメントレビュー記録</h2>
      <p>監査結果だけでなく、リスク・運用状況・利害関係者からの情報等を確認し、トップマネジメントの決定を記録します。</p>
      <form method="post" action="/pms-review/management-review">
        <label>実施日 <input type="date" name="review_date" value="{_value(review.review_date)}" required></label><br><br>
        <label>トップマネジメント <input type="text" name="top_management_name" value="{escape(top_manager)}" required></label><br><br>
        <label>レビューした入力情報<br><textarea name="input_summary" rows="6" cols="80" required>{escape(input_summary)}</textarea></label><br><br>
        <label>決定・指示事項<br><textarea name="decision_summary" rows="3" cols="80" required>{_value(review.decision_summary)}</textarea></label><br><br>
        <label>PMS変更の必要性
          <select name="changes_needed" required>
            <option value="">選択してください</option>
            <option value="no"{' selected' if review.changes_needed is False else ''}>現時点では変更不要</option>
            <option value="yes"{' selected' if review.changes_needed is True else ''}>変更・改善が必要</option>
          </select>
        </label><br><br>
        <label>改善・変更アクション（変更が必要な場合は必須）<br><textarea name="improvement_actions" rows="3" cols="80">{_value(review.improvement_actions)}</textarea></label><br><br>
        <label>証跡名 <input type="text" name="evidence_name" value="{_value(review.evidence_name) or 'マネジメントレビュー議事録'}" required></label><br><br>
        <button type="submit">マネジメントレビュー記録を保存</button>
      </form>
    </section>
    """


def _render_existing_records(state: PmsReviewState) -> str:
    return f"""
    <details style="background:#f7f7f7;padding:12px;margin:18px 0;">
      <summary><strong>登録済み記録を確認</strong></summary>
      <ul>
        <li>内部監査：{escape(state.audit.audit_date or '未登録')} / 不適合：{state.audit.nonconformity_count if state.audit.nonconformity_count is not None else '未判定'}件</li>
        <li>是正処置：{escape(state.corrective_action.effectiveness_result or '対象未確定・未登録')}</li>
        <li>マネジメントレビュー：{escape(state.management_review.review_date or '未登録')}</li>
      </ul>
    </details>
    """


def render_pms_review_page(state: PmsReviewState, flash: str | None = None) -> str:
    result = evaluate_pms_review(state)
    current = _current_step(result)
    form = ""
    if current == 1:
        form = _render_audit_form(state)
    elif current == 2:
        form = _render_corrective_form(state)
    elif current == 3:
        form = _render_review_form(state)

    flash_html = f'<p style="background:#eefaf0;padding:10px;">{escape(flash)}</p>' if flash else ""
    return f"""<!DOCTYPE html>
<html lang="ja">
<head><meta charset="utf-8"><title>PMS評価・改善</title></head>
<body style="font-family:sans-serif;margin:2rem;line-height:1.6;max-width:1000px;">
  <p><a href="/">← トップへ戻る</a></p>
  <h1>PMS評価・改善</h1>
  <p>内部監査、不適合の是正、マネジメントレビューを一つの流れで管理します。</p>
  {flash_html}
  {_render_overview(result)}
  {_render_todo(result)}
  {form}
  {_render_existing_records(state)}
</body>
</html>
"""
