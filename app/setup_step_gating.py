"""初期設定画面の後工程を、前工程の完了状態に応じて順次アンロックする。

MVPでは既存の業務ロジックやPOSTルートを変更せず、通常UI上で先の工程を
誤って操作しないための表示制御に限定する。見出しは残し、次に何を完了すれば
進めるかを利用者へ案内する。
"""

from __future__ import annotations

from app.intake import is_ledger_complete
from app.intake_demo_state import IntakeDemoState
from app.intake_schemas import (
    ControlDecisionStatus,
    PersonalInformationCandidateStatus,
)
from app.risk_schemas import RiskCandidateStatus


def _candidate_decisions_complete(state: IntakeDemoState) -> bool:
    if not state.answers_submitted:
        return False
    return all(
        candidate.status != PersonalInformationCandidateStatus.CANDIDATE
        and not candidate.needs_review
        for candidate in state.candidates
    )


def step4_unlocked(state: IntakeDemoState) -> bool:
    """個人情報確認と台帳入力が完了していればリスク確認へ進める。"""

    return _candidate_decisions_complete(state) and is_ledger_complete(state.candidates)


def step5_unlocked(state: IntakeDemoState) -> bool:
    """STEP4の該当判断と、確認済みリスクの評価確認がすべて終わっていれば管理策へ進める。"""

    if not step4_unlocked(state):
        return False
    return all(
        risk.status != RiskCandidateStatus.CANDIDATE
        and not risk.needs_review
        and (
            risk.status != RiskCandidateStatus.CONFIRMED
            or risk.evaluation_reviewed
        )
        for risk in state.risks
    )


def step6_unlocked(state: IntakeDemoState) -> bool:
    """管理策候補の採用／非適用判断がすべて終わっていれば運用開始へ進める。"""

    if not step5_unlocked(state):
        return False
    return all(
        suggestion.status != ControlDecisionStatus.SUGGESTED
        and not suggestion.needs_review
        for suggestion in state.control_suggestions
    )


def _locked_section(step_id: str, heading: str, message: str, prerequisite_anchor: str) -> str:
    return f"""
    <section class="step locked-step" id="{step_id}">
      <h2>{heading}</h2>
      <p>{message}</p>
      <p><a href="#{prerequisite_anchor}">前の工程を確認する</a></p>
      <p class="back-to-top"><a href="#setup-top">↑ 初期設定の先頭へ戻る</a></p>
    </section>
    """


def _replace_section(html: str, step_id: str, replacement: str) -> str:
    start_marker = f'<section class="step" id="{step_id}">'
    start = html.find(start_marker)
    if start == -1:
        return html
    end = html.find("</section>", start)
    if end == -1:
        return html
    end += len("</section>")
    return html[:start] + replacement + html[end:]


def apply_setup_step_gating(html: str, state: IntakeDemoState) -> str:
    """前工程が未完了のSTEP4〜6を案内表示へ置き換える。"""

    if not step4_unlocked(state):
        html = _replace_section(
            html,
            "step4",
            _locked_section(
                "step4",
                "STEP 4　リスク確認",
                "STEP3の個人情報台帳を完了すると、リスク候補を確認できるようになります。",
                "step3",
            ),
        )

    if not step5_unlocked(state):
        html = _replace_section(
            html,
            "step5",
            _locked_section(
                "step5",
                "STEP 5　管理策確認",
                "STEP4のリスク判断と評価確認を完了すると、管理策候補を確認できるようになります。",
                "step4",
            ),
        )

    if not step6_unlocked(state):
        html = _replace_section(
            html,
            "step6",
            _locked_section(
                "step6",
                "STEP 6　運用開始",
                "STEP5の管理策判断を完了すると、運用画面へ進めるようになります。",
                "step5",
            ),
        )

    return html
