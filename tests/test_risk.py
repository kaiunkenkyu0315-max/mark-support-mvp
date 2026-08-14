import pytest

from app import intake_demo_state
from app.intake import derive_personal_information_candidates
from app.intake_schemas import PersonalInformationCandidateStatus, QuestionnaireAnswers
from app.risk import (
    calculate_risk_level,
    confirmed_risk_reasons_for_control,
    derive_risk_candidates,
    evaluate_risk,
    merge_risk_candidates_after_change,
)
from app.risk_schemas import RiskCandidate, RiskCandidateStatus, RiskLevel


def make_answers(**overrides):
    defaults = dict(
        has_employees=False,
        recruits_people=False,
        manages_customer_contacts=False,
        receives_inquiries=False,
        outsources_personal_data_processing=False,
        uses_external_cloud_services=False,
        stores_personal_data_on_paper=False,
        allows_remote_access=False,
    )
    defaults.update(overrides)
    return QuestionnaireAnswers(**defaults)


def confirm_all(candidates):
    for candidate in candidates:
        candidate.status = PersonalInformationCandidateStatus.CONFIRMED
    return candidates


# --- リスク候補生成ロジック（純粋関数） ---


def test_case1_unconfirmed_personal_information_does_not_yield_pi_dependent_risk():
    answers = make_answers(has_employees=True)
    candidates = derive_personal_information_candidates(answers)  # すべて未確認のまま

    risks = derive_risk_candidates(answers, candidates)

    assert not any(risk.risk_id == "RISK-004" for risk in risks)
    assert not any(risk.risk_id == "RISK-005" for risk in risks)


def test_case2_paper_storage_yes_yields_paper_loss_risk_candidate():
    answers = make_answers(stores_personal_data_on_paper=True)

    risks = derive_risk_candidates(answers, [])

    assert any(risk.risk_id == "RISK-002" for risk in risks)


def test_case3_outsourcing_yes_yields_vendor_leak_risk_candidate():
    answers = make_answers(outsources_personal_data_processing=True)

    risks = derive_risk_candidates(answers, [])

    assert any(risk.risk_id == "RISK-003" for risk in risks)


def test_case4_cloud_or_remote_access_yields_unauthorized_access_risk_candidate():
    cloud_answers = make_answers(uses_external_cloud_services=True)
    remote_answers = make_answers(allows_remote_access=True)

    assert any(r.risk_id == "RISK-001" for r in derive_risk_candidates(cloud_answers, []))
    assert any(r.risk_id == "RISK-001" for r in derive_risk_candidates(remote_answers, []))


def test_case5_employees_and_confirmed_pi_yields_insider_risk_candidate():
    answers = make_answers(has_employees=True)
    candidates = confirm_all(derive_personal_information_candidates(answers))

    risks = derive_risk_candidates(answers, candidates)

    assert any(risk.risk_id == "RISK-005" for risk in risks)


def test_case6_generated_risk_candidates_are_not_confirmed():
    answers = make_answers(stores_personal_data_on_paper=True, outsources_personal_data_processing=True)

    risks = derive_risk_candidates(answers, [])

    assert risks
    assert all(risk.status == RiskCandidateStatus.CANDIDATE for risk in risks)


# --- リスク評価（純粋関数） ---


def test_case9_score_is_impact_times_likelihood():
    candidate = RiskCandidate(
        id=1,
        risk_id="RISK-001",
        name="不正アクセス",
        description="",
        reason="",
        suggested_impact=3,
        suggested_likelihood=2,
        impact=3,
        likelihood=2,
    )

    evaluation = evaluate_risk(candidate)

    assert evaluation.score == 6


@pytest.mark.parametrize(
    "impact,likelihood,expected",
    [
        (1, 1, RiskLevel.LOW),
        (1, 2, RiskLevel.LOW),
        (1, 3, RiskLevel.MEDIUM),
        (2, 2, RiskLevel.MEDIUM),
        (2, 3, RiskLevel.HIGH),
        (3, 3, RiskLevel.HIGH),
    ],
)
def test_case10_score_is_classified_into_low_medium_high(impact, likelihood, expected):
    assert calculate_risk_level(impact, likelihood) == expected


# --- 管理策への理由付け（表示用ヘルパー） ---


def test_case13_confirmed_vendor_leak_risk_feeds_vendor_management_reason():
    confirmed_risk = RiskCandidate(
        id=1,
        risk_id="RISK-003",
        name="委託先での漏えい・不適切な取扱い",
        description="",
        reason="",
        status=RiskCandidateStatus.CONFIRMED,
        suggested_impact=3,
        suggested_likelihood=2,
        impact=3,
        likelihood=2,
    )

    reasons = confirmed_risk_reasons_for_control("vendor_management", [confirmed_risk])

    assert reasons
    assert any("委託先での漏えい" in reason for reason in reasons)


