"""内部監査・是正処置・マネジメントレビューの整合性評価。

画面操作ではなく、保存された事実・記録から現在の不足を判定する。
"""

from __future__ import annotations

from app.pms_review_schemas import PmsReviewEvaluationResult, PmsReviewIssue, PmsReviewState


def _filled(value: str | None) -> bool:
    return bool((value or "").strip())


def evaluate_pms_review(state: PmsReviewState) -> PmsReviewEvaluationResult:
    issues: list[PmsReviewIssue] = []
    audit = state.audit

    audit_complete = all(
        (
            _filled(audit.audit_date),
            _filled(audit.purpose),
            _filled(audit.criteria),
            _filled(audit.scope),
            _filled(audit.auditor_name),
            audit.auditor_independence_confirmed,
            _filled(audit.result_summary),
            audit.nonconformity_count is not None,
            _filled(audit.report_date),
            audit.reported_to_top_management,
            _filled(audit.evidence_name),
        )
    )
    if not audit_complete:
        issues.append(
            PmsReviewIssue(
                rule_id="AUD-001",
                message="内部監査の計画・実施・結果報告の記録を完成させてください。",
            )
        )

    corrective_required = bool(
        audit_complete and audit.nonconformity_count is not None and audit.nonconformity_count > 0
    )
    corrective = state.corrective_action
    corrective_complete = not corrective_required
    if corrective_required:
        corrective_complete = all(
            (
                _filled(corrective.finding_summary),
                _filled(corrective.immediate_action),
                _filled(corrective.root_cause),
                _filled(corrective.corrective_action),
                _filled(corrective.implemented_on),
                corrective.effectiveness_result == "effective",
                _filled(corrective.effectiveness_checked_on),
                _filled(corrective.approved_by),
                _filled(corrective.approved_at),
                _filled(corrective.evidence_name),
            )
        )
        if not corrective_complete:
            message = "監査で確認された不適合について、原因分析・是正処置・有効性確認・承認を記録してください。"
            if corrective.effectiveness_result == "ineffective":
                message = "是正処置の有効性が確認できていません。追加の是正処置を行い、再評価してください。"
            issues.append(PmsReviewIssue(rule_id="CAR-001", message=message))

    review = state.management_review
    management_review_complete = all(
        (
            _filled(review.review_date),
            _filled(review.top_management_name),
            _filled(review.input_summary),
            _filled(review.decision_summary),
            review.changes_needed is not None,
            _filled(review.evidence_name),
        )
    )
    if management_review_complete and review.changes_needed:
        management_review_complete = _filled(review.improvement_actions)

    # MVPの取得支援フローでは、監査と必要な是正処置の記録を整えた後に
    # マネジメントレビューへ進む。レビュー自体の記録が存在していても、前工程が
    # 未完了なら全体としては完了扱いにしない。
    prerequisites_complete = audit_complete and (not corrective_required or corrective_complete)
    if not management_review_complete or not prerequisites_complete:
        issues.append(
            PmsReviewIssue(
                rule_id="MR-001",
                message="マネジメントレビューの入力情報・トップマネジメントの決定・記録を完成させてください。",
            )
        )

    return PmsReviewEvaluationResult(
        issues=issues,
        audit_complete=audit_complete,
        corrective_required=corrective_required,
        corrective_complete=corrective_complete,
        management_review_complete=management_review_complete and prerequisites_complete,
    )
