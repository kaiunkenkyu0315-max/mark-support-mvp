"""intakeフロー（業務ヒアリング〜個人情報確認〜リスクアセスメント〜管理策候補提示）
のHTML描画。

ここでは業務判定（候補生成・管理策提示・リスク評価・回答変更時の再計算ルール）を
一切行わない。app.intake_demo_state が保持する事実・候補・確定状態を
そのまま表示するだけとする。UI側に「従業員あり→教育管理」「紙保管あり→紙媒体リスク」
のような判定を書かない。
"""

from __future__ import annotations

from app.control_status import SETUP_STATUS_CSS_CLASS, SETUP_STATUS_LABELS
from app.intake import (
    CONTROL_STATUS_LABELS,
    LEDGER_FIELD_LABELS,
    find_control_suggestion,
    is_ledger_complete,
    is_ledger_entry_complete,
    missing_ledger_fields,
)
from app.intake_demo_state import QUESTIONS, IntakeDemoState, get_setup_status
from app.intake_schemas import (
    ControlDecisionStatus,
    ControlSuggestion,
    PersonalInformationCandidate,
    PersonalInformationCandidateStatus,
)
from app.risk import CONTROL_RELATED_RISK_IDS, confirmed_risk_reasons_for_control, evaluate_risk
from app.risk_schemas import RiskCandidate, RiskCandidateStatus, RiskLevel

QUESTION_LABELS = dict(QUESTIONS)

# 各質問の短い補足説明（利用者向け）。専門知識がなくても回答できるよう、
# 具体例を1文だけ添える。長文ヘルプにはしない。
QUESTION_HELP: dict[str, str] = {
    "has_employees": "例：正社員・パート・アルバイトを問わず、雇用している人がいれば『はい』。",
    "recruits_people": "例：求人募集・応募者の書類選考や面接を行っていれば『はい』。",
    "manages_customer_contacts": "例：顧客・取引先の担当者名や連絡先を名簿や名刺で管理していれば『はい』。",
    "receives_inquiries": "例：問い合わせフォームやメールで氏名・連絡先を受け取っていれば『はい』。",
    "outsources_personal_data_processing": "例：給与計算・採用管理などを外部の会社やクラウドサービスに委託していれば『はい』。",
    "uses_external_cloud_services": "例：勤怠管理・採用管理・顧客管理等をクラウドサービス（SaaS）で利用していれば『はい』。",
    "stores_personal_data_on_paper": "例：履歴書、雇用契約書、申込書、顧客名簿等をファイルやキャビネットで保管している場合は『はい』。",
    "allows_remote_access": "例：自宅や外出先から社内システムや顧客情報にアクセスすることがあれば『はい』。",
}

CANDIDATE_STATUS_LABELS = {
    PersonalInformationCandidateStatus.CANDIDATE: "未確認（候補）",
    PersonalInformationCandidateStatus.CONFIRMED: "確認済み（取り扱っている）",
    PersonalInformationCandidateStatus.EXCLUDED: "除外（該当しない）",
}

RISK_STATUS_LABELS = {
    RiskCandidateStatus.CANDIDATE: "未確認（候補）",
    RiskCandidateStatus.CONFIRMED: "確認済み",
    RiskCandidateStatus.EXCLUDED: "除外（該当しない）",
}

RISK_LEVEL_CSS_CLASS = {
    RiskLevel.LOW: "risk-low",
    RiskLevel.MEDIUM: "risk-medium",
    RiskLevel.HIGH: "risk-high",
}

EVALUATION_SCALE_LABELS = {1: "1（低）", 2: "2（中）", 3: "3（高）"}

# 採用済み管理策から、既存MVPへの導線ボタン文言。
CONTROL_LINK_LABELS = {
    "education": "教育管理へ進む",
    "vendor_management": "委託先管理へ進む",
    "access_control": "アクセス権限管理へ進む",
    "paper_management": "紙媒体管理へ進む",
}

# 上部の工程ナビゲーション。表示だけでなく、各STEPへのページ内リンクとして使う。
STEPPER = [
    ("step1", "STEP1 業務情報"),
    ("step2", "STEP2 個人情報確認"),
    ("step3", "STEP3 個人情報台帳"),
    ("step4", "STEP4 リスク確認"),
    ("step5", "STEP5 管理策確認"),
    ("step6", "STEP6 運用開始"),
]

NEEDS_REVIEW_NOTE = "回答内容が変更されたため、再確認をおすすめします。"

RISK_LEVEL_DISCLAIMER = (
    "リスクレベルは、事故の発生・法令違反・Pマーク取得可否を意味するものではありません。"
    "あくまで優先的に対策を検討する目安です。"
)

