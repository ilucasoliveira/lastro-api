from datetime import datetime

from pydantic import BaseModel


class DocumentSummary(BaseModel):
    id: int
    title: str
    source_url: str | None
    page_count: int
    created_at: datetime


class PageOut(BaseModel):
    number: int
    text: str


class DocumentDetail(DocumentSummary):
    pages: list[PageOut]
