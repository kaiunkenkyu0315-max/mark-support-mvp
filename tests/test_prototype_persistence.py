import sqlite3

from fastapi.testclient import TestClient

from app import company_profile, intake_demo_state
from app.intake_schemas import QuestionnaireAnswers, SetupStatus
from app.main import app
from app.prototype_persistence import (
    SQLiteStateStore,
    apply_state_snapshot,
    capture_current_state,
    restore_current_state,
    save_current_state,
)
from app.setup_progress import get_effective_setup_status


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


def test_application_restart_restores_successful_mutations_from_sqlite(tmp_path, monkeypatch):
    baseline = capture_current_state()
    db_path = tmp_path / "restart" / "prototype.sqlite3"
    monkeypatch.setenv("MARK_SUPPORT_PERSISTENCE", "1")
    monkeypatch.setenv("MARK_SUPPORT_DB_PATH", str(db_path))

    try:
        with TestClient(app) as client:
            response = client.post("/dev/preset/operations", follow_redirects=False)
            assert response.status_code == 303
            assert get_effective_setup_status(intake_demo_state.get_state()) == SetupStatus.COMPLETE
            assert company_profile.get_state().configured is True

        assert db_path.exists()

        # サーバープロセス終了を模してインメモリ正本を消す。
        company_profile.reset_state()
        intake_demo_state.reset_state()
        assert get_effective_setup_status(intake_demo_state.get_state()) == SetupStatus.NOT_STARTED
        assert company_profile.get_state().configured is False

        # 同じFastAPIアプリを再起動するとlifespanでSQLiteから状態が復元される。
        with TestClient(app) as client:
            response = client.get("/")
            assert response.status_code == 200
            assert get_effective_setup_status(intake_demo_state.get_state()) == SetupStatus.COMPLETE
            assert company_profile.get_state().configured is True
    finally:
        apply_state_snapshot(baseline)
