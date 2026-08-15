from app.document_schemas import DocumentStatus, DocumentType
from app.documents import (
    build_all_documents,
    build_education_procedure_document,
    build_personal_information_ledger_document,
    build_vendor_procedure_document,
)
from app.intake_schemas import (
    ControlDecisionStatus,
    ControlSuggestion,
    PersonalInformationCandidate,
    PersonalInformationCandidateStatus,
)
from app.schemas import Company, EmployeeRole, TrainingControl, TrainingFrequency, TrainingPlan
from app.vendor_schemas import AssessmentFrequency, VendorControl

COMPANY = Company(id=1, name="株式会社サンプル", fiscal_year=2026)

FULL_LEDGER_ENTRY = dict(
    acquisition_method="申込フォームからの入力",
    storage_method="社内システムに保存",
    storage_location="社内サーバー",
    outsourced=False,
    third_party_provided=False,
    retention_period="退職後5年",
    disposal_method="システムから削除",
    responsible_role="総務部長",
)


def make_candidate(status=PersonalInformationCandidateStatus.CONFIRMED, **overrides):
    defaults = dict(
        id=1,
        name="従業員情報",
        subject_type="従業員",
        purpose="人事・労務管理",
        reason="従業員がいると回答されたため",
        source_key="has_employees",
        status=status,
    )
    defaults.update(overrides)
    return PersonalInformationCandidate(**defaults)


def make_confirmed_full_candidate(**overrides):
    candidate = make_candidate(**FULL_LEDGER_ENTRY, **overrides)
    return candidate


def make_control_suggestion(control_id, status=ControlDecisionStatus.ADOPTED, **overrides):
    defaults = dict(control_id=control_id, name="管理策", reason="理由", status=status)
    defaults.update(overrides)
    return ControlSuggestion(**defaults)


def make_training_control(**overrides):
    defaults = dict(
        id=1,
        name="個人情報保護教育",
        frequency=TrainingFrequency.ANNUAL,
        target_roles=[EmployeeRole.GENERAL_EMPLOYEE],
        comprehension_required=True,
        material_evidence_required=True,
        approval_required=True,
    )
    defaults.update(overrides)
    return TrainingControl(**defaults)


def make_training_plan(**overrides):
    defaults = dict(
        id=1,
        title="2026年度 個人情報保護教育計画",
        fiscal_year=2026,
        control_id=1,
        material_evidence_registered=False,
        approved=False,
    )
    defaults.update(overrides)
    return TrainingPlan(**defaults)


def make_vendor_control(**overrides):
    defaults = dict(
        id=1,
        name="委託先管理",
        initial_assessment_required=True,
        contract_check_required=True,
        periodic_assessment_required=True,
        assessment_frequency=AssessmentFrequency.ANNUAL,
    )
    defaults.update(overrides)
    return VendorControl(**defaults)


# --- 1. confirmed個人情報が台帳文書へ反映される ---


def test_confirmed_personal_information_is_reflected_in_ledger_document():
    candidate = make_confirmed_full_candidate()

    document = build_personal_information_ledger_document(COMPANY, [candidate])

    table = document.sections[-1].table
    assert table is not None
    assert table.rows[0][0] == "従業員情報"
    assert "社内サーバー" in table.rows[0]


def test_excluded_personal_information_is_not_reflected_in_ledger_document():
    candidate = make_candidate(status=PersonalInformationCandidateStatus.EXCLUDED)

    document = build_personal_information_ledger_document(COMPANY, [candidate])

    table = document.sections[-1].table
    assert table is None or all("従業員情報" not in row for row in table.rows)


# --- 2. 台帳必須情報不足ならreadyにならない ---


def test_ledger_document_is_draft_when_required_fields_missing():
    candidate = make_candidate()  # 台帳必須項目は未入力

    document = build_personal_information_ledger_document(COMPANY, [candidate])

    assert document.status == DocumentStatus.DRAFT
    assert document.missing_fields


def test_ledger_document_is_ready_when_all_required_fields_filled():
    candidate = make_confirmed_full_candidate()

    document = build_personal_information_ledger_document(COMPANY, [candidate])

    assert document.status == DocumentStatus.READY
    assert document.missing_fields == []


def test_ledger_document_is_draft_when_no_confirmed_personal_information():
    document = build_personal_information_ledger_document(COMPANY, [])

    assert document.status == DocumentStatus.DRAFT
    assert document.missing_fields


# --- 3. 教育管理策adoptedなら教育手順を生成 ---


def test_education_procedure_is_generated_when_control_adopted():
    suggestions = [make_control_suggestion("education", ControlDecisionStatus.ADOPTED)]
    control = make_training_control()
    plan = make_training_plan()

    document = build_education_procedure_document(COMPANY, suggestions, control, plan)

    assert document.status == DocumentStatus.READY
    assert document.sections
    headings = [section.heading for section in document.sections]
    assert "目的" in headings
    assert "対象者" in headings
    assert "実施頻度" in headings


