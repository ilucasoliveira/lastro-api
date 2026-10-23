import asyncio
import hashlib

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.document import Document, Page
from app.services.pdf_extractor import extract_pages


class NoExtractableTextError(Exception):
    """Raised when a PDF opens fine but none of its pages contain text."""


class DuplicateDocumentError(Exception):
    """Raised when the exact same file was already ingested."""

    def __init__(self, existing_id: int):
        super().__init__(f"Document already ingested with id {existing_id}")
        self.existing_id = existing_id


async def create_document(
    db: AsyncSession, *, data: bytes, title: str, source_url: str | None
) -> Document:
    """Extract the text of a PDF and store it page by page in one transaction."""
    # Parsing a PDF is pure CPU work. Run on the event loop, a 300 page file
    # would freeze every other request this process is serving until it ends.
    pages = await asyncio.to_thread(extract_pages, data)
    if not any(text.strip() for text in pages):
        raise NoExtractableTextError

    sha256 = hashlib.sha256(data).hexdigest()
    document = Document(
        title=title,
        source_url=source_url,
        sha256=sha256,
        pages=[Page(number=number, text=text) for number, text in enumerate(pages, start=1)],
    )
    db.add(document)

    # No "does it exist yet?" query first. The unique constraint on sha256 is
    # the only check that holds when two uploads of the same file race each
    # other, so it is the one relied on, and a duplicate is recognised by the
    # insert failing.
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        existing_id = await db.scalar(select(Document.id).where(Document.sha256 == sha256))
        if existing_id is None:
            # The constraint that failed was not the duplicate check.
            raise
        raise DuplicateDocumentError(existing_id) from None

    return document


async def list_documents(db: AsyncSession) -> list[tuple[Document, int]]:
    """Every document with its page count, newest first, without loading the pages."""
    statement = (
        select(Document, func.count(Page.id))
        .outerjoin(Page)
        .group_by(Document.id)
        .order_by(Document.created_at.desc())
    )
    result = await db.execute(statement)
    return [(document, page_count) for document, page_count in result.all()]


async def get_document(db: AsyncSession, document_id: int) -> Document | None:
    statement = (
        select(Document).options(selectinload(Document.pages)).where(Document.id == document_id)
    )
    return await db.scalar(statement)
