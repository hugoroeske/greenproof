"""Step 1: turn a PDF into a list of sentences with page numbers."""
from __future__ import annotations

import io
import re
from dataclasses import dataclass

from pypdf import PdfReader


@dataclass
class Sentence:
    page: int
    text: str


_ABBREVIATIONS = ("e.g.", "i.e.", "etc.", "approx.", "vs.", "incl.", "no.", "co.", "ltd.", "inc.", "fig.")


def _clean_page_text(text: str) -> str:
    text = text.replace("­", "")              # soft hyphens
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)   # words split across lines
    text = text.replace("•", "\n").replace("▪", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    return text


def _paragraphs(text: str) -> list[str]:
    """Re-join lines that were wrapped by the PDF layout; keep real paragraph breaks."""
    paragraphs, current = [], []
    for line in text.split("\n"):
        line = line.strip()
        if not line:                                  # blank line = paragraph break
            if current:
                paragraphs.append(" ".join(current))
                current = []
            continue
        if current:
            prev = current[-1]
            ends_sentence = prev.endswith((".", "!", "?", ":"))
            looks_like_heading = len(prev.split()) <= 6 and not prev.endswith((",", ";", "-"))
            if ends_sentence or looks_like_heading:
                paragraphs.append(" ".join(current))
                current = []
        current.append(line)
    if current:
        paragraphs.append(" ".join(current))
    return paragraphs


def split_sentences(text: str) -> list[str]:
    """Simple rule-based sentence splitter that keeps numbers like 2.5% intact."""
    sentences: list[str] = []
    for block in _paragraphs(text):
        block = " ".join(block.split())
        if not block:
            continue
        protected = block
        for abbr in _ABBREVIATIONS:
            protected = re.sub(re.escape(abbr), abbr.replace(".", "<DOT>"), protected, flags=re.IGNORECASE)
        parts = re.split(r"(?<=[.!?])\s+(?=[A-Z\"“(])", protected)
        sentences.extend(p.replace("<DOT>", ".").strip() for p in parts if p.strip())
    return sentences


def _is_usable(sentence: str) -> bool:
    words = sentence.split()
    if len(words) < 4 or len(words) > 90:
        return False
    letters = sum(c.isalpha() for c in sentence)
    if letters / max(len(sentence), 1) < 0.55:     # mostly numbers -> table row
        return False
    return True


def _pages_pypdf(pdf_bytes: bytes) -> list[str]:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception:  # damaged page – keep the page number, skip the text
            pages.append("")
    return pages


def _pages_pdfplumber(pdf_bytes: bytes) -> list[str]:
    import pdfplumber
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        return [(p.extract_text() or "") for p in pdf.pages]


def extract_pages(pdf_bytes: bytes) -> list[str]:
    """Raw text per page (cleaned). Falls back to pdfplumber if pypdf finds almost no text."""
    pages = _pages_pypdf(pdf_bytes)
    if sum(len(p.strip()) for p in pages) < 100 * max(1, len(pages) // 4):
        try:
            alt = _pages_pdfplumber(pdf_bytes)
            if sum(map(len, alt)) > sum(map(len, pages)):
                pages = alt
        except Exception:
            pass
    return [_clean_page_text(p) for p in pages]


def sentences_from_pages(pages: list[str]) -> list[Sentence]:
    result: list[Sentence] = []
    seen: set[str] = set()
    for page_no, text in enumerate(pages, start=1):
        for s in split_sentences(text):
            key = s.lower()
            if _is_usable(s) and key not in seen:   # repeated headers/footers only once
                seen.add(key)
                result.append(Sentence(page=page_no, text=s))
    return result


def extract_sentences(pdf_bytes: bytes) -> list[Sentence]:
    return sentences_from_pages(extract_pages(pdf_bytes))
