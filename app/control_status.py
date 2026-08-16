"""利用者向け状態表示の共通定義。

各運用モジュール（education / vendors / access_control / paper）と
管理者ダッシュボード（app.main / app.dashboard）の双方が、同じ意味で
状態を表示するための単一の定義場所とする。

特に、管理策の採用可否（setup側のControlSuggestion.status。正本）と、
その管理策の運用評価（各運用モジュールのevaluate_*関数が返す結果）を
混同しない。管理策がadoptedになって初めて、運用評価結果（要対応／適合）を
利用者向けステータスとして表示する。suggested・not_applicable・未提示の間は、
運用評価の中身（issuesの有無）に関わらず、採用可否に基づく中立的な状態
（採用判断待ち／非適用／未提示）のみを返す。

ここでの「未着手」「要確認」「未提示」「非適用」「要対応」「適合」「完了」の
意味は、README等ではなくこのモジュールを単一の正とする。
"""

from __future__ import annotations

from app.intake_schemas import ControlDecisionStatus, ControlSuggestion, SetupStatus

# 初期設定全体（SetupStatus）の表示ラベル・CSSクラス。
# app.main（トップページ・ダッシュボード）と app.intake_view（初期設定画面）の
# 双方から参照し、表記のずれを防ぐ。
SETUP_STATUS_LABELS: dict[SetupStatus, str] = {
    SetupStatus.NOT_STARTED: "未着手",
    SetupStatus.IN_PROGRESS: "設定中",
    SetupStatus.COMPLETE: "完了",
}

SETUP_STATUS_CSS_CLASS: dict[SetupStatus, str] = {
    SetupStatus.NOT_STARTED: "not-started",
    SetupStatus.IN_PROGRESS: "needs-action",
    SetupStatus.COMPLETE: "compliant",
}


def operational_status(
    suggestion: ControlSuggestion | None, *, has_issues: bool
) -> tuple[str, str, str]:
    """採用可否（setupのControlSuggestion.status）を踏まえた運用状態を返す。

    Returns:
        (label, css_class, note) の3要素タプル。
        note は、なぜその状態なのかを画面にそのまま出せる一文の説明。

    管理策がadopted（採用済み）の場合のみ、実際の運用評価結果
    （has_issuesの有無）から「要対応」「適合」を返す。それ以外
    （未提示／採用判断待ち／非適用）では、has_issuesを一切参照しない
    ——採用されていない管理策の運用評価を、利用者向けステータスとして
    表示しないため。
    """

    if suggestion is None:
        return (
            "未提示",
            "not-started",
            "この管理策は、現在の初期設定内容では候補として提示されていません。業務回答を変更すると候補になる場合があります。",
        )
    if suggestion.status == ControlDecisionStatus.SUGGESTED:
        return (
            "採用判断待ち",
            "not-started",
            "初期設定で候補として提示されていますが、採用するかどうかの判断がまだ済んでいません。",
        )
    if suggestion.status == ControlDecisionStatus.NOT_APPLICABLE:
        reason = suggestion.non_applicable_reason or "理由の記載なし"
        return (
            "非適用",
            "not-started",
            f"初期設定で非適用と判断されています（理由：{reason}）。",
        )
    # ADOPTED の場合のみ、実際の運用評価結果を利用者向けステータスとして表示する。
    if has_issues:
        return (
            "要対応",
            "needs-action",
            "採用済みの管理策について、運用上の不足があります。",
        )
    return (
        "適合",
        "compliant",
        "採用済みの管理策について、現在確認している運用要件を満たしています。",
    )


def is_adopted(suggestion: ControlSuggestion | None) -> bool:
    """管理策が採用済み（adopted）かどうかを、setupの判断のみを見て返す。"""

    return suggestion is not None and suggestion.status == ControlDecisionStatus.ADOPTED
