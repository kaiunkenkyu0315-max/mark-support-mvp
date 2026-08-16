"""取得計画と同じ計画モデルを、年間PMS運用にも再利用できることを検証する。"""

from app import (
    access_control_demo_state,
    company_profile,
    demo_state,
    intake_demo_state,
    paper_demo_state,
    vendor_demo_state,
)
from app.access_control import evaluate_access_control
from app.annual_pms_plan import build_annual_pms_plan
from app.dashboard import build_dashboard_data
from app.dev_preset import load_operational_review_preset
from app.document_routes import get_current_documents
from app.education import evaluate_training
from app.paper import evaluate_paper_management
from app.plan_view import render_plan
from app.setup_progress import get_effective_setup_status
from app.vendors import evaluate_vendors


def _reset_all() -> None:
    company_profile.reset_state()
    intake_demo_state.reset_state()
    demo_state.reset_state()
    vendor_demo_state.reset_state()
    access_control_demo_state.reset_state()
    paper_demo_state.reset_state()


def _dashboard_data():
    intake_state = intake_demo_state.get_state()
    education_state = demo_state.get_state()
    vendor_state = vendor_demo_state.get_state()
    access_state = access_control_demo_state.get_state()
    paper_state = paper_demo_state.get_state()

    return build_dashboard_data(
        setup_status=get_effective_setup_status(intake_state),
        candidates=intake_state.candidates,
        risks=intake_state.risks,
        control_suggestions=intake_state.control_suggestions,
        documents=get_current_documents(),
        education_result=evaluate_training(
            education_state.employees,
            education_state.control,
            education_state.plan,
            education_state.records,
        ),
        vendor_result=evaluate_vendors(
            vendor_state.vendors,
            vendor_state.control,
            vendor_state.assessments,
            vendor_state.contracts,
        ),
        access_control_result=evaluate_access_control(
            access_state.accounts,
            access_state.control,
            access_state.cycle,
        ),
        paper_result=evaluate_paper_management(paper_state.control, paper_state.status),
    )


def test_annual_plan_uses_same_forest_to_tree_structure_for_current_operations():
    _reset_all()
    load_operational_review_preset()

    plan = build_annual_pms_plan(_dashboard_data())
    html = render_plan(plan, css_class="annual-pms-plan")
    _reset_all()

    assert plan.title == "年間PMS運用計画"
    assert plan.completed_count == 0
    assert plan.tracked_total == 4
    assert plan.current_text == "3. 教育"
    assert next(step for step in plan.steps if step.number == 3).current is True
    assert next(step for step in plan.steps if step.number == 1).status == "後続実装"
    assert next(step for step in plan.steps if step.number == 7).status == "後続実装"
    assert "年間PMS運用計画" in html
    assert "現MVP運用範囲進捗：0 / 4 工程 完了" in html
    assert "現在地：3. 教育" in html


def test_annual_plan_moves_to_vendor_after_education_is_completed():
    _reset_all()
    load_operational_review_preset()

    demo_state.register_material_evidence()
    demo_state.complete_all_trainings()
    demo_state.register_missing_comprehension()
    demo_state.approve_plan()

    plan = build_annual_pms_plan(_dashboard_data())
    _reset_all()

    assert plan.completed_count == 1
    assert plan.tracked_total == 4
    assert plan.current_text == "4. 委託先評価"
    assert next(step for step in plan.steps if step.number == 3).status == "完了"
    assert next(step for step in plan.steps if step.number == 4).current is True


def test_annual_plan_keeps_unimplemented_audit_after_all_current_operations_complete():
    _reset_all()
    load_operational_review_preset()

    demo_state.register_material_evidence()
    demo_state.complete_all_trainings()
    demo_state.register_missing_comprehension()
    demo_state.approve_plan()

    vendor_demo_state.complete_missing_initial_assessments()
    vendor_demo_state.confirm_missing_contracts()
    vendor_demo_state.complete_missing_periodic_assessments()

    access_control_demo_state.complete_missing_account_reviews()
    access_control_demo_state.remove_unnecessary_accounts()
    access_control_demo_state.complete_review_cycle()
    access_control_demo_state.approve_review_cycle()

    paper_demo_state.confirm_storage_lock()
    paper_demo_state.define_take_out_rule()
    paper_demo_state.confirm_disposal()
    paper_demo_state.approve_status()

    plan = build_annual_pms_plan(_dashboard_data())
    _reset_all()

    assert plan.completed_count == 4
    assert plan.tracked_total == 4
    assert plan.current_text == "現MVP運用範囲完了（次の後続工程：7. 内部監査）"
    assert next(step for step in plan.steps if step.number == 7).status == "後続実装"
    assert next(step for step in plan.steps if step.number == 8).status == "後続実装"
    assert next(step for step in plan.steps if step.number == 9).status == "後続実装"