# 台帳入力の負担を下げるための一般的な候補。
# datalistを使うため、候補に当てはまらない場合も利用者は自由記入できる。
LEDGER_INPUT_OPTIONS: dict[str, tuple[str, ...]] = {
    "acquisition_method": (
        "本人から直接取得",
        "Webフォーム",
        "書面",
        "メール",
        "取引先・委託元から提供",
        "その他",
    ),
    "storage_method": (
        "電子データ",
        "紙",
        "外部記録媒体",
        "電子データ＋紙",
        "その他",
    ),
    "storage_location": (
        "クラウド／SaaS",
        "社内サーバ",
        "PC端末",
        "施錠キャビネット",
        "書庫",
        "外部記録媒体の保管庫",
        "その他",
    ),
    "disposal_method": (
        "システムから削除",
        "シュレッダー",
        "溶解処理",
        "専門業者へ廃棄委託",
        "媒体を物理破壊",
        "その他",
    ),
    "responsible_role": (
        "個人情報保護管理者",
        "総務責任者",
        "人事責任者",
        "情報システム責任者",
        "各部門責任者",
        "その他",
    ),
}

LEDGER_INPUT_HELP: dict[str, str] = {
    "acquisition_method": "候補から選ぶか、当てはまらなければ直接入力できます。例：展示会で本人から名刺を受領。",
    "storage_method": "情報そのものの形態を選びます。例：電子データ、紙、USB等の外部記録媒体。",
    "storage_location": "実際に保管している場所を選びます。例：クラウド／SaaS、社内サーバ、施錠キャビネット。",
    "retention_period": "例：退職後5年、契約終了後3年。法令・契約・利用目的等で適切な期間が異なるため、現在のMVPでは自社で定めている期間を入力してください。",
    "disposal_method": "候補から選ぶか、当てはまらなければ直接入力できます。例：システムから削除、シュレッダー。",
    "responsible_role": "個人名ではなく役割で入力します。例：総務責任者、人事責任者。",
}


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _render_stepper() -> str:
    items = "".join(
        f'<li><a href="#{anchor}">{_escape(label)}</a></li>'
        for anchor, label in STEPPER
    )
    return f'<ol class="stepper">{items}</ol>'


def _back_to_top_link() -> str:
    return '<p class="back-to-top"><a href="#setup-top">↑ 初期設定の先頭へ戻る</a></p>'


# ---------------------------------------------------------------------------
# STEP 1: 業務情報
# ---------------------------------------------------------------------------


def _radio(field: str, value: str, label: str, current: bool | None) -> str:
    checked = " checked" if (current is True and value == "yes") or (current is False and value == "no") else ""
    return (
        f'<label><input type="radio" name="{field}" value="{value}" required{checked}> {label}</label>'
    )


def _tristate_radio_group(field: str, current: bool | None) -> str:
    """台帳項目のうち、あり／なし／未回答の3値を取り得る項目用のラジオボタン群。

    未入力（None）を「いいえ」で代用せず、明示的に「未回答」として選べるようにする。
    """

    options = (("yes", "あり", current is True), ("no", "なし", current is False), ("unknown", "未回答", current is None))
    return "".join(
        f'<label><input type="radio" name="{field}" value="{value}"{" checked" if checked else ""}> {label}</label>'
        for value, label, checked in options
    )


def _render_step1_answers(state: IntakeDemoState) -> str:
    questions_html = "".join(
        f"""
        <div class="question">
          <p>{_escape(question_text)}</p>
          <p class="question-help">{_escape(QUESTION_HELP.get(field, ""))}</p>
          {_radio(field, "yes", "はい", getattr(state.answers, field))}
          {_radio(field, "no", "いいえ", getattr(state.answers, field))}
        </div>
        """
        for field, question_text in QUESTIONS
    )

    intro = (
        "まだ回答が保存されていません。以下の質問に回答して保存してください。"
        if not state.answers_submitted
        else "回答を変更すると、個人情報候補・管理策候補が自動的に再計算されます。"
    )

    return f"""
    <section class="step" id="step1">
      <h2>STEP 1　業務情報</h2>
      <p>{intro}</p>
      <form method="post" action="/setup/answers">
        {questions_html}
        <button type="submit">回答を保存する</button>
      </form>
      {_back_to_top_link()}
    </section>
    """


# ---------------------------------------------------------------------------
# 旧STEP 2候補一覧（互換用・画面では使用しない）
# ---------------------------------------------------------------------------


