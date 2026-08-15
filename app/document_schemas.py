"""文書生成MVPで扱う最小データモデル。

生成する文書は、企業情報・確認済み個人情報・採用済み管理策・標準テンプレートから
機械的に構成する（AIによる自由作文は行わない）。

事実データ（PersonalInformationCandidate / TrainingControl / VendorControl 等）を
別途複製せず、文書の本文（sections）はそれらの事実データから都度その場で
組み立てる（app.document_templates / app.documents が担う）。ここでは、
組み立てた結果を表現する入れ物としてのモデルのみを定義する。

related_control_ids は、この文書がどの管理策（ControlSuggestion.control_id）に
基づいて生成されたかを表す。文書と管理策の関係を表示テキストだけにせず、
構造化データとして保持する。
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class DocumentType(str, Enum):
    PERSONAL_INFORMATION_LEDGER = "personal_information_ledger"
    EDUCATION_PROCEDURE = "education_procedure"
    VENDOR_MANAGEMENT_PROCEDURE = "vendor_management_procedure"


class DocumentStatus(str, Enum):
    """文書の状態。

    DRAFT: 下書きとして内容は確認できるが、必要な情報が不足している。
    READY: 必要な情報がすべて揃い、文書として利用できる。
    NOT_APPLICABLE: 関連する管理策が採用されていない等の理由で、
        今回のMVPでは正式な生成対象としない。
    """

    DRAFT = "draft"
    READY = "ready"
    NOT_APPLICABLE = "not_applicable"


class DocumentTable(BaseModel):
    headers: list[str]
    rows: list[list[str]]


class DocumentSection(BaseModel):
    heading: str
    paragraphs: list[str] = []
    table: DocumentTable | None = None


class Document(BaseModel):
    document_id: str
    document_type: DocumentType
    title: str
    related_control_ids: list[str] = []
    status: DocumentStatus
    missing_fields: list[str] = []
    sections: list[DocumentSection] = []