def test_education_procedure_reflects_target_roles_and_frequency():
    suggestions = [make_control_suggestion("education", ControlDecisionStatus.ADOPTED)]
    control = make_training_control(target_roles=[EmployeeRole.EXECUTIVE])
    plan = make_training_plan()

    document = build_education_procedure_document(COMPANY, suggestions, control, plan)

    target_section = next(s for s in document.sections if s.heading == "対象者")
    assert "経営者" in target_section.paragraphs[0]
    frequency_section = next(s for s in document.sections if s.heading == "実施頻度")
    assert "年1回" in frequency_section.paragraphs[0]


# --- 4. 教育管理策not_applicableなら正式生成対象にしない ---


def test_education_procedure_is_not_applicable_when_control_not_applicable():
    suggestions = [
        make_control_suggestion(
            "education", ControlDecisionStatus.NOT_APPLICABLE, non_applicable_reason="対象業務なし"
        )
    ]
    control = make_training_control()
    plan = make_training_plan()

    document = build_education_procedure_document(COMPANY, suggestions, control, plan)

    assert document.status == DocumentStatus.NOT_APPLICABLE
    assert document.sections == []
    assert any("対象業務なし" in text for text in document.missing_fields)


def test_education_procedure_is_not_applicable_when_control_only_suggested():
    suggestions = [make_control_suggestion("education", ControlDecisionStatus.SUGGESTED)]
    control = make_training_control()
    plan = make_training_plan()

    document = build_education_procedure_document(COMPANY, suggestions, control, plan)

    assert document.status == DocumentStatus.NOT_APPLICABLE


def test_education_procedure_is_not_applicable_when_control_never_suggested():
    control = make_training_control()
    plan = make_training_plan()

    document = build_education_procedure_document(COMPANY, [], control, plan)

    assert document.status == DocumentStatus.NOT_APPLICABLE


# --- 5. 委託先管理策adoptedなら委託先管理手順を生成 ---


def test_vendor_procedure_is_generated_when_control_adopted():
    suggestions = [make_control_suggestion("vendor_management", ControlDecisionStatus.ADOPTED)]
    control = make_vendor_control()

    document = build_vendor_procedure_document(COMPANY, suggestions, control)

    assert document.status == DocumentStatus.READY
    headings = [section.heading for section in document.sections]
    assert "初回評価" in headings
    assert "契約確認" in headings
    assert "定期評価" in headings


def test_vendor_procedure_is_not_applicable_when_control_not_adopted():
    suggestions = [make_control_suggestion("vendor_management", ControlDecisionStatus.SUGGESTED)]
    control = make_vendor_control()

    document = build_vendor_procedure_document(COMPANY, suggestions, control)

    assert document.status == DocumentStatus.NOT_APPLICABLE
    assert document.sections == []


# --- 6. related_control_idsを保持する ---


def test_documents_keep_related_control_ids():
    suggestions = [
        make_control_suggestion("education", ControlDecisionStatus.ADOPTED),
        make_control_suggestion("vendor_management", ControlDecisionStatus.ADOPTED),
    ]
    documents = build_all_documents(
        company=COMPANY,
        candidates=[make_confirmed_full_candidate()],
        control_suggestions=suggestions,
        education_control=make_training_control(),
        education_plan=make_training_plan(),
        vendor_control=make_vendor_control(),
    )

    ledger = next(d for d in documents if d.document_type == DocumentType.PERSONAL_INFORMATION_LEDGER)
    education = next(d for d in documents if d.document_type == DocumentType.EDUCATION_PROCEDURE)
    vendor = next(d for d in documents if d.document_type == DocumentType.VENDOR_MANAGEMENT_PROCEDURE)

    assert ledger.related_control_ids == []
    assert education.related_control_ids == ["education"]
    assert vendor.related_control_ids == ["vendor_management"]


# --- 7. 元データ変更後にプレビュー内容も変化する ---


def test_ledger_document_changes_after_source_data_changes():
    candidate = make_candidate()
    before = build_personal_information_ledger_document(COMPANY, [candidate])
    assert before.status == DocumentStatus.DRAFT

    for field, value in FULL_LEDGER_ENTRY.items():
        setattr(candidate, field, value)
    after = build_personal_information_ledger_document(COMPANY, [candidate])

    assert after.status == DocumentStatus.READY
    table = after.sections[-1].table
    assert "社内サーバー" in table.rows[0]


def test_education_procedure_changes_after_control_data_changes():
    suggestions = [make_control_suggestion("education", ControlDecisionStatus.ADOPTED)]
    control = make_training_control(comprehension_required=True)
    plan = make_training_plan()

    before = build_education_procedure_document(COMPANY, suggestions, control, plan)
    before_section = next(s for s in before.sections if s.heading == "理解度確認")
    assert "確認する" in before_section.paragraphs[0]

    control.comprehension_required = False
    after = build_education_procedure_document(COMPANY, suggestions, control, plan)
    after_section = next(s for s in after.sections if s.heading == "理解度確認")
    assert "必須としない" in after_section.paragraphs[0]