def _render_step2_candidates(state: IntakeDemoState) -> str:
    """旧読み取り専用候補一覧。

    候補表示と確認操作を分けると利用者が迷うため、画面描画では使用しない。
    候補情報は現在のSTEP2（_render_step3_confirmation）内で操作と一緒に表示する。
    """
    if not state.answers_submitted:
        body = "<p>STEP1に回答すると、ここに個人情報の候補が表示されます。</p>"
    elif not state.candidates:
        body = "<p>現在の回答からは、該当する個人情報の候補はありません。</p>"
    else:
        rows = "".join(
            f"""
            <li class="candidate-item">
              <p class="candidate-name">{_escape(candidate.name)}（{CANDIDATE_STATUS_LABELS[candidate.status]}）</p>
              <p class="candidate-reason">候補となった理由：{_escape(candidate.reason)}</p>
              {'<p class="needs-review">⚠ ' + NEEDS_REVIEW_NOTE + '</p>' if candidate.needs_review else ""}
            </li>
            """
            for candidate in state.candidates
        )
        body = f'<ul class="candidate-list">{rows}</ul>'
    return body


# ---------------------------------------------------------------------------
# STEP 2: 個人情報確認（候補表示＋操作を統合）
# ---------------------------------------------------------------------------


def _render_candidate_action_item(candidate: PersonalInformationCandidate) -> str:
    review_note = f'<p class="needs-review">⚠ {NEEDS_REVIEW_NOTE}</p>' if candidate.needs_review else ""
    return f"""
    <li class="candidate-item">
      <p class="candidate-name">{_escape(candidate.name)}（現在：{CANDIDATE_STATUS_LABELS[candidate.status]}）</p>
      <p class="candidate-reason">候補となった理由：{_escape(candidate.reason)}</p>
      {review_note}
      <form method="post" action="/setup/candidates/{candidate.id}/confirm">
        <button type="submit">取り扱っている</button>
      </form>
      <form method="post" action="/setup/candidates/{candidate.id}/exclude">
        <button type="submit">該当しない</button>
      </form>
    </li>
    """


def _render_step3_confirmation(state: IntakeDemoState) -> str:
    actionable = [
        candidate
        for candidate in state.candidates
        if candidate.status == PersonalInformationCandidateStatus.CANDIDATE or candidate.needs_review
    ]

    if not state.answers_submitted:
        body = "<p>STEP1に回答すると、ここで個人情報候補を確認できるようになります。</p>"
    elif not actionable:
        body = "<p>確認が必要な個人情報候補はありません。</p>"
    else:
        rows = "".join(_render_candidate_action_item(candidate) for candidate in actionable)
        body = f'<ul class="candidate-list">{rows}</ul>'

    return f"""
    <section class="step" id="step2">
      <h2>STEP 2　個人情報確認</h2>
      <p>業務回答から機械的に抽出した候補です。候補ごとに、実際に取り扱っているかどうかを確認してください。</p>
      {body}
      {_back_to_top_link()}
    </section>
    """


def _related_controls_for_candidate(
    state: IntakeDemoState, candidate: PersonalInformationCandidate
) -> list[ControlSuggestion]:
    """confirmed個人情報1件について、既存の管理策推薦関係から説明できる関連管理策を返す。

    STEP5の _related_candidates()（管理策→個人情報）と対になる、逆方向
    （個人情報→管理策）の参照。新しい関連付けルールは作らず、STEP5と同じ判定
    基準（教育：対象本人区分が「従業員」／委託先管理：外部委託あり）のみを使う。
    管理策候補がまだ一度も提示されていない場合は関連として表示しない
    （関係を捏造しない）。
    """

    related: list[ControlSuggestion] = []
    education = find_control_suggestion(state.control_suggestions, "education")
    if education is not None and candidate.subject_type == "従業員":
        related.append(education)
    vendor_management = find_control_suggestion(state.control_suggestions, "vendor_management")
    if vendor_management is not None and candidate.outsourced:
        related.append(vendor_management)
    return related


def _tristate_display(value: bool | None) -> str:
    if value is None:
        return "（未回答）"
    return "あり" if value else "なし"


def _render_datalist(list_id: str, options: tuple[str, ...]) -> str:
    option_html = "".join(f'<option value="{_escape(option)}"></option>' for option in options)
    return f'<datalist id="{list_id}">{option_html}</datalist>'


def _render_ledger_datalists() -> str:
    return "".join(
        _render_datalist(f"ledger-{field.replace('_', '-')}-options", options)
        for field, options in LEDGER_INPUT_OPTIONS.items()
    )


def _render_assisted_ledger_input(
    candidate: PersonalInformationCandidate,
    field: str,
    label: str,
    value: str | None,
    placeholder: str,
) -> str:
    input_id = f"{field}-{candidate.id}"
    list_id = f"ledger-{field.replace('_', '-')}-options"
    help_text = LEDGER_INPUT_HELP[field]
    return f"""
    <div class="ledger-form-field">
      <label for="{input_id}">{_escape(label)}</label>
      <input id="{input_id}" type="text" name="{field}" list="{list_id}"
             value="{_escape(value or '')}" placeholder="{_escape(placeholder)}">
      <p class="ledger-field-help">{_escape(help_text)}</p>
    </div>
    """


