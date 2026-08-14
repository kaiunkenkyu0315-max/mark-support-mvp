import pytest

from app import intake_demo_state
from app.intake import (
    derive_personal_information_candidates,
    merge_candidates_after_answers_change,
    merge_control_suggestions_after_answers_change,
    recommend_controls,
)
from app.intake_schemas import (
    ControlDecisionStatus,
    PersonalInformationCandidateStatus,
    QuestionnaireAnswers,
)


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


# --- 個人情報候補・管理策候補の生成ロジック（純粋関数） ---


def test_case3_employees_yes_yields_employee_information_candidate():
    answers = make_answers(has_employees=True)

    candidates = derive_personal_information_candidates(answers)

    employee_candidate = next(c for c in candidates if c.name == "従業員情報")
    assert employee_candidate.status == PersonalInformationCandidateStatus.CANDIDATE


def test_case4_employees_no_does_not_yield_employee_information_candidate():
    answers = make_answers(has_employees=False)

    candidates = derive_personal_information_candidates(answers)

    assert not any(c.name == "従業員情報" for c in candidates)


def test_case5_recruiting_yes_yields_applicant_information_candidate():
    answers = make_answers(recruits_people=True)

    candidates = derive_personal_information_candidates(answers)

    assert any(c.name == "採用応募者情報" for c in candidates)


def test_case6_outsourcing_yes_yields_vendor_management_suggestion():
    answers = make_answers(outsources_personal_data_processing=True)

    suggestions = recommend_controls(answers)

    assert any(s.control_id == "vendor_management" for s in suggestions)


def test_unanswered_questionnaire_yields_no_candidates_or_suggestions():
    answers = QuestionnaireAnswers()

    assert derive_personal_information_candidates(answers) == []
    assert recommend_controls(answers) == []


# --- 回答変更時の再計算（merge_*） ---


def test_merge_candidates_keeps_confirmed_decision_when_premise_still_holds():
    answers = make_answers(has_employees=True)
    candidates = derive_personal_information_candidates(answers)
    candidates[0].status = PersonalInformationCandidateStatus.CONFIRMED

    # 従業員の有無以外の回答が増えても、既存の確認済み判断は維持される。
    new_answers = make_answers(has_employees=True, receives_inquiries=True)
    merged = merge_candidates_after_answers_change(candidates, new_answers)

    employee_candidate = next(c for c in merged if c.name == "従業員情報")
    assert employee_candidate.status == PersonalInformationCandidateStatus.CONFIRMED
    assert employee_candidate.needs_review is False


def test_merge_candidates_flags_needs_review_when_confirmed_premise_is_lost():
    answers = make_answers(has_employees=True)
    candidates = derive_personal_information_candidates(answers)
    candidates[0].status = PersonalInformationCandidateStatus.CONFIRMED

    # 従業員なしに回答が変わっても、確認済みだった候補は消さず要再確認にする。
    new_answers = make_answers(has_employees=False)
    merged = merge_candidates_after_answers_change(candidates, new_answers)

    employee_candidate = next(c for c in merged if c.name == "従業員情報")
    assert employee_candidate.status == PersonalInformationCandidateStatus.CONFIRMED
    assert employee_candidate.needs_review is True


def test_merge_candidates_drops_unconfirmed_candidate_when_premise_is_lost():
    answers = make_answers(has_employees=True)
    candidates = derive_personal_information_candidates(answers)
    assert candidates[0].status == PersonalInformationCandidateStatus.CANDIDATE

    new_answers = make_answers(has_employees=False)
    merged = merge_candidates_after_answers_change(candidates, new_answers)

    assert not any(c.name == "従業員情報" for c in merged)


def test_merge_control_suggestions_keeps_adopted_decision_when_premise_still_holds():
    answers = make_answers(has_employees=True)
    suggestions = recommend_controls(answers)
    suggestions[0].status = ControlDecisionStatus.ADOPTED

    new_answers = make_answers(has_employees=True, receives_inquiries=True)
    merged = merge_control_suggestions_after_answers_change(suggestions, new_answers)

    education = next(s for s in merged if s.control_id == "education")
    assert education.status == ControlDecisionStatus.ADOPTED


