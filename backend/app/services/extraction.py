from io import BytesIO
import re
from uuid import uuid4

from pypdf import PdfReader

from app.models import Chunk


class DocumentError(ValueError):
    """A problem we can explain safely to the person uploading a document."""


def extract_pages(content: bytes, max_pages: int) -> list[tuple[int, str]]:
    if not content.startswith(b'%PDF-'):
        raise DocumentError('This file does not appear to be a PDF.')
    try:
        reader = PdfReader(BytesIO(content), strict=False)
        if reader.is_encrypted:
            raise DocumentError('Password-protected PDFs are not supported. Upload an unlocked copy.')
        if len(reader.pages) > max_pages:
            raise DocumentError(f'Please use a PDF with at most {max_pages} pages.')
        pages = []
        total_characters = 0
        for number, page in enumerate(reader.pages, start=1):
            text = re.sub(r'\s+', ' ', page.extract_text() or '').strip()
            total_characters += len(text)
            if total_characters > 600_000:
                raise DocumentError('This PDF contains too much text. Split it into smaller documents.')
            pages.append((number, text))
    except DocumentError:
        raise
    except Exception as exc:
        raise DocumentError('We could not read this PDF. Try exporting a new PDF copy.') from exc
    if not any(text for _, text in pages):
        raise DocumentError('No extractable text was found. This may be a scanned PDF. OCR is not included in version 1.')
    return pages


def chunk_pages(document_id: str, title: str, pages: list[tuple[int, str]],
                size: int = 1400, overlap: int = 200) -> list[Chunk]:
    """Stay inside each physical PDF page so citations cannot drift across pages."""
    if size <= overlap or overlap < 0:
        raise ValueError('Chunk size must be larger than overlap.')
    chunks = []
    for page_number, text in pages:
        start = 0
        while start < len(text):
            end = min(start + size, len(text))
            # Prefer a word boundary but always make progress, including unbroken text.
            boundary = text.rfind(' ', start + size // 2, end)
            if end < len(text) and boundary > start:
                end = boundary
            chunks.append(Chunk(id=str(uuid4()), document_id=document_id, title=title,
                                page_number=page_number, chunk_order=len(chunks), text=text[start:end]))
            if end == len(text):
                break
            start = max(start + 1, end - overlap)
    if len(chunks) > 600:
        raise DocumentError('This PDF creates too many passages. Split it into smaller documents.')
    return chunks