def _render_ledger_management_summary(
    state: IntakeDemoState, candidate: PersonalInformationCandidate
) -> str:
    """confirmed個人情報1件について「どう管理しているか」を見やすくまとめる。

    台帳フォーム（入力用）とは別に、現在の入力値を読みやすい形で提示する。
    関連する管理策は _related_controls_for_candidate() で説明できる範囲のみ表示する。
    """

    def _line(label: str, value: str | None) -> str:
        return f"<li>{label}：{_escape(value) if value else '（未入力）'}</li>"

    items_html = "".join(
        [
            _line("取得方法", candidate.acquisition_method),
            _line("保管形態", candidate.storage_method),
            _line("保管場所", candidate.storage_location),
            f"<li>委託：{_tristate_display(candidate.outsourced)}</li>",
            f"<li>第三者提供：{_tristate_display(candidate.third_party_provided)}</li>",
            _line("保存期間", candidate.retention_period),
            _line("廃棄方法", candidate.disposal_method),
            _line("管理責任者", candidate.responsible_role),
        ]
    )

    related = _related_controls_for_candidate(state, candidate)
    if related:
        related_items = "".join(
            f'<li><a href="{suggestion.link_url}">{_escape(suggestion.name)}</a>'
            f"（{CONTROL_STATUS_LABELS[suggestion.status]}）</li>"
            for suggestion in related
        )
        related_html = (
            '<p class="ledger-related-title">関連する管理策：</p>'
            f'<ul class="ledger-related-list">{related_items}</ul>'
        )
    else:
        related_html = '<p class="ledger-related-title">関連する管理策：（現在の回答からは特定できません）</p>'

    return f"""
    <div class="ledger-management-summary">
      <p class="ledger-management-title">管理方法：</p>
      <ul class="ledger-management-list">{items_html}</ul>
      {related_html}
    </div>
    """


def _render_ledger_entry(state: IntakeDemoState, candidate: PersonalInformationCandidate) -> str:
    review_note = f'<p class="needs-review">⚠ {NEEDS_REVIEW_NOTE}</p>' if candidate.needs_review else ""
    entry_complete = is_ledger_entry_complete(candidate)
    if entry_complete:
        entry_status_note = '<p class="ledger-entry-complete">台帳項目：入力済み</p>'
    else:
        missing_labels = "、".join(
            LEDGER_FIELD_LABELS.get(field, field) for field in missing_ledger_fields(candidate)
        )
        entry_status_note = (
            f'<p class="ledger-entry-incomplete">⚠ 台帳必須項目が未入力です（{_escape(missing_labels)}）。</p>'
        )

    return f"""
    <li class="candidate-item">
      <p class="candidate-name">{_escape(candidate.name)}</p>
      <p class="candidate-reason">
        対象本人の区分：{_escape(candidate.subject_type)}／
        主な利用目的：{_escape(candidate.purpose)}／
        候補となった業務：{_escape(QUESTION_LABELS.get(candidate.source_key, candidate.source_key))}
      </p>
      {review_note}
      {entry_status_note}
      {_render_ledger_management_summary(state, candidate)}
      <form method="post" action="/setup/candidates/{candidate.id}/ledger" class="ledger-form">
        <p class="ledger-form-guide">候補から選ぶだけで入力できます。当てはまらない場合は、そのまま自由に入力してください。</p>
        {_render_assisted_ledger_input(candidate, 'acquisition_method', '取得方法', candidate.acquisition_method, '例：本人から直接取得')}
        {_render_assisted_ledger_input(candidate, 'storage_method', '保管形態', candidate.storage_method, '例：電子データ')}
        {_render_assisted_ledger_input(candidate, 'storage_location', '保管場所', candidate.storage_location, '例：クラウド／SaaS')}
        <div class="ledger-form-row">
          <span class="ledger-form-row-label">外部委託の有無</span>
          {_tristate_radio_group('outsourced', candidate.outsourced)}
        </div>
        <div class="ledger-form-row">
          <span class="ledger-form-row-label">第三者提供の有無</span>
          {_tristate_radio_group('third_party_provided', candidate.third_party_provided)}
        </div>
        <div class="ledger-form-field">
          <label for="retention-period-{candidate.id}">保存期間</label>
          <input id="retention-period-{candidate.id}" type="text" name="retention_period"
                 value="{_escape(candidate.retention_period or '')}" placeholder="例：退職後5年">
          <p class="ledger-field-help">{_escape(LEDGER_INPUT_HELP['retention_period'])}</p>
        </div>
        {_render_assisted_ledger_input(candidate, 'disposal_method', '廃棄方法', candidate.disposal_method, '例：システムから削除')}
        {_render_assisted_ledger_input(candidate, 'responsible_role', '管理担当者（役割）', candidate.responsible_role, '例：総務責任者')}
        <button type="submit">台帳項目を保存する</button>
      </form>
    </li>
    """


