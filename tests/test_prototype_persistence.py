import sqlite3

from app import company_profile, intake_demo_state
from app.intake_schemas import QuestionnaireAnswers
from app.prototype_persistence import (
    SQLiteStateStore,
    apply_state_snapshot,
    capture_current_state,
    restore_current_state,
    save_current_state,
)


def test_sqlite_round_trip_restores_all_registered_prototype_state(tmp_path):
    baseline = capture_current_state()
    db_path = tmp_path / "nested" / "prototype.sqlite3"
    store = SQLiteStateStore(db_path)

    try:
        company_profile.update_profile(
            name="株式会社永続化テスト",
            employee_count=37,
            fiscal_year=2027,
            privacy_manager_name="個人情報保護 管理者",
        )
        intake_demo_state.submit_answers(
            QuestionnaireAnswers(
                has_employees=True,
                recruits_people=True,
                manages_customer_contacts=True,
                receives_inquiries=False,
                outsources_personal_data_processing=False,
                uses_external_cloud_services=True,
                stores_personal_data_on_paper=False,
                allows_remote_access=True,
            )
        )

        save_current_state(store)

        assert db_path.exists()
        with sqlite3.connect(db_path) as connection:
            rows = connection.execute(
                "SELECT state_key, payload_json FROM prototype_state ORDER BY state_key"
            ).fetchall()
        assert len(rows) == 9
        assert any(
            key == "company_profile" and "株式会社永続化テスト" in payload
            for key, payload in rows
        )

        company_profile.reset_state()
        intake_demo_state.reset_state()
        assert company_profile.get_state().name != "株式会社永続化テスト"
        assert intake_demo_state.get_state().answers_submitted is False

        restored_count = restore_current_state(store)

        assert restored_count == 9
        assert company_profile.get_state().name == "株式会社永続化テスト"
        assert company_profile.get_state().employee_count == 37
        assert company_profile.get_state().fiscal_year == 2027
        assert intake_demo_state.get_state().answers_submitted is True
        assert intake_demo_state.get_state().answers.has_employees is True
        assert intake_demo_state.get_state().answers.allows_remote_access is True
        assert intake_demo_state.get_state().candidates
        assert intake_demo_state.get_state().risks
    finally:
        apply_state_snapshot(baseline)
