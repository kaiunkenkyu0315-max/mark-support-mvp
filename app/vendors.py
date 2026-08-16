"""委託先管理の整合性判定ロジック。

事実データ（Vendor / VendorControl / VendorAssessment / VendorContractStatus）に
業務ルールを適用し、評価結果（VendorEvaluationResult）を導出する。

FastAPIやHTTP処理には依存しない、純粋な業務ロジックとして実装する。
"""

from __future__ import annotations

from datetime import date

from app.vendor_schemas import (
    AssessmentResult,
    Vendor,
    VendorAssessment,
    VendorContractStatus,
    VendorControl,
    VendorEvaluationResult,
    VendorEvaluationStatus,
    VendorIssue,
)


def assessment_frequency_label(control: VendorControl) -> str:
    """委託先評価の頻度を表示用ラベルへ変換する。"""

    return (
        "年1回"
        if control.assessment_frequency.value == "annual"
        else control.assessment_frequency.value
    )


def evaluate_vendors(
    vendors: list[Vendor],
    control: VendorControl,
    assessments: list[VendorAssessment],
    contracts: list[VendorContractStatus],
    today: date | None = None,
) -> VendorEvaluationResult:
    """委託先管理策に対する実施状況を評価する。

    現在の管理対象は、active かつ handles_personal_data の委託先のみとする。
    """

    if today is None:
        today = date.today()

    targets = [vendor for vendor in vendors if vendor.active and vendor.handles_personal_data]
    target_ids = [vendor.id for vendor in targets]

    assessments_by_vendor = {assessment.vendor_id: assessment for assessment in assessments}
    contracts_by_vendor = {contract.vendor_id: contract for contract in contracts}

    issues: list[VendorIssue] = []

    # VEN-001: 初回評価未実施
    # activeかつ個人情報を取り扱う委託先について、初回評価が未実施なら不足とする。
    if control.initial_assessment_required:
        missing_initial_ids = [
            vendor_id
            for vendor_id in target_ids
            if not (
                vendor_id in assessments_by_vendor
                and assessments_by_vendor[vendor_id].initial_assessment_completed
            )
        ]
        if missing_initial_ids:
            issues.append(
                VendorIssue(
                    rule_id="VEN-001",
                    message=f"初回評価が未実施の委託先が{len(missing_initial_ids)}社あります。",
                    vendor_ids=missing_initial_ids,
                )
            )

        # VEN-003: 初回評価で不適格
        # 評価を実施した事実と、委託先として適格かどうかの結果を区別する。
        failed_initial_ids = [
            vendor_id
            for vendor_id in target_ids
            if (assessment := assessments_by_vendor.get(vendor_id)) is not None
            and assessment.initial_assessment_completed
            and assessment.initial_assessment_result == AssessmentResult.FAILED
        ]
        if failed_initial_ids:
            issues.append(
                VendorIssue(
                    rule_id="VEN-003",
                    message=f"初回評価で不適格の委託先が{len(failed_initial_ids)}社あります。",
                    vendor_ids=failed_initial_ids,
                )
            )

    # VEN-002: 契約確認
    # activeかつ個人情報を取り扱う委託先について、契約確認が未完了なら不足とする。
    if control.contract_check_required:
        missing_contract_ids = [
            vendor_id
            for vendor_id in target_ids
            if not (
                vendor_id in contracts_by_vendor
                and contracts_by_vendor[vendor_id].contract_confirmed
            )
        ]
        if missing_contract_ids:
            issues.append(
                VendorIssue(
                    rule_id="VEN-002",
                    message=f"契約確認が未完了の委託先が{len(missing_contract_ids)}社あります。",
                    vendor_ids=missing_contract_ids,
                )
            )

    # VEN-004: 定期評価
    # 定期評価必須の場合、有効な評価（実施日があり、結果が合格）が無ければ不足とする。
    if control.periodic_assessment_required:
        invalid_periodic_ids = [
            vendor_id
            for vendor_id in target_ids
            if (assessment := assessments_by_vendor.get(vendor_id)) is None
            or assessment.latest_assessment_date is None
            or assessment.assessment_result != AssessmentResult.PASSED
        ]
        if invalid_periodic_ids:
            issues.append(
                VendorIssue(
                    rule_id="VEN-004",
                    message=f"有効な定期評価がない委託先が{len(invalid_periodic_ids)}社あります。",
                    vendor_ids=invalid_periodic_ids,
                )
            )

    # VEN-006: 評価期限超過
    # 次回評価期限が設定されており、その期限を過ぎている場合は不足とする。
    overdue_ids = [
        vendor_id
        for vendor_id in target_ids
        if (assessment := assessments_by_vendor.get(vendor_id)) is not None
        and assessment.next_assessment_due is not None
        and assessment.next_assessment_due < today
    ]
    if overdue_ids:
        issues.append(
            VendorIssue(
                rule_id="VEN-006",
                message=f"次回評価期限を超過している委託先が{len(overdue_ids)}社あります。",
                vendor_ids=overdue_ids,
            )
        )

    status = (
        VendorEvaluationStatus.NEEDS_ACTION if issues else VendorEvaluationStatus.COMPLIANT
    )

    return VendorEvaluationResult(
        status=status,
        target_vendor_ids=target_ids,
        issues=issues,
    )