# ---------------------------------------------------------------------------
# STEP 3: 個人情報台帳
# ---------------------------------------------------------------------------


def _render_ledger_section(state: IntakeDemoState) -> str:
    confirmed = [
        candidate
        for candidate in state.candidates
        if candidate.status == PersonalInformationCandidateStatus.CONFIRMED
    ]

    if not confirmed:
        return f"""
        <section class="ledger" id="step3">
          <h2>STEP 3　個人情報台帳</h2>
          <p>STEP2で「取り扱っている」と確認した個人情報について、取得・保管・委託・保存・廃棄等の管理方法を登録します。まだ確認済みの個人情報はありません。</p>
          {_back_to_top_link()}
        </section>
        """

    ledger_complete = is_ledger_complete(state.candidates)
    ledger_status_label = "完了" if ledger_complete else "未完了"
    ledger_status_class = "compliant" if ledger_complete else "needs-action"
    rows = "".join(_render_ledger_entry(state, candidate) for candidate in confirmed)

    return f"""
    <section class="ledger" id="step3">
      <h2>STEP 3　個人情報台帳</h2>
      <p>STEP2で「取り扱っている」と確認した個人情報だけを台帳として管理します。
      よくある内容は候補から選択でき、候補にない場合だけ自由入力できます。</p>
      <p class="ledger-status">台帳の状態：<span class="status-badge {ledger_status_class}">{ledger_status_label}</span></p>
      {_render_ledger_datalists()}
      <ul class="candidate-list">{rows}</ul>
      {_back_to_top_link()}
    </section>
    """


# ---------------------------------------------------------------------------
# STEP 4: リスク確認
# ---------------------------------------------------------------------------


def _related_personal_information_names(state: IntakeDemoState, risk: RiskCandidate) -> list[str]:
    candidates_by_key = {candidate.source_key: candidate for candidate in state.candidates}
    return [
        candidates_by_key[key].name
        for key in risk.related_personal_information_keys
        if key in candidates_by_key
    ]


def _render_risk_evaluation_block(risk: RiskCandidate) -> str:
    evaluation = evaluate_risk(risk)
    level_class = RISK_LEVEL_CSS_CLASS[evaluation.level]

    impact_options = "".join(
        f'<option value="{value}"{" selected" if value == risk.impact else ""}>{label}</option>'
        for value, label in EVALUATION_SCALE_LABELS.items()
    )
    likelihood_options = "".join(
        f'<option value="{value}"{" selected" if value == risk.likelihood else ""}>{label}</option>'
        for value, label in EVALUATION_SCALE_LABELS.items()
    )

    return f"""
    <div class="risk-evaluation">
      <p>システム初期案：影響度 {EVALUATION_SCALE_LABELS[risk.suggested_impact]}／発生可能性 {EVALUATION_SCALE_LABELS[risk.suggested_likelihood]}</p>
      <p class="risk-badge {level_class}">最終評価：影響度{risk.impact}×発生可能性{risk.likelihood}＝{evaluation.score}（{evaluation.level.value}）</p>
      <form method="post" action="/setup/risks/{risk.id}/evaluate">
        <label>影響度
          <select name="impact">{impact_options}</select>
        </label>
        <label>発生可能性
          <select name="likelihood">{likelihood_options}</select>
        </label>
        <button type="submit">評価を更新する</button>
      </form>
    </div>
    """


def _render_risk_item(state: IntakeDemoState, risk: RiskCandidate) -> str:
    status_label = RISK_STATUS_LABELS[risk.status]
    related_names = _related_personal_information_names(state, risk)
    related_html = (
        f"<p class=\"risk-related\">関連する個人情報：{'、'.join(_escape(name) for name in related_names)}</p>"
        if related_names
        else ""
    )
    review_note = f'<p class="needs-review">⚠ {NEEDS_REVIEW_NOTE}</p>' if risk.needs_review else ""

    if risk.status == RiskCandidateStatus.CANDIDATE or risk.needs_review:
        actions_html = f"""
        <form method="post" action="/setup/risks/{risk.id}/confirm">
          <button type="submit">このリスクを確認する</button>
        </form>
        <form method="post" action="/setup/risks/{risk.id}/exclude">
          <button type="submit">該当しない</button>
        </form>
        """
    elif risk.status == RiskCandidateStatus.CONFIRMED:
        actions_html = _render_risk_evaluation_block(risk)
    else:
        actions_html = ""

    return f"""
    <li class="risk-item">
      <p class="risk-name">{_escape(risk.name)}（{status_label}）</p>
      <p class="risk-description">{_escape(risk.description)}</p>
      <p class="risk-reason">候補となった理由：{_escape(risk.reason)}</p>
      {related_html}
      {review_note}
      {actions_html}
    </li>
    """


