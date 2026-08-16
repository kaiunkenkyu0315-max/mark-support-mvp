"""取得計画・年間PMS運用計画で共通利用する最小の計画モデル。

計画の種類ごとに別UIを増やさず、工程・状態・現在地・遷移先という共通構造を
保持する。開始日・期限・担当者などは後続で拡張できるが、MVPでは森→木の
ナビゲーションに必要な情報だけを持つ。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlanStep:
    number: int
    name: str
    description: str
    status: str
    status_kind: str
    link: str | None = None
    implemented: bool = True
    current: bool = False


@dataclass(frozen=True)
class Plan:
    title: str
    description: str
    steps: list[PlanStep]
    completed_count: int
    tracked_total: int
    current_text: str
    progress_label: str = "進捗"
    footer_note: str | None = None
