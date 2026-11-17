"""Resume parsing: validation and text extraction from PDF / TXT uploads."""

import os
import re

from config import ALLOWED_EXTENSIONS

try:
    import pymupdf  # PyMuPDF >= 1.24
except ImportError:  # pragma: no cover
    try:
        import fitz as pymupdf  # older PyMuPDF
    except ImportError:
        pymupdf = None


class ResumeParseError(Exception):
    """Raised when a resume cannot be read or parsed."""


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def validate_pdf(file_stream, filename):
    """Validate that the upload is a readable PDF within size limits."""
    ext = filename.rsplit(".", 1)[1].lower() if "." in filename else ""
    if ext != "pdf":
        raise ResumeParseError("Please upload a valid PDF file.")

    header = file_stream.read(5)
    file_stream.seek(0)
    if header != b"%PDF-":
        raise ResumeParseError("The uploaded file is not a valid PDF.")

    return True


def extract_pdf_text(file_stream):
    """Extract text from a PDF file-like object."""
    if pymupdf is None:
        raise ResumeParseError("PDF support is not installed (PyMuPDF missing).")
    try:
        doc = pymupdf.open(stream=file_stream.read(), filetype="pdf")
        text = "\n".join(page.get_text() for page in doc)
        doc.close()
    except Exception as exc:
        raise ResumeParseError(f"Could not read the PDF: {exc}") from exc
    return text


def extract_txt_text(file_stream):
    try:
        return file_stream.read().decode("utf-8", errors="ignore")
    except Exception as exc:
        raise ResumeParseError(f"Could not read the text file: {exc}") from exc


def extract_text(file_stream, filename):
    """Extract clean text from an uploaded file based on its extension."""
    ext = filename.rsplit(".", 1)[1].lower() if "." in filename else ""
    if ext == "pdf":
        text = extract_pdf_text(file_stream)
    elif ext == "txt":
        text = extract_txt_text(file_stream)
    else:
        raise ResumeParseError("Unsupported file type. Please upload a PDF or TXT file.")

    text = re.sub(r"[^\S\n]+", " ", text or "").strip()
    if not text:
        raise ResumeParseError("No readable text could be extracted from this file.")
    return text


def section_map(text):
    """Split a resume into rough sections by common headings."""
    pattern = re.compile(
        r"(?i)^\s*(education|experience|projects?|skills?|work experience|"
        r"internship|certifications?|achievements?|summary|objective|"
        r"leadership|publications?|contact)\s*[:.-]?\s*$",
        re.MULTILINE,
    )
    sections = {}
    last = None
    for line in text.splitlines():
        line = line.strip()
        m = pattern.match(line)
        if m:
            last = m.group(1).lower()
            sections[last] = []
        elif last:
            sections[last].append(line)
    return {k: " ".join(v) for k, v in sections.items()}


def cleanup(file_path):
    """Remove a temporary uploaded file when possible."""
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
    except OSError:
        pass