def _render_step4_risks(state: IntakeDemoState) -> str:
    confirmed_pi_count = sum(
        1
        for candidate in state.candidates
        if candidate.status == PersonalInformationCandidateStatus.CONFIRMED
    )
    confirmed_risks = [risk for risk in state.risks if risk.status == RiskCandidateStatus.CONFIRMED]
    high_risk_count = sum(
        1 for risk in confirmed_risks if evaluate_risk(risk).level == RiskLevel.HIGH
    )

    summary = f"""
    <ul class="risk-summary">
      <li>確認済み個人情報：{confirmed_pi_count}件</li>
      <li>リスク候補：{len(state.risks)}件</li>
      <li>確認済みリスク：{len(confirmed_risks)}件</li>
      <li>高リスク：{high_risk_count}件</li>
    </ul>
    <p class="risk-disclaimer">{RISK_LEVEL_DISCLAIMER}</p>
    """

    if not state.answers_submitted:
        body = "<p>STEP1に回答すると、ここでリスク候補を確認できるようになります。</p>"
    elif not state.risks:
        body = "<p>現在の回答・確認済み個人情報からは、該当するリスク候補はありません。</p>"
    else:
        rows = "".join(_render_risk_item(state, risk) for risk in state.risks)
        body = f'<ul class="risk-list">{rows}</ul>'

    return f"""
    <section class="step" id="step4">
      <h2>STEP 4　リスク確認</h2>
      <p>確認済みの個人情報・業務内容から、想定されるリスクの候補です。内容を確認し、実際に該当するかどうかを判断してください。</p>
      {summary}
      {body}
      {_back_to_top_link()}
    </section>
    """


# ---------------------------------------------------------------------------
# STEP 5: 管理策確認
# ---------------------------------------------------------------------------


def _related_candidates(state: IntakeDemoState, suggestion: ControlSuggestion) -> list[PersonalInformationCandidate]:
    confirmed = [
        candidate
        for candidate in state.candidates
        if candidate.status == PersonalInformationCandidateStatus.CONFIRMED
    ]
    if suggestion.control_id == "education":
        return [candidate for candidate in confirmed if candidate.subject_type == "従業員"]
    if suggestion.control_id == "vendor_management":
        return [candidate for candidate in confirmed if candidate.outsourced]
    return []


def _render_control_item(state: IntakeDemoState, suggestion: ControlSuggestion) -> str:
    status_label = CONTROL_STATUS_LABELS[suggestion.status]
    related = _related_candidates(state, suggestion)
    related_html = (
        f"<p class=\"control-related\">関連：{'、'.join(_escape(c.name) for c in related)}</p>"
        if related
        else '<p class="control-related">関連：（個人情報を確認すると表示されます）</p>'
    )
    review_note = f'<p class="needs-review">⚠ {NEEDS_REVIEW_NOTE}</p>' if suggestion.needs_review else ""

    confirmed_risks = [risk for risk in state.risks if risk.status == RiskCandidateStatus.CONFIRMED]
    risk_reasons = confirmed_risk_reasons_for_control(suggestion.control_id, confirmed_risks)
    reason_items = "".join(f"<li>{_escape(text)}</li>" for text in [suggestion.reason, *risk_reasons])
    reason_html = f'<p class="control-reason">提示理由：</p><ul class="control-reason-list">{reason_items}</ul>'

    if suggestion.status == ControlDecisionStatus.SUGGESTED:
        actions_html = f"""
        <form method="post" action="/setup/controls/{suggestion.control_id}/adopt">
          <button type="submit">採用する</button>
        </form>
        <form method="post" action="/setup/controls/{suggestion.control_id}/not-applicable" class="not-applicable-form">
          <input type="text" name="reason" placeholder="非適用の理由（必須）" required>
          <button type="submit">非適用にする</button>
        </form>
        """
    elif suggestion.status == ControlDecisionStatus.ADOPTED:
        link_label = CONTROL_LINK_LABELS.get(suggestion.control_id, "確認する")
        actions_html = (
            f'<p><a href="{suggestion.link_url}">{_escape(link_label)}</a></p>' if suggestion.link_url else ""
        )
    else:
        reason = suggestion.non_applicable_reason or "理由の記載なし"
        actions_html = f'<p class="non-applicable-reason">非適用理由：{_escape(reason)}</p>'

    return f"""
    <li class="control-item">
      <p class="control-name">{_escape(suggestion.name)}（{status_label}）</p>
      {reason_html}
      {related_html}
      {review_note}
      {actions_html}
    </li>
    """


