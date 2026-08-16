"""STEP0 会社・PMS基本情報のHTML描画。

申請書をそのまま入力画面にせず、申請・文書・教育・監査などで繰り返し使う
共通情報だけを先に登録する。申請固有の詳細項目は後続機能で補完する。
"""

from __future__ import annotations

from html import escape

from app import company_profile


def _input(
    *,
    field: str,
    label: str,
    value: str,
    placeholder: str = "",
    required: bool = False,
    input_type: str = "text",
    help_text: str = "",
) -> str:
    required_attr = " required" if required else ""
    placeholder_attr = f' placeholder="{escape(placeholder)}"' if placeholder else ""
    help_html = f'<p class="question-help">{escape(help_text)}</p>' if help_text else ""
    return f"""
    <div class="company-form-field">
      <label for="{field}">{escape(label)}</label>
      <input id="{field}" type="{input_type}" name="{field}" value="{escape(value)}"{placeholder_attr}{required_attr}>
      {help_html}
    </div>
    """


def _setup_status_sync_script(configured: bool) -> str:
    """STEP0保存済みなら、従来描画の「未着手」を利用者向けに「設定中」へ揃える。"""

    if not configured:
        return ""
    return """
    <script>
    document.addEventListener("DOMContentLoaded", function () {
      const badge = document.querySelector(".setup-status .status-badge");
      if (!badge) return;
      if (badge.textContent.trim() === "未着手") {
        badge.textContent = "設定中";
        badge.classList.remove("not-started");
        badge.classList.add("needs-action");
      }
    });
    </script>
    """


def render_company_section() -> str:
    profile = company_profile.get_state()
    status = "保存済み" if profile.configured else "未保存（現在はデモ初期値）"

    company_fields = "".join(
        [
            _input(
                field="name",
                label="会社名",
                value=profile.name,
                required=True,
                help_text="登記上の正式商号を入力します。",
            ),
            _input(
                field="name_kana",
                label="会社名フリガナ",
                value=profile.name_kana,
                placeholder="例：カブシキガイシャサンプル",
            ),
            _input(
                field="corporate_number",
                label="法人番号",
                value=profile.corporate_number,
                placeholder="13桁（法人番号がある場合）",
            ),
            _input(
                field="registered_address",
                label="登記上の本店所在地",
                value=profile.registered_address,
                placeholder="例：東京都港区○○1-2-3 ○○ビル5階",
            ),
            _input(
                field="representative_title",
                label="代表者役職",
                value=profile.representative_title,
                placeholder="例：代表取締役",
            ),
            _input(
                field="representative_name",
                label="代表者氏名",
                value=profile.representative_name,
                placeholder="例：山田 太郎",
            ),
        ]
    )

    pms_fields = "".join(
        [
            _input(
                field="privacy_manager_name",
                label="個人情報保護管理者 氏名",
                value=profile.privacy_manager_name,
                placeholder="例：山田 花子",
                help_text="個人情報保護監査責任者とは別の方を設定します。",
            ),
            _input(
                field="privacy_manager_department_role",
                label="個人情報保護管理者 所属・役職",
                value=profile.privacy_manager_department_role,
                placeholder="例：管理部 部長",
            ),
            _input(
                field="audit_manager_name",
                label="個人情報保護監査責任者 氏名",
                value=profile.audit_manager_name,
                placeholder="例：佐藤 次郎",
                help_text="個人情報保護管理者とは別の方を設定します。代表者との兼任も避けます。",
            ),
            _input(
                field="audit_manager_department_role",
                label="個人情報保護監査責任者 所属・役職",
                value=profile.audit_manager_department_role,
                placeholder="例：取締役",
            ),
            _input(
                field="application_contact_name",
                label="Pマーク申請担当者 氏名",
                value=profile.application_contact_name,
                placeholder="例：鈴木 美咲",
            ),
            _input(
                field="application_contact_department_role",
                label="Pマーク申請担当者 所属・役職",
                value=profile.application_contact_department_role,
                placeholder="例：総務部 主任",
            ),
            _input(
                field="application_contact_email",
                label="Pマーク申請担当者 メールアドレス",
                value=profile.application_contact_email,
                placeholder="例：privacy@example.jp",
                input_type="email",
            ),
        ]
    )

    return f"""
    {_setup_status_sync_script(profile.configured)}
    <section class="step" id="step0">
      <h2>STEP 0　会社・PMS基本情報</h2>
      <p>申請・文書・教育・監査などで繰り返し使う基本情報を一度だけ登録します。未定の担当者情報は後から追記できます。</p>
      <p class="company-profile-status">会社・PMS基本情報の状態：{status}</p>
      <form method="post" action="/setup/company" class="company-form">
        <h3>会社基本情報</h3>
        {company_fields}
        <div class="company-form-field">
          <label for="employee_count">従業者数</label>
          <input id="employee_count" type="number" name="employee_count" min="1" max="9999"
                 value="{profile.employee_count}" required>
          <p class="question-help">現在は合計人数だけ登録します。雇用区分別の内訳は申請支援機能で追加予定です。</p>
        </div>
        <div class="company-form-field">
          <label for="fiscal_year">対象年度</label>
          <input id="fiscal_year" type="number" name="fiscal_year" min="2000" max="2100"
                 value="{profile.fiscal_year}" required>
        </div>

        <h3>PMS体制</h3>
        <p class="question-help">申請書や教育・内部監査・承認フローで再利用する責任者情報です。</p>
        {pms_fields}

        <button type="submit">会社・PMS基本情報を保存して次へ</button>
      </form>
      <p class="back-to-top"><a href="#setup-top">↑ 初期設定の先頭へ戻る</a></p>
    </section>
    """
