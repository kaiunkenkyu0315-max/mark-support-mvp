"""年間PMS運用の森→木UI。"""

from __future__ import annotations

from html import escape

from app import annual_cycle_demo_state, company_profile
from app.annual_pms_context import AnnualPmsContext
from app.annual_pms_plan import build_annual_pms_plan
from app.plan_view import render_plan


def _value(value: str | None) -> str:
    return escape(value or "")


def _selected(current: str | None, value: str) -> str:
    return " selected" if current == value else ""


def _annual_plan_form() -> str:
    profile = company_profile.get_state()
    record = annual_cycle_demo_state.get_state().plan
    coordinator = (
        record.coordinator_name
        or profile.application_contact_name
        or profile.privacy_manager_name
        or "Pマーク担当者"
    )
    privacy_manager = record.privacy_manager_name or profile.privacy_manager_name or "個人情報保護管理者"
    audit_manager = record.audit_manager_name or profile.audit_manager_name or "個人情報保護監査責任者"
    top_manager = record.top_management_name or profile.representative_name or "代表者"
    objectives = record.objectives or "PMSを年間を通じて有効に運用し、個人情報保護上のリスクを適切に管理する"
    schedule = record.schedule_summary or (
        "年度開始時に台帳・リスク・管理策を見直し、年度内に教育・委託先評価・権限棚卸し・"
        "紙媒体管理を実施し、内部監査とマネジメントレビューで次年度へつなげる"
    )
    approver = record.approved_by or top_manager

    return f"""
    <section class="action-card">
      <h2>今やること：1. 年度運用計画・体制確認</h2>
      <p>年度の担当体制・目標・主要な実施予定を記録します。会社基本情報から使える項目は初期値にしています。</p>
      <form method="post" action="/annual-pms/annual-plan">
        <label>対象年度 <input type="number" name="fiscal_year" value="{record.fiscal_year or profile.fiscal_year}" required></label><br><br>
        <label>計画作成日 <input type="date" name="planned_on" value="{_value(record.planned_on)}" required></label><br><br>
        <label>年間運用担当者 <input type="text" name="coordinator_name" value="{escape(coordinator)}" required></label><br><br>
        <label>個人情報保護管理者 <input type="text" name="privacy_manager_name" value="{escape(privacy_manager)}" required></label><br><br>
        <label>監査責任者 <input type="text" name="audit_manager_name" value="{escape(audit_manager)}" required></label><br><br>
        <label>トップマネジメント <input type="text" name="top_management_name" value="{escape(top_manager)}" required></label><br><br>
        <label>年度のPMS運用目標<br><textarea name="objectives" rows="3" cols="80" required>{escape(objectives)}</textarea></label><br><br>
        <label>主要な実施予定<br><textarea name="schedule_summary" rows="4" cols="80" required>{escape(schedule)}</textarea></label><br><br>
        <label>承認者 <input type="text" name="approved_by" value="{escape(approver)}" required></label><br><br>
        <label>承認日 <input type="date" name="approved_at" value="{_value(record.approved_at)}" required></label><br><br>
        <label>証跡名 <input type="text" name="evidence_name" value="{_value(record.evidence_name) or '年間PMS運用計画書'}" required></label><br><br>
        <button type="submit">年度運用計画を保存して次へ</button>
      </form>
    </section>
    """


def _review_select(name: str, label: str, current: str | None) -> str:
    return f"""
      <label>{escape(label)}
        <select name="{escape(name)}" required>
          <option value="">選択してください</option>
          <option value="no_change"{_selected(current, 'no_change')}>変更なし</option>
          <option value="changed"{_selected(current, 'changed')}>変更あり</option>
        </select>
      </label><br><br>
    """


