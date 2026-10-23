from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError


class InvalidPdfError(Exception):
    """Raised when the uploaded bytes cannot be read as a PDF."""


def extract_pages(data: bytes) -> list[str]:
    """Return the text of every page, in order. Index 0 is page 1.

    Pages without extractable text (scanned images) come back as an empty
    string instead of being dropped, so page numbers stay aligned: dropping
    one would make every citation after it point at the wrong page.

    The text is otherwise returned as pypdf extracts it. Cleaning it up
    (repeated headers, line breaks from the layout) belongs to chunking,
    where the decisions about what counts as noise are made.
    """
    try:
        reader = PdfReader(BytesIO(data))
        # Encrypted PDFs open fine and only fail on the first page read, so
        # extraction stays inside the try to turn that into the same error.
        return [_strip_nul(page.extract_text() or "") for page in reader.pages]
    except PdfReadError as exc:
        raise InvalidPdfError(str(exc)) from exc


def _strip_nul(text: str) -> str:
    # Some PDFs map glyphs to the NUL character, and PostgreSQL refuses NUL in
    # a text column, failing the whole insert over one invisible character.
    return text.replace("\x00", "")
