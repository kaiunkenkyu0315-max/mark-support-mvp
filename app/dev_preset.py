"""MVP開発中の手動確認を短縮するための開発用プリセット。

本番業務ロジックではなく、サーバー再起動で失われるインメモリ状態を
検証しやすい状態へ一括設定するためだけに使用する。
"""

from __future__ import annotations

from app import (
    access_control_demo_state,
    company_profile,
    demo_state,
    intake_demo_state,
    paper_demo_state,
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

    # リスク確定後に提示されたものも含め、現在提示されている管理策をすべて採用する。
    for suggestion in list(intake_demo_state.get_state().control_suggestions):
        intake_demo_state.adopt_control(suggestion.control_id)

    # 運用側は「不足を残したデモ初期状態」に戻し、各管理機能をすぐ確認できるようにする。
    demo_state.reset_state()
    vendor_demo_state.reset_state()
    access_control_demo_state.reset_state()
    paper_demo_state.reset_state()
