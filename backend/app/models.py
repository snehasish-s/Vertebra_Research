from typing import Literal
from pydantic import BaseModel, Field, field_validator


class Document(BaseModel):
    id: str
    title: str
    status: Literal['extracting', 'embedding', 'ready', 'error', 'deleting'] = 'extracting'
    page_count: int = 0
    chunk_count: int = 0
    error: str | None = None
    created_at: str
    estimated_cost_usd: float = 0


class Chunk(BaseModel):
    id: str
    document_id: str
    title: str
    page_number: int
    chunk_order: int
    text: str
    embedding: list[float] = Field(default_factory=list)
    score: float = 0


class Question(BaseModel):
    question: str = Field(min_length=3, max_length=1500)

    @field_validator('question')
    @classmethod
    def trim_question(cls, value):
        if len(value.strip()) < 3:
            raise ValueError('Please enter a question with at least three characters.')
        return value.strip()


class Claim(BaseModel):
    text: str
    source_ids: list[str]


class ModelAnswer(BaseModel):
    insufficient_evidence: bool
    claims: list[Claim]


class Citation(BaseModel):
    id: str
    document_id: str
    title: str
    page_number: int
    excerpt: str


class Answer(BaseModel):
    answer: str
    claims: list[Claim]
    citations: list[Citation]
    abstained: bool
    latency_ms: int
    estimated_cost_usd: float
    mode: str
