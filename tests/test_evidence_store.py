from app.evidence_store import EvidenceStore


def test_evidence_store_saves_lists_and_reads_real_file(tmp_path):
    store = EvidenceStore(tmp_path / "evidence")

    item = store.save(
        "education",
        "教育資料.pdf",
        b"%PDF-1.4 prototype evidence",
        "application/pdf",
    )

    listed = store.list("education")
    assert len(listed) == 1
    assert listed[0].id == item.id
    assert listed[0].original_name == "教育資料.pdf"
    assert listed[0].size_bytes == len(b"%PDF-1.4 prototype evidence")

    found = store.get("education", item.id)
    assert found is not None
    metadata, path = found
    assert metadata.original_name == "教育資料.pdf"
    assert path.read_bytes() == b"%PDF-1.4 prototype evidence"


def test_evidence_store_rejects_executable_files(tmp_path):
    store = EvidenceStore(tmp_path / "evidence")

    try:
        store.save("education", "danger.exe", b"MZ", "application/octet-stream")
    except ValueError as exc:
        assert "添付できません" in str(exc)
    else:
        raise AssertionError("実行形式を保存してはいけない")
