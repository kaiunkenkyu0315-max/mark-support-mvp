import json

from app.evidence_store import EvidenceStore


def test_evidence_store_saves_lists_and_reads_real_file(tmp_path):
    store = EvidenceStore(tmp_path / "evidence")

    item = store.save(
        "education",
        "教育資料.pdf",
        b"%PDF-1.4 prototype evidence",
        "application/pdf",
        fiscal_year=2026,
    )

    listed = store.list("education")
    assert len(listed) == 1
    assert listed[0].id == item.id
    assert listed[0].original_name == "教育資料.pdf"
    assert listed[0].size_bytes == len(b"%PDF-1.4 prototype evidence")
    assert listed[0].fiscal_year == 2026
    assert len(listed[0].registered_on) == 10

    found = store.get("education", item.id)
    assert found is not None
    metadata, path = found
    assert metadata.original_name == "教育資料.pdf"
    assert path.read_bytes() == b"%PDF-1.4 prototype evidence"


def test_evidence_store_reads_old_manifest_without_fiscal_year(tmp_path):
    root = tmp_path / "evidence"
    area_dir = root / "education"
    area_dir.mkdir(parents=True)
    (area_dir / "old.pdf").write_bytes(b"old")
    (area_dir / "manifest.json").write_text(
        json.dumps(
            [
                {
                    "id": "legacy",
                    "area": "education",
                    "original_name": "旧教育資料.pdf",
                    "stored_name": "old.pdf",
                    "content_type": "application/pdf",
                    "size_bytes": 3,
                    "uploaded_at": "2026-08-18T10:00:00+00:00",
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    listed = EvidenceStore(root).list("education")

    assert len(listed) == 1
    assert listed[0].original_name == "旧教育資料.pdf"
    assert listed[0].fiscal_year is None
    assert listed[0].registered_on == "2026-08-18"


def test_evidence_store_rejects_executable_files(tmp_path):
    store = EvidenceStore(tmp_path / "evidence")

    try:
        store.save("education", "danger.exe", b"MZ", "application/octet-stream")
    except ValueError as exc:
        assert "添付できません" in str(exc)
    else:
        raise AssertionError("実行形式を保存してはいけない")