def test_unconfirmed_risk_does_not_feed_control_reason():
    candidate_risk = RiskCandidate(
        id=1,
        risk_id="RISK-003",
        name="委託先での漏えい・不適切な取扱い",
        description="",
        reason="",
        status=RiskCandidateStatus.CANDIDATE,
        suggested_impact=3,
        suggested_likelihood=2,
        impact=3,
        likelihood=2,
    )

    reasons = confirmed_risk_reasons_for_control("vendor_management", [candidate_risk])

    assert reasons == []


# --- 回答変更時の再計算（merge_risk_candidates_after_change） ---


def test_case14_merge_does_not_silently_drop_confirmed_risk_when_premise_changes():
    answers = make_answers(outsources_personal_data_processing=True)
    risks = derive_risk_candidates(answers, [])
    risks[0].status = RiskCandidateStatus.CONFIRMED

    new_answers = make_answers(outsources_personal_data_processing=False)
    merged = merge_risk_candidates_after_change(risks, new_answers, [])

    vendor_risk = next(r for r in merged if r.risk_id == "RISK-003")
    assert vendor_risk.status == RiskCandidateStatus.CONFIRMED
    assert vendor_risk.needs_review is True


def test_merge_keeps_confirmed_risk_without_needs_review_when_premise_still_holds():
    answers = make_answers(outsources_personal_data_processing=True)
    risks = derive_risk_candidates(answers, [])
    risks[0].status = RiskCandidateStatus.CONFIRMED
    risks[0].impact = 1
    risks[0].likelihood = 1

    new_answers = make_answers(outsources_personal_data_processing=True, stores_personal_data_on_paper=True)
    merged = merge_risk_candidates_after_change(risks, new_answers, [])

    vendor_risk = next(r for r in merged if r.risk_id == "RISK-003")
    assert vendor_risk.status == RiskCandidateStatus.CONFIRMED
    assert vendor_risk.needs_review is False
    # 評価値（利用者が変更した値）も維持される。
    assert vendor_risk.impact == 1
    assert vendor_risk.likelihood == 1


def test_merge_drops_unconfirmed_risk_when_premise_is_lost():
    answers = make_answers(outsources_personal_data_processing=True)
    risks = derive_risk_candidates(answers, [])
    assert risks[0].status == RiskCandidateStatus.CANDIDATE

    new_answers = make_answers(outsources_personal_data_processing=False)
    merged = merge_risk_candidates_after_change(risks, new_answers, [])

    assert not any(r.risk_id == "RISK-003" for r in merged)


# --- デモ状態の操作（利用者確認・評価変更は demo_state 側の役割） ---


@pytest.fixture(autouse=True)
def reset_intake_state():
    intake_demo_state.reset_state()
    yield
    intake_demo_state.reset_state()


def test_case7_confirming_a_risk_marks_it_confirmed():
    intake_demo_state.submit_answers(make_answers(stores_personal_data_on_paper=True))
    target = intake_demo_state.get_state().risks[0]

    intake_demo_state.confirm_risk(target.id)

    updated = next(r for r in intake_demo_state.get_state().risks if r.id == target.id)
    assert updated.status == RiskCandidateStatus.CONFIRMED


def test_case8_excluding_a_risk_is_distinguished_from_confirming():
    intake_demo_state.submit_answers(make_answers(stores_personal_data_on_paper=True))
    target = intake_demo_state.get_state().risks[0]

    intake_demo_state.exclude_risk(target.id)

    updated = next(r for r in intake_demo_state.get_state().risks if r.id == target.id)
    assert updated.status == RiskCandidateStatus.EXCLUDED
    assert updated.status != RiskCandidateStatus.CONFIRMED


def test_case11_user_can_change_impact_and_likelihood():
    intake_demo_state.submit_answers(make_answers(stores_personal_data_on_paper=True))
    target = intake_demo_state.get_state().risks[0]
    intake_demo_state.confirm_risk(target.id)

    intake_demo_state.update_risk_evaluation(target.id, impact=3, likelihood=3)

    updated = next(r for r in intake_demo_state.get_state().risks if r.id == target.id)
    assert updated.impact == 3
    assert updated.likelihood == 3
    assert evaluate_risk(updated).level == RiskLevel.HIGH


def test_case12_confirming_a_risk_alone_does_not_adopt_any_control():
    intake_demo_state.submit_answers(
        make_answers(has_employees=True, outsources_personal_data_processing=True)
    )
    state = intake_demo_state.get_state()
    for risk in state.risks:
        intake_demo_state.confirm_risk(risk.id)

    state = intake_demo_state.get_state()
    assert all(
        suggestion.status.value == "suggested" for suggestion in state.control_suggestions
    )


def test_case15_reset_clears_risk_state():
    intake_demo_state.submit_answers(make_answers(stores_personal_data_on_paper=True))
    target = intake_demo_state.get_state().risks[0]
    intake_demo_state.confirm_risk(target.id)

    intake_demo_state.reset_state()

    assert intake_demo_state.get_state().risks == []
