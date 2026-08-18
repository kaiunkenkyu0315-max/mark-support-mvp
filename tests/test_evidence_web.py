from fastapi.testclient import TestClient

from app import demo_state
from app.education import evaluate_training
from app.main import app

client = TestClient(app)


def _education_issue_count() -> int:
    state = demo_state.get_state()
    return len(evaluate_training(state.employees, state.control, state.plan, state.records).issues)


def test_education_can_attach_and_download_real_evidence_without_changing_compliance(tmp_path, monkeypatch):
    monkeypatch.setenv("MARK_SUPPORT_EVIDENCE_DIR", str(tmp_path / "evidence"))
    client.post("/dev/preset/operations")

    before_issue_count = _education_issue_count()
    assert before_issue_count > 0

    response = client.post(
        "/evidence/education/upload",
        files={"file": ("2026年度教育資料.pdf", b"%PDF-1.4 education", "application/pdf")},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "証跡ファイルを添付しました" in response.text
    assert "2026年度教育資料.pdf" in response.text
    assert "添付しただけでは、教育工程の完了・適合にはなりません" in response.text
    assert _education_issue_count() == before_issue_count

    marker = '/evidence/education/'
    start = response.text.index(marker) + len(marker)
    evidence_id = response.text[start:].split('"', 1)[0]
    download = client.get(f"{marker}{evidence_id}")

    assert download.status_code == 200
    assert download.content == b"%PDF-1.4 education"


def test_education_rejects_unsupported_evidence_file(tmp_path, monkeypatch):
    monkeypatch.setenv("MARK_SUPPORT_EVIDENCE_DIR", str(tmp_path / "evidence"))
    client.post("/dev/preset/operations")

    response = client.post(
        "/evidence/education/upload",
        files={"file": ("danger.exe", b"MZ", "application/octet-stream")},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "このファイル形式は添付できません" in response.text
    assert "danger.exe" not in response.text
