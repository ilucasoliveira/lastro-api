from io import BytesIO

import pytest
from pypdf import PdfReader, PdfWriter

from app.services.pdf_extractor import InvalidPdfError, extract_pages
from tests.pdf_factory import make_pdf


def test_returns_one_entry_per_page_in_order():
    data = make_pdf(["Primeira página", "Segunda página", "Terceira página"])

    pages = extract_pages(data)

    assert len(pages) == 3
    assert "Primeira" in pages[0]
    assert "Segunda" in pages[1]
    assert "Terceira" in pages[2]


def test_keeps_portuguese_accents():
    pages = extract_pages(make_pdf(["Transação concluída em até 10 segundos"]))

    assert "Transação concluída" in pages[0]


def test_nul_characters_are_removed_because_postgres_rejects_them():
    pages = extract_pages(make_pdf(["Pix\x00 instantâneo"]))

    assert "\x00" not in pages[0]
    assert "Pix instantâneo" in pages[0]


def test_blank_page_stays_in_place_so_page_numbers_do_not_shift():
    pages = extract_pages(make_pdf(["Antes", "", "Depois"]))

    assert len(pages) == 3
    assert pages[1].strip() == ""
    assert "Depois" in pages[2]


@pytest.mark.parametrize(
    "data",
    [b"", b"not a pdf at all", b"%PDF-1.7\nthe header is right but nothing else is"],
    ids=["empty", "not-a-pdf", "truncated"],
)
def test_unreadable_bytes_raise_invalid_pdf_error(data):
    with pytest.raises(InvalidPdfError):
        extract_pages(data)


def _encrypt(data: bytes, user_password: str, algorithm: str) -> bytes:
    writer = PdfWriter(clone_from=PdfReader(BytesIO(data)))
    writer.encrypt(user_password=user_password, owner_password="owner", algorithm=algorithm)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


@pytest.mark.parametrize("algorithm", ["RC4-128", "AES-256"])
def test_pdf_locked_with_a_password_raises_invalid_pdf_error(algorithm):
    data = _encrypt(make_pdf(["Segredo"]), user_password="secret", algorithm=algorithm)

    with pytest.raises(InvalidPdfError):
        extract_pages(data)


@pytest.mark.parametrize("algorithm", ["RC4-128", "AES-256"])
def test_pdf_with_only_permission_restrictions_is_still_read(algorithm):
    # Government PDFs are often encrypted with an empty user password: anyone
    # can open them, and the encryption only restricts printing or copying.
    data = _encrypt(make_pdf(["Regulamento do Pix"]), user_password="", algorithm=algorithm)

    assert "Regulamento do Pix" in extract_pages(data)[0]
