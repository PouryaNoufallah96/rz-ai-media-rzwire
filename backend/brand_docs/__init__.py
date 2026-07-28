"""Load authoritative brand documents for promo generation and chat retrieval.

Supported source formats are Markdown, DOCX, and PDF. Each brand may have one
or more sources. Sources are loaded once at import time and cached in memory. A
missing or unreadable document never prevents the server from starting; callers
can provide a short fallback pitch instead.
"""

import sys
import threading
from pathlib import Path

try:
    from docx import Document

    _DOCX_AVAILABLE = True
except ImportError:
    _DOCX_AVAILABLE = False

try:
    from pypdf import PdfReader

    _PDF_AVAILABLE = True
except ImportError:
    _PDF_AVAILABLE = False


_HERE = Path(__file__).parent

# Brand display name -> authoritative source filenames, in precedence order.
_BRAND_FILES = {
    'MGC Coin': ('MGC Coin.pdf', 'MGC Social Channels.md'),
    'Ranking Platform': ('Ranking Platform.md', 'Ranking Social Channels.md'),
    'Oasis Coin': ('OASIS Token.pdf', 'OASIS Website.md', 'Oasis Social Channels.md'),
    'Jewelry Coin': ('Jewelry Coin.md', 'Jewelry Social Channels.md'),
}

_cache: dict[str, str] = {}
_source_cache: dict[str, tuple[tuple[str, str], ...]] = {}
_loaded = False
_lock = threading.Lock()


def _read_docx(path: Path) -> str:
    """Extract plain text from a DOCX, preserving paragraph boundaries."""
    doc = Document(str(path))
    return '\n'.join(paragraph.text for paragraph in doc.paragraphs)


def _read_pdf(path: Path) -> str:
    """Extract searchable PDF text while preserving page boundaries."""
    reader = PdfReader(str(path))
    pages = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or '').replace('\ufffd', '-').strip()
        if text:
            pages.append(f'[Page {page_number}]\n{text}')
    return '\n\n'.join(pages)


def _read_brand_file(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == '.md':
        return path.read_text(encoding='utf-8')
    if suffix == '.docx':
        if not _DOCX_AVAILABLE:
            raise RuntimeError('python-docx is not installed')
        return _read_docx(path)
    if suffix == '.pdf':
        if not _PDF_AVAILABLE:
            raise RuntimeError('pypdf is not installed')
        return _read_pdf(path)
    raise ValueError(f'unsupported brand-document format: {suffix}')


def _combine_sources(sources: tuple[tuple[str, str], ...]) -> str:
    if len(sources) == 1:
        return sources[0][1]
    return '\n\n'.join(
        f'===== AUTHORITATIVE SOURCE: {filename} =====\n{text}'
        for filename, text in sources
    )


def _load_all() -> None:
    """Populate the caches once. Safe to call from multiple threads."""
    global _loaded
    if _loaded:
        return
    with _lock:
        if _loaded:
            return
        for brand, filenames in _BRAND_FILES.items():
            loaded_sources = []
            for filename in filenames:
                path = _HERE / filename
                try:
                    text = _read_brand_file(path)
                    if text and text.strip():
                        loaded_sources.append((filename, text.strip()))
                        print(
                            f'[brand_docs] loaded source: {brand} / {filename} '
                            f'({len(text)} chars)',
                            file=sys.stderr,
                        )
                    else:
                        print(
                            f'[brand_docs] WARNING {filename} is empty - source skipped',
                            file=sys.stderr,
                        )
                except Exception as exc:  # noqa: BLE001
                    print(
                        f'[brand_docs] WARNING could not read {filename}: {exc} - '
                        'source skipped',
                        file=sys.stderr,
                    )
            if loaded_sources:
                sources = tuple(loaded_sources)
                _source_cache[brand] = sources
                _cache[brand] = _combine_sources(sources)
            else:
                print(
                    f'[brand_docs] WARNING no source loaded for {brand} - uses fallback',
                    file=sys.stderr,
                )
        _loaded = True


def get_brand_doc(brand: str, fallback: str = '') -> str:
    """Return all authoritative sources for a brand, or a short fallback."""
    if not _loaded:
        _load_all()
    return _cache.get(brand) or fallback


def get_brand_documents(brand: str) -> tuple[tuple[str, str], ...]:
    """Return individual ``(filename, text)`` sources for chat indexing."""
    if not _loaded:
        _load_all()
    return _source_cache.get(brand, ())


def available_brands() -> tuple[str, ...]:
    """Return brands with configured authoritative sources."""
    return tuple(_BRAND_FILES)


def get_brand_source_path(brand: str) -> str:
    """Return the primary configured source filename for compatibility."""
    filenames = _BRAND_FILES.get(brand, ())
    return filenames[0] if filenames else ''


_load_all()
