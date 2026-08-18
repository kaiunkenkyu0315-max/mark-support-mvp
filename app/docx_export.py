"""登録済みPMSデータをWord (.docx) として出力する最小生成層。

追加ライブラリに依存せず、Office Open XMLの最小構成を標準ライブラリだけで生成する。
ここでは業務判定は行わず、呼び出し側が「出力可能な状態か」を判断したうえで、
渡された事実データを文書化する。
"""

from __future__ import annotations

from html import escape
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from app.document_schemas import Document
from app.documents import CONTROL_NAME_LABELS
from app.schemas import ComprehensionResult, EducationDemoState if False else TrainingPlan


CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>
"""

PACKAGE_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>
"""

DOCUMENT_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>
"""


def _text(value: object | None) -> str:
    if value is None:
        return "未登録"
    text = str(value)
    return text if text else "未登録"


def _run(text: object, *, bold: bool = False, size: int | None = None) -> str:
    props: list[str] = []
    if bold:
        props.append("<w:b/>")
    if size:
        props.append(f'<w:sz w:val="{size}"/>')
    rpr = f"<w:rPr>{''.join(props)}</w:rPr>" if props else ""
    return f'<w:r>{rpr}<w:t xml:space="preserve">{escape(str(text))}</w:t></w:r>'


def _paragraph(text: object = "", *, bold: bool = False, size: int | None = None) -> str:
    return f"<w:p>{_run(text, bold=bold, size=size)}</w:p>"


def _heading(text: object, level: int = 1) -> str:
    size = {1: 32, 2: 26, 3: 22}.get(level, 22)
    return _paragraph(text, bold=True, size=size)


def _cell(text: object, *, bold: bool = False) -> str:
    return (
        '<w:tc><w:tcPr><w:tcW w:w="2400" w:type="dxa"/></w:tcPr>'
        + _paragraph(text, bold=bold)
        + "</w:tc>"
    )


def _table(headers: list[str], rows: list[list[object]]) -> str:
    header_row = "<w:tr>" + "".join(_cell(header, bold=True) for header in headers) + "</w:tr>"
    body_rows = "".join(
        "<w:tr>" + "".join(_cell(value) for value in row) + "</w:tr>" for row in rows
    )
    return (
        "<w:tbl>"
        '<w:tblPr><w:tblBorders>'
        '<w:top w:val="single" w:sz="4" w:color="BFBFBF"/>'
        '<w:left w:val="single" w:sz="4" w:color="BFBFBF"/>'
        '<w:bottom w:val="single" w:sz="4" w:color="BFBFBF"/>'
        '<w:right w:val="single" w:sz="4" w:color="BFBFBF"/>'
        '<w:insideH w:val="single" w:sz="4" w:color="D9D9D9"/>'
        '<w:insideV w:val="single" w:sz="4" w:color="D9D9D9"/>'
        "</w:tblBorders></w:tblPr>"
        + header_row
        + body_rows
        + "</w:tbl>"
    )


def _package(body_parts: list[str]) -> bytes:
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>"
        + "".join(body_parts)
        + '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134" '
        'w:header="708" w:footer="708" w:gutter="0"/></w:sectPr>'
        "</w:body></w:document>"
    )
    stream = BytesIO()
    with ZipFile(stream, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", CONTENT_TYPES)
        archive.writestr("_rels/.rels", PACKAGE_RELS)
        archive.writestr("word/document.xml", document_xml)
        archive.writestr("word/_rels/document.xml.rels", DOCUMENT_RELS)
    return stream.getvalue()


def build_document_docx(document: Document) -> bytes:
    """既存Documentプレビューと同じ内容をWord化する。"""

    parts = [_heading(document.title), _paragraph("現在の登録情報から生成したPMS文書です。")]
    for section in document.sections:
        parts.append(_heading(section.heading, 2))
        parts.extend(_paragraph(text) for text in section.paragraphs)
        if section.table:
            parts.append(_table(section.table.headers, section.table.rows))
    return _package(parts)


def build_pms_document_list_docx(documents: list[Document]) -> bytes:
    status_labels = {
        "ready": "準備完了",
        "draft": "下書き（情報不足）",
        "not_applicable": "未生成（管理策未採用）",
    }
    rows: list[list[object]] = []
    for document in documents:
        controls = "、".join(
            CONTROL_NAME_LABELS.get(control_id, control_id)
            for control_id in document.related_control_ids
        ) or "—"
        rows.append(
            [
                document.title,
                status_labels.get(document.status.value, document.status.value),
                controls,
            ]
        )
    return _package(
        [
            _heading("PMS文書一覧"),
            _paragraph("現在の登録情報から生成・判定されているPMS文書の一覧です。"),
            _table(["文書名", "状態", "関連する管理策"], rows),
        ]
    )


def build_education_record_docx(state) -> bytes:
    """教育計画・実施・受講・理解度・承認の事実記録をWord化する。"""

    plan = state.plan
    employee_by_id = {employee.id: employee for employee in state.employees}
    record_rows: list[list[object]] = []
    for record in state.records:
        employee = employee_by_id.get(record.employee_id)
        if employee is None:
            continue
        comprehension = {
            ComprehensionResult.PASSED: "合格・確認済み",
            ComprehensionResult.FAILED: "不合格・要再教育",
            None: "未登録",
        }[record.comprehension_result]
        record_rows.append(
            [
                employee.name,
                employee.role.value,
                "受講済み" if record.completed else "未受講",
                _text(record.completed_on),
                comprehension,
            ]
        )

    summary_rows = [
        ["年度", plan.fiscal_year],
        ["教育名称", plan.title],
        ["実施日", _text(plan.execution_date)],
        ["実施方法", _text(plan.delivery_method)],
        ["教材", _text(plan.material_name)],
        ["実施責任者", _text(plan.instructor_name)],
        ["理解度確認方法", _text(plan.comprehension_method)],
        ["承認者", _text(plan.approved_by)],
        ["承認日", _text(plan.approved_at)],
    ]

    return _package(
        [
            _heading(f"{plan.fiscal_year}年度 個人情報保護教育 実施記録"),
            _paragraph(f"会社名：{state.company.name}"),
            _heading("教育実施概要", 2),
            _table(["項目", "記録内容"], summary_rows),
            _heading("受講・理解度確認記録", 2),
            _table(["氏名", "役割", "受講状態", "受講日", "理解度確認"], record_rows),
        ]
    )
