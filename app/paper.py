"""紙媒体管理の整合性判定ロジック。

事実データ（PaperControl / PaperMediaStatus）に業務ルールを適用し、評価結果
（PaperEvaluationResult）を導出する。FastAPIやHTTP処理には依存しない、
純粋な業務ロジックとして実装する。UI側では判定を行わない。
"""

from __future__ import annotations

from app.paper_schemas import (
    PaperControl,
    PaperEvaluationResult,
    PaperEvaluationStatus,
    PaperIssue,
    PaperMediaStatus,
)


def evaluate_paper_management(control: PaperControl, status: PaperMediaStatus) -> PaperEvaluationResult:
    """紙媒体管理策に対する実施状況を評価する。"""

    issues: list[PaperIssue] = []

    # PAP-001: 施錠管理未確認
    if control.lock_check_required and not status.storage_locked:
        issues.append(
            PaperIssue(rule_id="PAP-001", message="保管場所の施錠管理が未確認です。")
        )

    # PAP-002: 持出しルール未設定
    if control.take_out_rule_required and not (status.take_out_rule or "").strip():
        issues.append(
            PaperIssue(rule_id="PAP-002", message="持出しルールが未設定です。")
        )

    # PAP-003: 廃棄確認不足
    if control.disposal_check_required and not status.disposal_confirmed:
        issues.append(
            PaperIssue(rule_id="PAP-003", message="廃棄確認が未実施です。")
        )

    # PAP-004: 実施結果未承認
    if control.approval_required and not status.approved:
        issues.append(
            PaperIssue(rule_id="PAP-004", message="実施結果が未承認です。")
        )

    result_status = (
        PaperEvaluationStatus.NEEDS_ACTION if issues else PaperEvaluationStatus.COMPLIANT
    )

    return PaperEvaluationResult(status=result_status, issues=issues)
