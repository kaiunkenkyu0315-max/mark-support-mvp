"""MVP開発中の手動確認を短縮するための開発用プリセット。

本番業務ロジックではなく、サーバー再起動で失われるインメモリ状態を
検証しやすい状態へ一括設定するためだけに使用する。
"""

from __future__ import annotations

from app import (
    access_control_demo_state,
    annual_cycle_demo_state,
    application_prep_demo_state,
    company_profile,
    demo_state,
    intake_demo_state,
    paper_demo_state,
    pms_review_demo_state,
    vendor_demo_state,
)
from app.intake_schemas import QuestionnaireAnswers


def load_operational_review_preset() -> None:
    """初期設定完了＋主要運用機能の検証初期状態を一括で作る。"""

    company_profile.update_profile(
        name="株式会社サンプル",
        name_kana="カブシキガイシャサンプル",
        corporate_number="1234567890123",
        registered_address="愛知県名古屋市中区サンプル1-2-3",
        representative_title="代表取締役",
        representative_name="山田 太郎",
        employee_count=50,
        fiscal_year=2026,
        privacy_manager_name="鈴木 花子",
        privacy_manager_department_role="総務部・個人情報保護管理者",
        audit_manager_name="佐藤 次郎",
        audit_manager_department_role="管理部・個人情報保護監査責任者",
        application_contact_name="山田 花子",
        application_contact_department_role="総務部・Pマーク担当",
        application_contact_email="pmark@example.jp",
    )

    intake_demo_state.reset_state()
    intake_demo_state.submit_answers(
        QuestionnaireAnswers(
            has_employees=True,
            recruits_people=True,
            manages_customer_contacts=True,
            receives_inquiries=True,
            outsources_personal_data_processing=True,
            uses_external_cloud_services=True,
            stores_personal_data_on_paper=True,
            allows_remote_access=True,
        )
    )

    state = intake_demo_state.get_state()
    intake_demo_state.decide_candidates({candidate.id: True for candidate in state.candidates})

    for candidate in intake_demo_state.get_state().candidates:
        intake_demo_state.update_ledger_entry(
            candidate.id,
            acquisition_method="本人または業務上の関係者から取得",
            storage_method="データ・紙媒体",
            storage_location="社内業務システム・施錠保管庫",
            outsourced=False,
            third_party_provided=False,
            retention_period="利用目的達成後5年間",
            disposal_method="復元できない方法で削除・廃棄",
            responsible_role="Pマーク担当者",
        )

    state = intake_demo_state.get_state()
    intake_demo_state.decide_risks({risk.id: True for risk in state.risks})
    state = intake_demo_state.get_state()
    intake_demo_state.update_risk_evaluations(
        {
            risk.id: (
                risk.impact if risk.impact is not None else 2,
                risk.likelihood if risk.likelihood is not None else 2,
            )
            for risk in state.risks
        }
    )

    for suggestion in list(intake_demo_state.get_state().control_suggestions):
        intake_demo_state.adopt_control(suggestion.control_id)

    demo_state.reset_state()
    vendor_demo_state.reset_state()
    access_control_demo_state.reset_state()
    paper_demo_state.reset_state()
    pms_review_demo_state.reset_state()
    application_prep_demo_state.reset_state()
    annual_cycle_demo_state.reset_state()


def load_annual_pms_preset() -> None:
    """年間PMS運用を年度計画から検証できる状態を作る。"""

    load_operational_review_preset()
    annual_cycle_demo_state.reset_state()
    pms_review_demo_state.reset_state()


def load_pms_review_preset() -> None:
    """初期設定＋4管理策運用を完了し、内部監査からすぐ検証できる状態を作る。"""

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

    pms_review_demo_state.reset_state()
    application_prep_demo_state.reset_state()


def load_application_prep_preset() -> None:
    """PMSレビューまで完了し、申請先確認からすぐ検証できる状態を作る。"""

    load_pms_review_preset()

    pms_review_demo_state.record_internal_audit(
        audit_date="2026-08-01",
        purpose="PMSの適合性・有効性確認",
        criteria="PMS規程・Pマーク構築運用指針",
        scope="全社PMS",
        auditor_name="佐藤 次郎",
        auditor_independence_confirmed=True,
        result_summary="重大な不適合なし",
        nonconformity_count=0,
        report_date="2026-08-02",
        reported_to_top_management=True,
        evidence_name="内部監査報告書",
    )
    pms_review_demo_state.record_management_review(
        review_date="2026-08-05",
        top_management_name="山田 太郎",
        input_summary="内部監査、リスク、教育、委託先、アクセス権限、紙媒体の運用状況を確認",
        decision_summary="現行PMSを維持し、継続的に改善する",
        changes_needed=False,
        improvement_actions="",
        evidence_name="マネジメントレビュー議事録",
    )

    application_prep_demo_state.reset_state()
