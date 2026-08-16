import pytest
from fastapi.testclient import TestClient

from app import intake_demo_state
from app.intake_schemas import ControlDecisionStatus
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_intake_state():
    """各テストの前後でデモ状態を初期化し、テスト間の状態汚染を防ぐ。"""

    intake_demo_state.reset_state()
    yield
    intake_demo_state.reset_state()


ALL_NO_FORM = {
    "has_employees": "no",
    "recruits_people": "no",
    "manages_customer_contacts": "no",
    "receives_inquiries": "no",
    "outsources_personal_data_processing": "no",
    "uses_external_cloud_services": "no",
    "stores_personal_data_on_paper": "no",
    "allows_remote_access": "no",
}


def answers_form(*yes_fields):
    """全問「いいえ」を基本に、指定したフィールドだけ「はい」にしたフォームデータを作る。"""

    form = dict(ALL_NO_FORM)
    for field in yes_fields:
        form[field] = "yes"
    return form


def test_case1_setup_page_returns_200_in_unanswered_state():
    response = client.get("/setup")

    assert response.status_code == 200
    assert "まだ回答が保存されていません" in response.text


def test_case2_submitting_answers_generates_candidates_and_suggestions():
    response = client.post(
        "/setup/answers",
        data=answers_form("has_employees", "outsources_personal_data_processing"),
    )

    assert response.status_code == 200
    assert "従業員情報" in response.text
    assert "個人情報保護教育" in response.text
    assert "委託先管理" in response.text


def test_answers_are_reflected_when_changed():
    client.post("/setup/answers", data=answers_form("recruits_people"))
    response = client.post("/setup/answers", data=answers_form("has_employees"))

    assert "従業員情報" in response.text
    # 採用活動=いいえに変わったため、未確認のままだった採用応募者情報候補は残らない。
    assert "採用応募者情報" not in response.text


def test_case13_only_adopted_control_shows_link_to_its_operations_page():
    client.post("/setup/answers", data=answers_form("has_employees"))

    response = client.post("/setup/controls/education/adopt")

    assert response.status_code == 200
    assert "/education" in response.text
    assert "教育管理へ進む" in response.text


def test_non_applicable_control_does_not_show_operations_link():
    client.post(
        "/setup/answers",
        data=answers_form("has_employees", "outsources_personal_data_processing"),
    )

    response = client.post(
        "/setup/controls/vendor_management/not-applicable",
        data={"reason": "対象業務がないため"},
    )

    assert response.status_code == 200
    assert "対象業務がないため" in response.text
    assert "委託先管理へ進む" not in response.text


def test_confirming_candidate_moves_it_into_ledger():
    client.post("/setup/answers", data=answers_form("has_employees"))
    target = intake_demo_state.get_state().candidates[0]

    response = client.post(f"/setup/candidates/{target.id}/confirm")

    assert response.status_code == 200
    assert "STEP 3　個人情報台帳" in response.text


def test_case14_reset_restores_unanswered_state():
    client.post("/setup/answers", data=answers_form("has_employees"))
    client.post("/setup/controls/education/adopt")

    response = client.post("/setup/reset")

    assert response.status_code == 200
    assert "まだ回答が保存されていません" in response.text
    state = intake_demo_state.get_state()
    assert state.answers_submitted is False
    assert state.control_suggestions == []


def test_case15_existing_education_page_still_works():
    response = client.get("/education")

    assert response.status_code == 200


def test_case15_existing_vendors_page_still_works():
    response = client.get("/vendors")

    assert response.status_code == 200


# --- 台帳必須項目の入力・編集 ---

FULL_LEDGER_FORM = {
    "acquisition_method": "申込フォームからの入力",
    "storage_method": "社内システムに保存",
    "storage_location": "社内サーバー",
    "outsourced": "no",
    "third_party_provided": "no",
    "retention_period": "退職後5年",
    "disposal_method": "システムから削除",
    "responsible_role": "総務部長",
}


def test_ledger_entry_can_be_filled_in_and_is_reflected():
    client.post("/setup/answers", data=answers_form("has_employees"))
    target = intake_demo_state.get_state().candidates[0]
    client.post(f"/setup/candidates/{target.id}/confirm")

    response = client.post(
        f"/setup/candidates/{target.id}/ledger",
        data=FULL_LEDGER_FORM,
    )

    assert response.status_code == 200
    assert "社内サーバー" in response.text
    assert "台帳項目：入力済み" in response.text


def test_ledger_entry_incomplete_note_shown_before_fields_filled():
    client.post("/setup/answers", data=answers_form("has_employees"))
    target = intake_demo_state.get_state().candidates[0]

    response = client.post(f"/setup/candidates/{target.id}/confirm")

    assert "台帳必須項目" in response.text
    assert "未入力" in response.text


def test_ledger_entry_stays_incomplete_when_outsourced_left_unanswered():
    """outsourced/third_party_providedを空欄（未回答）のまま他の項目だけ埋めても未完了。"""

    client.post("/setup/answers", data=answers_form("has_employees"))
    target = intake_demo_state.get_state().candidates[0]
    client.post(f"/setup/candidates/{target.id}/confirm")

    partial_form = dict(FULL_LEDGER_FORM)
    del partial_form["outsourced"]
    del partial_form["third_party_provided"]
    response = client.post(f"/setup/candidates/{target.id}/ledger", data=partial_form)

    assert "台帳項目：入力済み" not in response.text
    assert "外部委託の有無" in response.text


def test_ledger_entry_becomes_complete_when_outsourced_explicitly_false():
    """outsourced=「なし」は未回答と区別され、台帳項目を完了させられる。"""

    client.post("/setup/answers", data=answers_form("has_employees"))
    target = intake_demo_state.get_state().candidates[0]
    client.post(f"/setup/candidates/{target.id}/confirm")

    response = client.post(f"/setup/candidates/{target.id}/ledger", data=FULL_LEDGER_FORM)

    updated = next(c for c in intake_demo_state.get_state().candidates if c.id == target.id)
    assert updated.outsourced is False
    assert updated.third_party_provided is False
    assert "台帳項目：入力済み" in response.text


# --- setupのnot_started/in_progress/complete状態のトップページ・setup画面反映 ---


def test_top_page_shows_not_started_before_any_answer():
    response = client.get("/")

    assert response.status_code == 200
    assert "未着手" in response.text


def test_setup_flow_moves_from_in_progress_to_complete_and_back_on_answer_change():
    # 設定中（回答済みだが未確認・未入力あり）
    response = client.post("/setup/answers", data=answers_form("has_employees"))
    assert "設定中" in response.text
    index_response = client.get("/")
    assert "設定中" in index_response.text

    target = intake_demo_state.get_state().candidates[0]
    client.post(f"/setup/candidates/{target.id}/confirm")
    client.post(f"/setup/candidates/{target.id}/ledger", data=FULL_LEDGER_FORM)
    complete_response = client.post("/setup/controls/education/adopt")
    for risk in intake_demo_state.get_state().risks:
        complete_response = client.post(f"/setup/risks/{risk.id}/exclude")

    # 完了
    assert intake_demo_state.get_state().candidates
    assert "台帳項目：入力済み" in complete_response.text
    complete_index = client.get("/")
    assert "完了" in complete_index.text

    setup_page = client.get("/setup")
    assert "初期設定の状態：" in setup_page.text

    # 回答変更で前提が崩れ、設定中へ戻る
    back_to_progress = client.post("/setup/answers", data=answers_form("recruits_people"))
    assert "設定中" in back_to_progress.text
    back_index = client.get("/")
    assert "設定中" in back_index.text
