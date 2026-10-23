"""Build tiny, valid PDFs in memory for tests.

A real PDF from the corpus would weigh hundreds of kilobytes, most of it
embedded fonts, and its text could change with the next version of the
document. These are a few hundred bytes and contain exactly the text each
test asserts on.
"""


def _escape(text: str) -> bytes:
    # Inside a PDF string literal, backslash and parentheses are syntax.
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    # WinAnsiEncoding is cp1252, which covers Portuguese accents.
    return escaped.encode("cp1252")


def _content_stream(text: str) -> bytes:
    """Draw each line of text below the previous one. Empty text draws nothing."""
    if not text:
        return b""
    lines = text.split("\n")
    body = b"BT /F1 12 Tf 72 770 Td 14 TL "
    body += b" T* ".join(b"(" + _escape(line) + b") Tj" for line in lines)
    return body + b" ET"


def make_pdf(pages: list[str]) -> bytes:
    """Return a PDF with one page per string. An empty string is a blank page."""
    # Fixed objects: 1 catalog, 2 page tree, 3 font. Each page then takes two
    # objects, the page itself and its content stream.
    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"",  # page tree, filled once the page numbers are known
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
    ]
    page_refs = []
    for text in pages:
        page_number = len(objects) + 1
        content_number = page_number + 1
        page_refs.append(f"{page_number} 0 R".encode())
        objects.append(
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            b"/Resources << /Font << /F1 3 0 R >> >> "
            + f"/Contents {content_number} 0 R >>".encode()
        )
        stream = _content_stream(text)
        objects.append(
            f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream"
        )
    objects[1] = (
        b"<< /Type /Pages /Kids [" + b" ".join(page_refs) + b"] "
        + f"/Count {len(pages)} >>".encode()
    )

    # The cross-reference table lists the byte offset of every object, which
    # is how a reader jumps straight to one without scanning the whole file.
    output = b"%PDF-1.4\n"
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(output))
        output += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"

    xref_offset = len(output)
    output += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    output += b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets)
    output += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n"
    ).encode()
    return output
