"""会社基本情報の共通デモ状態。

会社名・従業者数・対象年度は各機能で個別に持たず、このモジュールを共通の正本とする。
MVPではインメモリ保持のみで、サーバー再起動時はデモ初期値へ戻る。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CompanyProfile:
    name: str
    employee_count: int
    fiscal_year: int
    configured: bool = False


DEFAULT_COMPANY_NAME = "株式会社サンプル"
DEFAULT_EMPLOYEE_COUNT = 50
DEFAULT_FISCAL_YEAR = 2026


def build_initial_state() -> CompanyProfile:
    return CompanyProfile(
        name=DEFAULT_COMPANY_NAME,
        employee_count=DEFAULT_EMPLOYEE_COUNT,
        fiscal_year=DEFAULT_FISCAL_YEAR,
        configured=False,
    )


_state = build_initial_state()


def get_state() -> CompanyProfile:
    return _state


def update_profile(*, name: str, employee_count: int, fiscal_year: int) -> CompanyProfile:
    """会社基本情報を保存する。

    HTTP層でも入力制約を掛けるが、状態層でも最低限の防御を行う。
    """

    global _state
    cleaned_name = name.strip()
    if not cleaned_name:
        raise ValueError("会社名は必須です")
    if employee_count < 1:
        raise ValueError("従業者数は1名以上で入力してください")
    if fiscal_year < 2000 or fiscal_year > 2100:
        raise ValueError("対象年度が範囲外です")

    _state = CompanyProfile(
        name=cleaned_name,
        employee_count=employee_count,
        fiscal_year=fiscal_year,
        configured=True,
    )
    return _state


def reset_state() -> CompanyProfile:
    global _state
    _state = build_initial_state()
    return _state
