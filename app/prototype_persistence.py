"""プロトタイプ用SQLite永続化アダプタ。

既存MVPの各 ``*_demo_state`` は業務ロジック検証を優先してインメモリ状態を
正本としている。本モジュールはその構造を大きく変更せず、状態をSQLiteへ
JSONスナップショットとして保存・復元する。

これはプロトタイプ段階の永続化境界であり、本番の企業・年度・ユーザー単位の
正規化DBスキーマを代替するものではない。後続でRepository層へ置換できるよう、
HTTP層からは save_current_state / restore_current_state のみを利用する。
"""

from __future__ import annotations

import importlib
import json
import os
import sqlite3
import sys
from copy import deepcopy
from dataclasses import fields, is_dataclass
from datetime import date, datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

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

_STATE_MODULES = {
    "company_profile": company_profile,
    "intake": intake_demo_state,
    "education": demo_state,
    "vendors": vendor_demo_state,
    "access_control": access_control_demo_state,
    "paper": paper_demo_state,
    "pms_review": pms_review_demo_state,
    "application_prep": application_prep_demo_state,
    "annual_cycle": annual_cycle_demo_state,
}

_DEFAULT_DB_PATH = Path(".prototype") / "mark_support.sqlite3"
_FALSE_VALUES = {"0", "false", "no", "off"}


def persistence_enabled() -> bool:
    """通常実行では有効、pytestでは既存テスト隔離のため既定で無効にする。

    MARK_SUPPORT_PERSISTENCE を明示した場合はその指定を優先する。
    """

    configured = os.getenv("MARK_SUPPORT_PERSISTENCE")
    if configured is not None:
        return configured.strip().lower() not in _FALSE_VALUES
    return "pytest" not in sys.modules


def default_db_path() -> Path:
    configured = os.getenv("MARK_SUPPORT_DB_PATH")
    return Path(configured) if configured else _DEFAULT_DB_PATH


def _type_path(value_type: type[Any]) -> str:
    return f"{value_type.__module__}:{value_type.__qualname__}"


def _resolve_type(path: str) -> type[Any]:
    module_name, qualname = path.split(":", 1)
    value: Any = importlib.import_module(module_name)
    for part in qualname.split("."):
        value = getattr(value, part)
    return value


def _encode(value: Any) -> Any:
    """dataclass/Enumを含む状態を型情報付きJSON互換値へ変換する。"""

    if isinstance(value, Enum):
        return {
            "__kind__": "enum",
            "type": _type_path(type(value)),
            "value": _encode(value.value),
        }
    if is_dataclass(value) and not isinstance(value, type):
        return {
            "__kind__": "dataclass",
            "type": _type_path(type(value)),
            "fields": {field.name: _encode(getattr(value, field.name)) for field in fields(value)},
        }
    if isinstance(value, datetime):
        return {"__kind__": "datetime", "value": value.isoformat()}
    if isinstance(value, date):
        return {"__kind__": "date", "value": value.isoformat()}
    if isinstance(value, dict):
        return {
            "__kind__": "dict",
            "items": [[_encode(key), _encode(item)] for key, item in value.items()],
        }
    if isinstance(value, tuple):
        return {"__kind__": "tuple", "items": [_encode(item) for item in value]}
    if isinstance(value, set):
        return {"__kind__": "set", "items": [_encode(item) for item in value]}
    if isinstance(value, list):
        return [_encode(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"永続化未対応の型です: {type(value)!r}")


def _decode(value: Any) -> Any:
    if isinstance(value, list):
        return [_decode(item) for item in value]
    if not isinstance(value, dict) or "__kind__" not in value:
        return value

    kind = value["__kind__"]
    if kind == "enum":
        enum_type = _resolve_type(value["type"])
        return enum_type(_decode(value["value"]))
    if kind == "dataclass":
        data_type = _resolve_type(value["type"])
        kwargs = {name: _decode(item) for name, item in value["fields"].items()}
        return data_type(**kwargs)
    if kind == "datetime":
        return datetime.fromisoformat(value["value"])
    if kind == "date":
        return date.fromisoformat(value["value"])
    if kind == "dict":
        return {_decode(key): _decode(item) for key, item in value["items"]}
    if kind == "tuple":
        return tuple(_decode(item) for item in value["items"])
    if kind == "set":
        return {_decode(item) for item in value["items"]}
    raise ValueError(f"未知の永続化形式です: {kind}")


class SQLiteStateStore:
    """状態キーごとにJSONスナップショットを保存する小さなSQLiteストア。"""

    def __init__(self, path: Path | str):
        self.path = Path(path)

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS prototype_state (
                    state_key TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.commit()

    def save(self, states: dict[str, Any]) -> None:
        self.initialize()
        updated_at = datetime.now(timezone.utc).isoformat()
        rows = [
            (
                key,
                json.dumps(_encode(state), ensure_ascii=False, separators=(",", ":")),
                updated_at,
            )
            for key, state in states.items()
        ]
        with sqlite3.connect(self.path) as connection:
            connection.executemany(
                """
                INSERT INTO prototype_state (state_key, payload_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(state_key) DO UPDATE SET
                    payload_json = excluded.payload_json,
                    updated_at = excluded.updated_at
                """,
                rows,
            )
            connection.commit()

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        self.initialize()
        with sqlite3.connect(self.path) as connection:
            rows = connection.execute(
                "SELECT state_key, payload_json FROM prototype_state"
            ).fetchall()
        return {key: _decode(json.loads(payload_json)) for key, payload_json in rows}


def capture_current_state() -> dict[str, Any]:
    """現在の各業務状態を独立したスナップショットとして取得する。"""

    return {key: deepcopy(module.get_state()) for key, module in _STATE_MODULES.items()}


def apply_state_snapshot(states: dict[str, Any]) -> int:
    """既知の状態だけをインメモリ正本へ復元し、復元件数を返す。"""

    restored = 0
    for key, state in states.items():
        module = _STATE_MODULES.get(key)
        if module is None:
            continue
        # demo_state群の置換点をここへ集約し、各業務ロジックへ永続化依存を漏らさない。
        setattr(module, "_state", state)
        restored += 1
    return restored


def save_current_state(store: SQLiteStateStore) -> None:
    store.save(capture_current_state())


def restore_current_state(store: SQLiteStateStore) -> int:
    return apply_state_snapshot(store.load())
