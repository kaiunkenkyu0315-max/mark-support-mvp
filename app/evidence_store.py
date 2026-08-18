"""プロトタイプ用の証跡ファイル保存。

業務上の事実・評価結果とは分離し、ファイル添付そのものでは適合判定を変えない。
実ファイルはローカルの .prototype/evidence 配下へ保存し、表示用メタデータを
エリアごとのJSON manifestで管理する。本番ではオブジェクトストレージ等へ置換する。
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

_ALLOWED_SUFFIXES = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".csv", ".png", ".jpg", ".jpeg"}
_MAX_FILE_SIZE = 10 * 1024 * 1024


@dataclass(frozen=True)
class EvidenceFile:
    id: str
    area: str
    original_name: str
    stored_name: str
    content_type: str
    size_bytes: int
    uploaded_at: str


class EvidenceStore:
    def __init__(self, root: Path | str):
        self.root = Path(root)

    def _area_dir(self, area: str) -> Path:
        if not area or not area.replace("-", "").replace("_", "").isalnum():
            raise ValueError("証跡エリア名が不正です")
        return self.root / area

    def _manifest_path(self, area: str) -> Path:
        return self._area_dir(area) / "manifest.json"

    def _load_manifest(self, area: str) -> list[dict]:
        path = self._manifest_path(area)
        if not path.exists():
            return []
        return json.loads(path.read_text(encoding="utf-8"))

    def _save_manifest(self, area: str, rows: list[dict]) -> None:
        directory = self._area_dir(area)
        directory.mkdir(parents=True, exist_ok=True)
        self._manifest_path(area).write_text(
            json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def save(self, area: str, filename: str, content: bytes, content_type: str | None = None) -> EvidenceFile:
        original_name = Path(filename or "").name.strip()
        if not original_name:
            raise ValueError("ファイル名を確認してください")
        suffix = Path(original_name).suffix.lower()
        if suffix not in _ALLOWED_SUFFIXES:
            raise ValueError("このファイル形式は添付できません")
        if not content:
            raise ValueError("空のファイルは添付できません")
        if len(content) > _MAX_FILE_SIZE:
            raise ValueError("ファイルサイズは10MB以下にしてください")

        evidence_id = uuid4().hex
        stored_name = f"{evidence_id}{suffix}"
        directory = self._area_dir(area)
        directory.mkdir(parents=True, exist_ok=True)
        (directory / stored_name).write_bytes(content)

        item = EvidenceFile(
            id=evidence_id,
            area=area,
            original_name=original_name,
            stored_name=stored_name,
            content_type=content_type or "application/octet-stream",
            size_bytes=len(content),
            uploaded_at=datetime.now(timezone.utc).isoformat(),
        )
        rows = self._load_manifest(area)
        rows.append(asdict(item))
        self._save_manifest(area, rows)
        return item

    def list(self, area: str) -> list[EvidenceFile]:
        items: list[EvidenceFile] = []
        for row in self._load_manifest(area):
            item = EvidenceFile(**row)
            if (self._area_dir(area) / item.stored_name).exists():
                items.append(item)
        return items

    def get(self, area: str, evidence_id: str) -> tuple[EvidenceFile, Path] | None:
        for item in self.list(area):
            if item.id == evidence_id:
                return item, self._area_dir(area) / item.stored_name
        return None


def default_evidence_root() -> Path:
    configured = os.getenv("MARK_SUPPORT_EVIDENCE_DIR")
    return Path(configured) if configured else Path(".prototype") / "evidence"


def get_default_evidence_store() -> EvidenceStore:
    return EvidenceStore(default_evidence_root())
