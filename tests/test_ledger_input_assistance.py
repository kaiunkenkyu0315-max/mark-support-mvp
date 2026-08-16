import pytest
from fastapi.testclient import TestClient

from app import intake_demo_state
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_intake_state():
    intake_demo_state.reset_state()
    yield
    intake_demo_state.reset_state()


def _employee_answers():
    return {
        "has_employees": "yes",
        "recruits_people": "no",
        "manages_customer_contacts": "no",
        "receives_inquiries": "no",
        "outsources_personal_data_processing": "no",
        "uses_external_cloud_services": "no",
        "stores_personal_data_on_paper": "no",
        "allows_remote_access": "no",
    }


def _confirm_employee_candidate():
    client.post("/setup/answers", data=_employee_answers())
    target = intake_demo_state.get_state().candidates[0]
    return target, client.post(f"/setup/candidates/{target.id}/confirm")


def test_ledger_form_offers_common_choices_and_examples():
    _, response = _confirm_employee_candidate()

    assert response.status_code == 200
    assert 'list="ledger-acquisition-method-options"' in response.text
    assert 'list="ledger-storage-method-options"' in response.text
    assert 'list="ledger-storage-location-options"' in response.text
    assert "電子データ" in response.text
    assert "外部記録媒体" in response.text
    assert "クラウド／SaaS" in response.text
    assert "施錠キャビネット" in response.text
    assert "シュレッダー" in response.text
    assert "候補から選ぶだけで入力できます" in response.text
    assert "例：退職後5年" in response.text
    assert "法令・契約・利用目的等で適切な期間が異なる" in response.text


def test_ledger_form_still_accepts_values_outside_suggestions():
    target, _ = _confirm_employee_candidate()

    response = client.post(
        f"/setup/candidates/{target.id}/ledger",
        data={
            "acquisition_method": "社内独自申請システム",
            "storage_method": "独自媒体",
            "storage_location": "本社専用保管室",
            "outsourced": "no",
            "third_party_provided": "no",
            "retention_period": "社内規程に定める期間",
            "disposal_method": "社内廃棄手順に従う",
            "responsible_role": "管理部責任者",
        },
    )

    assert response.status_code == 200
    assert "社内独自申請システム" in response.text
    assert "独自媒体" in response.text
    assert "本社専用保管室" in response.text
    assert "台帳項目：入力済み" in response.text