def _render_unmapped_risk_note(state: IntakeDemoState) -> str:
    mapped_risk_ids = {
        risk_id for ids in CONTROL_RELATED_RISK_IDS.values() for risk_id in ids
    }
    confirmed_unmapped = [
        risk
        for risk in state.risks
        if risk.status == RiskCandidateStatus.CONFIRMED and risk.risk_id not in mapped_risk_ids
    ]
    if not confirmed_unmapped:
        return ""
    names = "、".join(_escape(risk.name) for risk in confirmed_unmapped)
    return (
        f'<p class="control-unmapped-note">{names}については、今回のMVPでは対応する管理策を'
        "実装していません（関連する管理策は今後追加予定です）。</p>"
    )


def _render_step5_controls(state: IntakeDemoState) -> str:
    if not state.answers_submitted:
        body = "<p>STEP1に回答すると、ここで管理策候補を確認できるようになります。</p>"
    elif not state.control_suggestions:
        body = "<p>現在の回答からは、提示できる管理策候補がありません。</p>"
    else:
        rows = "".join(
            _render_control_item(state, suggestion) for suggestion in state.control_suggestions
        )
        body = f'<ul class="control-list">{rows}</ul>'

    return f"""
    <section class="step" id="step5">
      <h2>STEP 5　管理策確認</h2>
      <p>確認した業務・個人情報・リスクの内容から、必要になり得る管理策候補です。採用するか、非適用にするかを判断してください。</p>
      {body}
      {_render_unmapped_risk_note(state)}
      {_back_to_top_link()}
    </section>
    """


# ---------------------------------------------------------------------------
# STEP 6: 運用開始
# ---------------------------------------------------------------------------


def _render_step6_summary(state: IntakeDemoState) -> str:
    adopted = [
        suggestion
        for suggestion in state.control_suggestions
        if suggestion.status == ControlDecisionStatus.ADOPTED
    ]

    if not adopted:
        body = "<p>採用した管理策はまだありません。STEP5で管理策を採用すると、ここに運用画面への導線が表示されます。</p>"
    else:
        links = "".join(
            f'<li><a href="{suggestion.link_url}">{_escape(CONTROL_LINK_LABELS.get(suggestion.control_id, suggestion.name))}</a></li>'
            for suggestion in adopted
            if suggestion.link_url
        )
        body = f'<p>採用した管理策の運用画面に進めます。</p><ul class="next-links">{links}</ul>'

    documents_link = '<p><a href="/documents">文書管理を確認する</a></p>'

    return f"""
    <section class="step" id="step6">
      <h2>STEP 6　運用開始</h2>
      {body}
      {documents_link}
      {_back_to_top_link()}
    </section>
    """


def _render_reset_section() -> str:
    return """
    <section class="reset">
      <form method="post" action="/setup/reset">
        <button type="submit">デモを未回答の初期状態に戻す</button>
      </form>
    </section>
    """


# ---------------------------------------------------------------------------
# ページ全体
# ---------------------------------------------------------------------------