def test_merge_control_suggestions_flags_needs_review_when_adopted_premise_is_lost():
    answers = make_answers(has_employees=True)
    suggestions = recommend_controls(answers)
    suggestions[0].status = ControlDecisionStatus.ADOPTED

    new_answers = make_answers(has_employees=False)
    merged = merge_control_suggestions_after_answers_change(suggestions, new_answers)

    education = next(s for s in merged if s.control_id == "education")
    assert education.status == ControlDecisionStatus.ADOPTED
    assert education.needs_review is True


# --- デモ状態の操作（利用者回答・確認・採用は demo_state 側の役割） ---


@pytest.fixture(autouse=True)
def reset_intake_state():
    intake_demo_state.reset_state()
    yield
    intake_demo_state.reset_state()


def test_case1_starts_in_unanswered_state():
    state = intake_demo_state.get_state()

    assert state.answers_submitted is False
    assert state.candidates == []
    assert state.control_suggestions == []


def test_case2_submitting_answers_saves_them_and_generates_candidates():
    answers = make_answers(has_employees=True, outsources_personal_data_processing=True)

    intake_demo_state.submit_answers(answers)

    state = intake_demo_state.get_state()
    assert state.answers_submitted is True
    assert any(c.name == "従業員情報" for c in state.candidates)
    assert any(s.control_id == "vendor_management" for s in state.control_suggestions)


def test_case7_candidate_generation_alone_does_not_confirm():
    intake_demo_state.submit_answers(make_answers(has_employees=True))

    state = intake_demo_state.get_state()
    assert state.candidates
    assert all(c.status == PersonalInformationCandidateStatus.CANDIDATE for c in state.candidates)


def test_case8_confirming_a_candidate_marks_it_confirmed():
    intake_demo_state.submit_answers(make_answers(has_employees=True))
    target = intake_demo_state.get_state().candidates[0]

    intake_demo_state.confirm_candidate(target.id)

    updated = next(c for c in intake_demo_state.get_state().candidates if c.id == target.id)
    assert updated.status == PersonalInformationCandidateStatus.CONFIRMED


def test_case9_excluding_a_candidate_is_distinguished_from_confirming():
    intake_demo_state.submit_answers(make_answers(has_employees=True))
    target = intake_demo_state.get_state().candidates[0]

    intake_demo_state.exclude_candidate(target.id)

    updated = next(c for c in intake_demo_state.get_state().candidates if c.id == target.id)
    assert updated.status == PersonalInformationCandidateStatus.EXCLUDED
    assert updated.status != PersonalInformationCandidateStatus.CONFIRMED


def test_case10_control_suggestion_alone_does_not_adopt():
    intake_demo_state.submit_answers(make_answers(has_employees=True))

    state = intake_demo_state.get_state()
    assert state.control_suggestions
    assert all(
        s.status == ControlDecisionStatus.SUGGESTED for s in state.control_suggestions
    )


def test_case11_adopting_a_control_marks_it_adopted():
    intake_demo_state.submit_answers(make_answers(has_employees=True))
    target = intake_demo_state.get_state().control_suggestions[0]

    intake_demo_state.adopt_control(target.control_id)

    updated = next(
        s
        for s in intake_demo_state.get_state().control_suggestions
        if s.control_id == target.control_id
    )
    assert updated.status == ControlDecisionStatus.ADOPTED


def test_case12_marking_not_applicable_preserves_reason():
    intake_demo_state.submit_answers(make_answers(has_employees=True))
    target = intake_demo_state.get_state().control_suggestions[0]

    intake_demo_state.mark_control_not_applicable(target.control_id, "対象業務がないため")

    updated = next(
        s
        for s in intake_demo_state.get_state().control_suggestions
        if s.control_id == target.control_id
    )
    assert updated.status == ControlDecisionStatus.NOT_APPLICABLE
    assert updated.non_applicable_reason == "対象業務がないため"


def test_case14_reset_restores_unanswered_state():
    intake_demo_state.submit_answers(make_answers(has_employees=True))
    intake_demo_state.adopt_control("education")

    intake_demo_state.reset_state()

    state = intake_demo_state.get_state()
    assert state.answers_submitted is False
    assert state.candidates == []
    assert state.control_suggestions == []
