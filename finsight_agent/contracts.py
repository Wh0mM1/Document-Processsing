from pydantic import BaseModel, Field


class Citation(BaseModel):
    document_id: str
    chunk_id: str
    page: int
    excerpt: str


class StructuredFact(BaseModel):
    label: str
    value: str | None
    period: str | None = None
    status: str = "supported"
    citations: list[Citation] = Field(min_length=1)


class ChartPoint(BaseModel):
    period: str
    value: float | None
    unit: str
    citations: list[Citation] = Field(min_length=1)


class ChartSpec(BaseModel):
    title: str
    metric: str
    points: list[ChartPoint]


class NarrativeSection(BaseModel):
    title: str
    text: str
    citations: list[Citation] = Field(min_length=1)


class ReportDraft(BaseModel):
    structured_data: list[StructuredFact]
    chart_specs: list[ChartSpec]
    narrative_sections: list[NarrativeSection]


class RevisionRequest(BaseModel):
    section_id: str
    user_instruction: str = Field(min_length=1, max_length=2000)