def render_setup_page(state: IntakeDemoState) -> str:
    setup_status = get_setup_status(state)
    status_label = SETUP_STATUS_LABELS[setup_status]
    status_class = SETUP_STATUS_CSS_CLASS[setup_status]

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <title>Pマーク準備 - Pマーク取得・運用支援ツール MVP</title>
  <style>
    html {{ scroll-behavior: smooth; }}
    body {{ font-family: sans-serif; margin: 2rem; line-height: 1.6; max-width: 900px; }}
    h1 {{ margin-bottom: 0.5rem; }}
    section {{ margin-bottom: 2rem; padding-bottom: 1rem; border-bottom: 1px solid #ccc; scroll-margin-top: 1rem; }}
    .stepper {{ display: flex; flex-wrap: wrap; gap: 0.5rem; padding: 0; margin: 1rem 0; list-style: none; }}
    .stepper li {{
      background: #eef5fc; border: 1px solid #0a4a8a; border-radius: 4px;
      padding: 0.2rem 0.6rem; font-size: 0.9rem;
    }}
    .stepper a {{ color: #0a4a8a; text-decoration: none; }}
    .stepper a:hover {{ text-decoration: underline; }}
    .back-to-top {{ margin-top: 1rem; font-size: 0.9rem; }}
    .setup-status {{ font-weight: bold; }}
    .status-badge {{ display: inline-block; padding: 0.2rem 0.6rem; border-radius: 4px; color: #fff; }}
    .status-badge.not-started {{ background: #666; }}
    .status-badge.needs-action {{ background: #b30000; }}
    .status-badge.compliant {{ background: #0a7a0a; }}
    .ledger-status {{ font-weight: bold; }}
    .ledger-entry-complete {{ margin: 0 0 0.5rem; color: #0a7a0a; font-weight: bold; }}
    .ledger-entry-incomplete {{ margin: 0 0 0.5rem; color: #b30000; font-weight: bold; }}
    .ledger-form {{ display: block; margin: 1rem 0 0; }}
    .ledger-form-guide {{ margin: 0 0 0.8rem; font-size: 0.9rem; color: #555; }}
    .ledger-form-field {{ margin: 0 0 0.8rem; }}
    .ledger-form-field label {{ display: block; margin: 0 0 0.15rem; font-weight: bold; }}
    .ledger-form-field input[type="text"] {{ width: min(28rem, 95%); box-sizing: border-box; padding: 0.3rem 0.4rem; }}
    .ledger-field-help {{ margin: 0.15rem 0 0; font-size: 0.82rem; color: #777; }}
    .ledger-form-row {{ margin: 0 0 0.8rem; }}
    .ledger-form-row-label {{ font-weight: bold; margin-right: 0.5rem; }}
    .ledger-form-row label {{ display: inline-block; margin-right: 0.75rem; font-weight: normal; }}
    .question {{ margin-bottom: 0.75rem; }}
    .question p {{ margin: 0 0 0.3rem; font-weight: bold; }}
    .question-help {{ font-weight: normal !important; font-size: 0.85rem; color: #777; }}
    .question label {{ margin-right: 1rem; }}
    .ledger-management-summary {{
      margin: 0.5rem 0; padding: 0.5rem 0.75rem; background: #fff; border: 1px solid #ddd; border-radius: 4px;
    }}
    .ledger-management-title, .ledger-related-title {{ font-weight: bold; margin: 0 0 0.3rem; }}
    .ledger-management-list {{ margin: 0 0 0.5rem; padding-left: 1.2rem; }}
    .ledger-related-list {{ margin: 0; padding-left: 1.2rem; }}
    .candidate-list, .control-list, .risk-list {{ list-style: none; margin: 0; padding: 0; }}
    .candidate-item, .control-item, .risk-item {{
      padding: 0.75rem 1rem; margin-bottom: 0.75rem; border-radius: 4px;
      background: #f5f5f5; border-left: 4px solid #888;
    }}
    .candidate-name, .control-name, .risk-name {{ font-weight: bold; margin: 0 0 0.3rem; }}
    .candidate-reason, .control-reason, .control-related,
    .risk-description, .risk-reason, .risk-related {{ margin: 0 0 0.5rem; color: #555; }}
    .control-reason-list {{ margin: 0 0 0.5rem; padding-left: 1.2rem; color: #555; }}
    .non-applicable-reason, .control-unmapped-note {{ margin: 0; color: #555; }}
    .needs-review {{ margin: 0 0 0.5rem; color: #a15c00; font-weight: bold; }}
    form {{ display: inline-block; margin: 0 0.5rem 0.5rem 0; }}
    .not-applicable-form input[type="text"] {{ margin-right: 0.3rem; }}
    .records-table {{ border-collapse: collapse; }}
    .records-table th, .records-table td {{ text-align: left; border: 1px solid #ccc; padding: 4px 8px; }}
    .next-links {{ padding-left: 1.2rem; font-size: 1.1rem; }}
    .risk-summary {{ display: flex; flex-wrap: wrap; gap: 1rem; padding: 0; margin: 0.5rem 0; list-style: none; }}
    .risk-summary li {{
      background: #f5f5f5; border: 1px solid #ccc; border-radius: 4px; padding: 0.3rem 0.7rem;
    }}
    .risk-disclaimer {{ font-size: 0.85rem; color: #777; margin: 0 0 1rem; }}
    .risk-evaluation {{ margin-top: 0.5rem; }}
    .risk-evaluation select {{ margin: 0 0.5rem; }}
    .risk-badge {{ display: inline-block; padding: 0.2rem 0.6rem; border-radius: 4px; font-weight: bold; }}
    .risk-badge.risk-low {{ background: #e6f4ea; color: #0a7a0a; }}
    .risk-badge.risk-medium {{ background: #fff4e0; color: #a15c00; }}
    .risk-badge.risk-high {{ background: #fdeaea; color: #b30000; }}
  </style>
</head>
<body id="setup-top">
  <p><a href="/">&laquo; トップへ戻る</a></p>
  <h1>Pマーク準備</h1>
  <p>会社・業務について回答すると、取り扱っている可能性のある個人情報や、必要になり得る管理策の候補が提示されます。内容を確認・採用しながら準備を進めます。</p>
  <p class="setup-status">初期設定の状態：<span class="status-badge {status_class}">{status_label}</span></p>
  {_render_stepper()}

  {_render_step1_answers(state)}
  {_render_step3_confirmation(state)}
  {_render_ledger_section(state)}
  {_render_step4_risks(state)}
  {_render_step5_controls(state)}
  {_render_step6_summary(state)}
  {_render_reset_section()}
</body>
</html>
"""