from pathlib import PurePath

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.document import Document
from app.schemas.document import DocumentDetail, DocumentSummary, PageOut
from app.services.document_service import (
    DuplicateDocumentError,
    NoExtractableTextError,
    create_document,
    get_document,
    list_documents,
)
from app.services.pdf_extractor import InvalidPdfError

router = APIRouter(prefix="/documents", tags=["documents"])

MAX_UPLOAD_BYTES = 20 * 1024 * 1024

# Every PDF starts with these bytes. The Content-Type header is whatever the
# client chose to send, so the file itself is what gets checked.
PDF_SIGNATURE = b"%PDF-"

UNREADABLE_PDF = "The PDF could not be read. Is it corrupted or locked with a password?"
NO_TEXT_PDF = "The PDF has no extractable text. Scanned documents are not supported yet."


def _summary(document: Document, page_count: int) -> DocumentSummary:
    return DocumentSummary(
        id=document.id,
        title=document.title,
        source_url=document.source_url,
        page_count=page_count,
        created_at=document.created_at,
    )


@router.post(
    "",
    status_code=201,
    response_model=DocumentSummary,
    summary="Upload a PDF and store its text page by page",
    responses={
        409: {"description": "This exact file was already ingested"},
        413: {"description": "File larger than 20 MB"},
        415: {"description": "File is not a PDF"},
        422: {"description": "PDF is corrupted, password protected or has no text"},
    },
)
async def upload_document(
    file: UploadFile = File(...),
    title: str | None = Form(None, max_length=300),
    source_url: str | None = Form(None, max_length=2000),
    db: AsyncSession = Depends(get_db),
):
    # Reading one byte past the limit is enough to know the file is too big,
    # without ever holding more than that in memory.
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "File is larger than 20 MB")
    if not data.startswith(PDF_SIGNATURE):
        raise HTTPException(415, "File is not a PDF")

    if not title:
        title = PurePath(file.filename).stem if file.filename else "Untitled"

    try:
        document = await create_document(db, data=data, title=title, source_url=source_url)
    except InvalidPdfError:
        raise HTTPException(422, UNREADABLE_PDF) from None
    except NoExtractableTextError:
        raise HTTPException(422, NO_TEXT_PDF) from None
    except DuplicateDocumentError as exc:
        # The id of the copy already stored lets the client carry on with it
        # instead of treating the conflict as a dead end.
        return JSONResponse(
            status_code=409,
            content={"detail": "This file was already ingested", "document_id": exc.existing_id},
        )

    return _summary(document, len(document.pages))


@router.get("", response_model=list[DocumentSummary], summary="List ingested documents")
async def get_documents(db: AsyncSession = Depends(get_db)):
    return [_summary(document, page_count) for document, page_count in await list_documents(db)]


@router.get(
    "/{document_id}",
    response_model=DocumentDetail,
    summary="One document with the text of every page",
    responses={404: {"description": "No document with this id"}},
)
async def get_document_detail(document_id: int, db: AsyncSession = Depends(get_db)):
    document = await get_document(db, document_id)
    if document is None:
        raise HTTPException(404, "Document not found")

    return DocumentDetail(
        **_summary(document, len(document.pages)).model_dump(),
        pages=[PageOut(number=page.number, text=page.text) for page in document.pages],
    )
