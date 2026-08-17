"""既存の取得計画へ申請準備工程を追加する薄い拡張層。

内部監査・マネジメントレビューまでの既存ロジックは app.dashboard_plan を正本とし、
ここでは申請準備（6）と、その先の外部工程（7）だけを追加する。
"""

from __future__ import annotations

from dataclasses import replace

from app.application_prep_schemas import ApplicationPrepEvaluationResult
from app.dashboard import DashboardData
from app.dashboard_plan import build_acquisition_plan
from app.plan_models import Plan, PlanStep
from app.plan_view import render_plan
from app.pms_review_schemas import PmsReviewEvaluationResult


def build_acquisition_plan_with_application(
    data: DashboardData,
    review_result: PmsReviewEvaluationResult,
    application_result: ApplicationPrepEvaluationResult,
) -> Plan:
    base = build_acquisition_plan(data, review_result)

    base_steps = [step for step in base.steps if step.number != 6]
    prior_complete = base.completed_count == base.tracked_total
    app_complete = application_result.complete
    app_current = prior_complete and not app_complete

    if app_current:
        base_steps = [replace(step, current=False) for step in base_steps]

    base_steps.append(
        PlanStep(
            number=6,
            name="申請準備",
            description="申請先・申請様式・PMS文書一式・アカウント・最終確認を整え、提出前の準備状態を確認します。",
            status=("完了" if app_complete else "対応中") if prior_complete else "レビュー後",
            status_kind=("complete" if app_complete else "current") if prior_complete else "pending",
            link="/application-prep",
            implemented=True,
            current=app_current,
        )
    )
    base_steps.append(
        PlanStep(
            number=7,
            name="申請・審査",
            description="選択した審査機関へ実際に申請し、形式審査・文書審査・現地審査等の外部手続へ進みます。",
            status="外部工程",
            status_kind="future",
            implemented=False,
        )
    )

    if not prior_complete:
        current_text = base.current_text
    elif not app_complete:
        current_text = "6. 申請準備"
    else:
        current_text = "MVP実装範囲完了（次の外部工程：7. 申請・審査）"

    return Plan(
        title=base.title,
        description=base.description,
        steps=base_steps,
        completed_count=base.completed_count + (1 if app_complete else 0),
        tracked_total=base.tracked_total + 1,
        current_text=current_text,
        progress_label=base.progress_label,
        footer_note="申請準備完了は付与適格性や取得完了を意味しません。実際の申請・審査は選択した審査機関の手続に従います。",
    )


def _inject_application_preset_shortcut(html: str) -> str:
    """既存の開発ショートカット末尾へ、申請準備用プリセットを追加する。"""

    if 'action="/dev/preset/application-prep"' in html:
        return html
    marker = "</form>\n    </section>\n</body>"
    addition = """</form>
      <form method="post" action="/dev/preset/application-prep" style="margin-top:0.75rem;">
        <button type="submit">申請準備検証用プリセットをセット</button>
        <span> — PMSレビューまで完了し、申請先・方法の確認から開始</span>
      </form>
    </section>
</body>"""
    if marker in html:
        return html.replace(marker, addition, 1)
    return html


def enhance_dashboard_with_application_plan(
    html: str,
    data: DashboardData,
    review_result: PmsReviewEvaluationResult,
    application_result: ApplicationPrepEvaluationResult,
) -> str:
    plan_html = render_plan(
        build_acquisition_plan_with_application(data, review_result, application_result),
        css_class="acquisition-plan",
    )
    marker = '<section class="todo-section">'
    if marker in html:
        html = html.replace(marker, plan_html + marker, 1)
    else:
        html = html.replace("</p>", "</p>" + plan_html, 1)
    return _inject_application_preset_shortcut(html)
