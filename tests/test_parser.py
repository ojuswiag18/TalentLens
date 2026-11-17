import io

import pytest

from src.resume_parser import (
    ResumeParseError,
    allowed_file,
    extract_txt_text,
    extract_text,
    section_map,
    validate_pdf,
)


def test_allowed_file():
    assert allowed_file("resume.pdf")
    assert allowed_file("cv.txt")
    assert not allowed_file("virus.exe")
    assert not allowed_file("resume")


def test_validate_pdf_accepts_pdf():
    stream = io.BytesIO(b"%PDF-1.7 fake content")
    assert validate_pdf(stream, "resume.pdf") is True


def test_validate_pdf_rejects_non_pdf_content():
    stream = io.BytesIO(b"not a pdf at all")
    with pytest.raises(ResumeParseError):
        validate_pdf(stream, "resume.pdf")


def test_validate_pdf_rejects_wrong_extension():
    stream = io.BytesIO(b"%PDF-1.7 fake")
    with pytest.raises(ResumeParseError):
        validate_pdf(stream, "resume.txt")


def test_extract_txt_text():
    stream = io.BytesIO("Python\nSQL\nPandas".encode("utf-8"))
    assert extract_txt_text(stream) == "Python\nSQL\nPandas"


def test_extract_text_unsupported_type():
    stream = io.BytesIO(b"data")
    with pytest.raises(ResumeParseError):
        extract_text(stream, "resume.docx")


def test_extract_text_empty_txt():
    stream = io.BytesIO(b"   ")
    with pytest.raises(ResumeParseError):
        extract_text(stream, "resume.txt")


def test_section_map():
    text = """Aarav
    EDUCATION
    B.Tech CS
    PROJECTS
    Built an app
    """
    sections = section_map(text)
    assert "education" in sections
    assert "projects" in sections
    assert "B.Tech CS" in sections["education"]