def _inventory_risk_review_form(context: AnnualPmsContext) -> str:
    profile = company_profile.get_state()
    record = annual_cycle_demo_state.get_state().inventory_risk_review
    reviewer = record.reviewed_by or profile.application_contact_name or profile.privacy_manager_name or "Pマーク担当者"
    approver = record.approved_by or profile.privacy_manager_name or "個人情報保護管理者"
    basis = record.review_basis or (
        "業務内容、組織・人員、利用システム、委託先、個人情報管理台帳、リスク評価、採用管理策を確認"
    )
    return f"""
    <section class="action-card">
      <h2>今やること：2. 個人情報台帳・リスク見直し</h2>
      <p>現在の正本から、確認対象は自動集計します。変更有無は担当者が明示判断してください。</p>
      <ul>
        <li>確認済み個人情報：<strong>{context.confirmed_personal_information_count}件</strong></li>
        <li>確認済みリスク：<strong>{context.confirmed_risk_count}件</strong></li>
        <li>採用済み管理策：<strong>{context.adopted_control_count}件</strong></li>
      </ul>
      <p><a href="/setup">台帳・リスク・管理策の正本を確認する</a></p>
      <form method="post" action="/annual-pms/inventory-risk-review">
        <label>見直し日 <input type="date" name="reviewed_on" value="{_value(record.reviewed_on)}" required></label><br><br>
        <label>見直し担当者 <input type="text" name="reviewed_by" value="{escape(reviewer)}" required></label><br><br>
        <label>確認した範囲・根拠<br><textarea name="review_basis" rows="3" cols="80" required>{escape(basis)}</textarea></label><br><br>
        {_review_select('business_change_result', '業務・組織・システム・委託先等の変更', record.business_change_result)}
        {_review_select('personal_information_result', '個人情報台帳の変更', record.personal_information_result)}
        {_review_select('risk_result', 'リスク評価の変更', record.risk_result)}
        {_review_select('control_result', '管理策の変更', record.control_result)}
        <div class="change-box">
          <strong>「変更あり」が1つでもある場合</strong>
          <p>先に既存の初期設定側で正本を更新し、反映した内容と完了日をここへ記録します。</p>
          <label>変更反映内容<br><textarea name="change_action_summary" rows="3" cols="80">{_value(record.change_action_summary)}</textarea></label><br><br>
          <label>変更反映完了日 <input type="date" name="change_action_completed_on" value="{_value(record.change_action_completed_on)}"></label>
        </div><br>
        <label>承認者 <input type="text" name="approved_by" value="{escape(approver)}" required></label><br><br>
        <label>承認日 <input type="date" name="approved_at" value="{_value(record.approved_at)}" required></label><br><br>
        <label>証跡名 <input type="text" name="evidence_name" value="{_value(record.evidence_name) or '個人情報・リスク年次見直し記録'}" required></label><br><br>
        <button type="submit">年次見直し記録を保存して次へ</button>
      </form>
    </section>
    """


def _next_existing_operation(context: AnnualPmsContext) -> str:
    plan = build_annual_pms_plan(
        context.dashboard_data,
        context.pms_review_result,
        context.annual_cycle_result,
    )
    current = next((step for step in plan.steps if step.current), None)
    if current and current.number > 2 and current.link and current.link != "/annual-pms":
        return f"""
        <section class="action-card complete-box">
          <h2>年度開始の2工程が完了しました</h2>
          <p>次の現在地は <strong>{current.number}. {escape(current.name)}</strong> です。</p>
          <p><a href="{escape(current.link)}">次の工程へ進む</a></p>
        </section>
        """
    return """


def render_annual_pms_page(context: AnnualPmsContext, *, flash: str | None = None) -> str:
    plan = build_annual_pms_plan(
        context.dashboard_data,
        context.pms_review_result,
        context.annual_cycle_result,
    )
    if not context.annual_cycle_result.plan_complete:
        action = _annual_plan_form()
    elif not context.annual_cycle_result.inventory_risk_review_complete:
        action = _inventory_risk_review_form(context)
    else:
        action = _next_existing_operation(context)

    issue = next(iter(context.annual_cycle_result.issues), None)
    issue_html = f'<p class="issue">{escape(issue.message)}</p>' if issue else ""
    flash_html = f'<p class="flash">{escape(flash)}</p>' if flash else ""
    plan_html = render_plan(plan, css_class="annual-pms-plan")

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <title>年間PMS運用</title>
  <style>
    body {{ font-family:sans-serif; margin:2rem; line-height:1.6; max-width:1000px; }}
    .action-card {{ border:1px solid #ccc; padding:16px; margin:20px 0; border-radius:4px; }}
    .change-box {{ background:#f7f7f7; padding:12px; }}
    .issue {{ background:#fff8ef; border-left:4px solid #d9822b; padding:10px; }}
    .flash {{ background:#eef6ff; border-left:4px solid #3973ac; padding:10px; }}
    .complete-box {{ background:#eefaf0; }}
    textarea {{ max-width:100%; }}
  </style>
</head>
<body>
  <h1>年間PMS運用</h1>
  <p><a href="/">トップへ戻る</a></p>
  <p>取得後のPMSを、年度開始からマネジメントレビューまで同じ計画表で運用します。</p>
  {plan_html}
  {flash_html}
  {issue_html}
  {action}
</body>
</html>
"""
