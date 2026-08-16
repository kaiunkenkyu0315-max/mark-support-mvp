"""会社・PMS基本情報の共通デモ状態。

会社名・従業者数・対象年度に加え、申請・文書・教育・監査など複数機能で再利用する
代表者、個人情報保護管理者、個人情報保護監査責任者、申請担当者の基本情報を
このモジュールで共通の正本として保持する。

MVPではインメモリ保持のみで、サーバー再起動時はデモ初期値へ戻る。
申請書固有の全項目をここへ詰め込まず、各機能で繰り返し使う情報を優先する。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CompanyProfile:
    # 会社基本情報
    name: str
    employee_count: int
    fiscal_year: int
    name_kana: str = ""
    corporate_number: str = ""
    registered_address: str = ""
    representative_title: str = ""
    representative_name: str = ""

    # PMS体制
    privacy_manager_name: str = ""
    privacy_manager_department_role: str = ""
    audit_manager_name: str = ""
    audit_manager_department_role: str = ""

    # Pマーク申請・連絡担当
    application_contact_name: str = ""
    application_contact_department_role: str = ""
    application_contact_email: str = ""

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


def update_profile(
    *,
    name: str,
    employee_count: int,
    fiscal_year: int,
    name_kana: str = "",
    corporate_number: str = "",
    registered_address: str = "",
    representative_title: str = "",
    representative_name: str = "",
    privacy_manager_name: str = "",
    privacy_manager_department_role: str = "",
    audit_manager_name: str = "",
    audit_manager_department_role: str = "",
    application_contact_name: str = "",
    application_contact_department_role: str = "",
    application_contact_email: str = "",
) -> CompanyProfile:
    """会社・PMS基本情報を保存する。

    申請書への転記を目的にした値も保持するが、ここでは法令・審査上の適格性判断はしない。
    文字列は前後空白を除去し、法人番号が入力されている場合だけ13桁数字か確認する。
    """

    global _state
    cleaned_name = name.strip()
    cleaned_corporate_number = corporate_number.strip()

    if not cleaned_name:
        raise ValueError("会社名は必須です")
    if employee_count < 1:
        raise ValueError("従業者数は1名以上で入力してください")
    if fiscal_year < 2000 or fiscal_year > 2100:
        raise ValueError("対象年度が範囲外です")
    if cleaned_corporate_number and (
        len(cleaned_corporate_number) != 13 or not cleaned_corporate_number.isdigit()
    ):
        raise ValueError("法人番号は13桁の数字で入力してください")

    _state = CompanyProfile(
        name=cleaned_name,
        employee_count=employee_count,
        fiscal_year=fiscal_year,
        name_kana=name_kana.strip(),
        corporate_number=cleaned_corporate_number,
        registered_address=registered_address.strip(),
        representative_title=representative_title.strip(),
        representative_name=representative_name.strip(),
        privacy_manager_name=privacy_manager_name.strip(),
        privacy_manager_department_role=privacy_manager_department_role.strip(),
        audit_manager_name=audit_manager_name.strip(),
        audit_manager_department_role=audit_manager_department_role.strip(),
        application_contact_name=application_contact_name.strip(),
        application_contact_department_role=application_contact_department_role.strip(),
        application_contact_email=application_contact_email.strip(),
        configured=True,
    )
    return _state


def reset_state() -> CompanyProfile:
    global _state
    _state = build_initial_state()
    return _state
