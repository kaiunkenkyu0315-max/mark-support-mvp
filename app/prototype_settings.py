"""プロトタイプ実行時の小さな設定境界。"""

from __future__ import annotations

import os
import sys

_FALSE_VALUES = {"0", "false", "no", "off"}
_TRUE_VALUES = {"1", "true", "yes", "on"}


def dev_tools_enabled() -> bool:
    """開発用プリセットUI/ルートを利用できるか返す。

    通常実行では利用者向け画面に開発機能を露出しない。明示的に
    ``MARK_SUPPORT_DEV_TOOLS=1`` を設定した場合だけ有効化する。
    pytest 実行中は既存の開発プリセットテストを維持するため既定で有効にする。
    """

    configured = os.getenv("MARK_SUPPORT_DEV_TOOLS")
    if configured is not None:
        normalized = configured.strip().lower()
        if normalized in _TRUE_VALUES:
            return True
        if normalized in _FALSE_VALUES:
            return False
    return "pytest" in sys.modules
