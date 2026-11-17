"""Centralized resume template configuration.

This module defines the single source of truth for all resume template styling.
PDF, DOCX, and Live Preview all derive their appearance from this configuration.

Each template defines:
- Colors (accent, heading, text, muted, border)
- Font sizes (name, title, heading, body, meta, small)
- Font families (for PDF/DOCX)
- Spacing (section gap, line gap, bullet gap)
- Visual elements (underline style, separator)
"""

# =============================================================================
# SECTION ORDER — single source of truth for all renderers
# =============================================================================
SECTION_ORDER = [
    "summary",
    "experience",
    "projects",
    "skills",
    "education",
    "certifications",
    "achievements",
    "languages",
    "links",
]

SECTION_LABELS = {
    "summary": "Professional Summary",
    "experience": "Experience",
    "projects": "Projects",
    "skills": "Skills",
    "education": "Education",
    "certifications": "Certifications",
    "achievements": "Achievements",
    "languages": "Languages",
    "links": "Links",
}

# =============================================================================
# TEMPLATE DEFINITIONS
# =============================================================================
TEMPLATES = {
    "modern": {
        "name": "Modern",
        "colors": {
            "accent": "#2563EB",         # Blue
            "heading": "#2563EB",
            "text": "#111111",
            "muted": "#666666",
            "border": "#DDDDDD",
            "separator": "#DDDDDD",
            "bg": "#FFFFFF",
        },
        "colors_rgb": {
            "accent": (37, 99, 235),
            "heading": (37, 99, 235),
            "text": (17, 17, 17),
            "muted": (100, 100, 100),
            "border": (221, 221, 221),
            "separator": (200, 200, 200),
        },
        "fonts": {
            "pdf": "Helvetica",
            "docx": "Calibri",
        },
        "sizes": {
            "name": 20,
            "name_executive": 22,
            "title": 11,
            "heading": 11,
            "body": 10,
            "meta": 9,
            "small": 9,
            "contact": 9,
        },
        "spacing": {
            "section_before": 3,
            "section_heading_h": 6,
            "section_after": 2.5,
            "line_h": 5,
            "body_after": 1,
            "experience_after": 1.5,
            "project_after": 1.5,
            "header_ln": 10,
            "title_ln": 7,
            "contact_ln": 6,
            "separator_after": 4,
        },
        "css": {
            "name_size": "1.35rem",
            "title_size": "0.72rem",
            "heading_size": "0.72rem",
            "body_size": "0.68rem",
            "meta_size": "0.62rem",
            "contact_size": "0.62rem",
            "line_height": "1.45",
            "heading_spacing": "0.8px",
        },
    },
    "professional": {
        "name": "Professional",
        "colors": {
            "accent": "#374151",
            "heading": "#374151",
            "text": "#111111",
            "muted": "#666666",
            "border": "#DDDDDD",
            "separator": "#DDDDDD",
            "bg": "#FFFFFF",
        },
        "colors_rgb": {
            "accent": (55, 65, 81),
            "heading": (55, 65, 81),
            "text": (17, 17, 17),
            "muted": (100, 100, 100),
            "border": (221, 221, 221),
            "separator": (200, 200, 200),
        },
        "fonts": {
            "pdf": "Helvetica",
            "docx": "Calibri",
        },
        "sizes": {
            "name": 20,
            "name_executive": 22,
            "title": 11,
            "heading": 11,
            "body": 10,
            "meta": 9,
            "small": 9,
            "contact": 9,
        },
        "spacing": {
            "section_before": 3,
            "section_heading_h": 6,
            "section_after": 2.5,
            "line_h": 5,
            "body_after": 1,
            "experience_after": 1.5,
            "project_after": 1.5,
            "header_ln": 10,
            "title_ln": 7,
            "contact_ln": 6,
            "separator_after": 4,
        },
        "css": {
            "name_size": "1.35rem",
            "title_size": "0.72rem",
            "heading_size": "0.72rem",
            "body_size": "0.68rem",
            "meta_size": "0.62rem",
            "contact_size": "0.62rem",
            "line_height": "1.45",
            "heading_spacing": "0.8px",
        },
    },
    "executive": {
        "name": "Executive",
        "colors": {
            "accent": "#1E1E1E",
            "heading": "#1E1E1E",
            "text": "#111111",
            "muted": "#666666",
            "border": "#DDDDDD",
            "separator": "#DDDDDD",
            "bg": "#FFFFFF",
        },
        "colors_rgb": {
            "accent": (30, 30, 30),
            "heading": (30, 30, 30),
            "text": (17, 17, 17),
            "muted": (100, 100, 100),
            "border": (221, 221, 221),
            "separator": (200, 200, 200),
        },
        "fonts": {
            "pdf": "Helvetica",
            "docx": "Calibri",
        },
        "sizes": {
            "name": 22,
            "name_executive": 22,
            "title": 11,
            "heading": 11,
            "body": 10,
            "meta": 9,
            "small": 9,
            "contact": 9,
        },
        "spacing": {
            "section_before": 3,
            "section_heading_h": 6,
            "section_after": 2.5,
            "line_h": 5,
            "body_after": 1,
            "experience_after": 1.5,
            "project_after": 1.5,
            "header_ln": 10,
            "title_ln": 7,
            "contact_ln": 6,
            "separator_after": 4,
        },
        "css": {
            "name_size": "1.5rem",
            "title_size": "0.72rem",
            "heading_size": "0.75rem",
            "body_size": "0.68rem",
            "meta_size": "0.62rem",
            "contact_size": "0.62rem",
            "line_height": "1.45",
            "heading_spacing": "0.8px",
        },
    },
}


def get_template(name):
    """Get template configuration by name. Falls back to 'modern' if not found."""
    return TEMPLATES.get(name, TEMPLATES["modern"])


def get_section_order():
    """Return the canonical section order."""
    return SECTION_ORDER[:]


def get_section_label(key):
    """Return the display label for a section key."""
    return SECTION_LABELS.get(key, key.title())
