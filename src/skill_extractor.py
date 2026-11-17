"""Skill extraction from resume and job description text using the
curated skills dataset with alias + fuzzy matching and level detection."""

import csv
import re
from difflib import get_close_matches

from config import Config, SKILLS_FILE
from src.text_processor import normalize, sentence_around, window_around

_LEVEL_KEYWORDS = {
    "advanced": ["advanced", "expert", "proficient", "deep", "in-depth"],
    "intermediate": ["intermediate", "mid-level", "working knowledge", "working proficiency"],
    "basic": ["basic", "beginner", "fundamental", "introductory", "foundation", "entry-level"],
}

_PREFERRED_KEYWORDS = ["preferred", "nice to have", "nice-to-have", "bonus", "plus", "optional", "good to have"]
_CRITICAL_KEYWORDS = ["required", "must", "mandatory", "essential", "core", "strong", "solid", "proficiency"]

_skill_cache = None
_cache_signature = None


def _load_skills():
    """Load and cache the skills dataset from CSV."""
    global _skill_cache, _cache_signature
    signature = SKILLS_FILE.stat().st_mtime_ns if SKILLS_FILE.exists() else None
    if Config.CACHE_ENABLED and _skill_cache is not None and signature == _cache_signature:
        return _skill_cache

    skills = []
    with open(SKILLS_FILE, "r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            name = row["skill"].strip()
            category = row["category"].strip()
            aliases = [a.strip().lower() for a in row.get("aliases", "").split(";") if a.strip()]
            aliases = [a for a in aliases if len(a) >= 2]
            patterns = sorted({normalize(name), *aliases}, key=len, reverse=True)
            skills.append({
                "name": name,
                "category": category,
                "patterns": patterns,
                "regex": re.compile(r"(?<![a-z0-9])(" + "|".join(re.escape(p) for p in patterns) + r")(?![a-z0-9])"),
            })
    _skill_cache = skills
    _cache_signature = signature
    return skills


def _detect_level(text, positions):
    """Infer a proficiency level from the sentence around each mention."""
    for pos in positions:
        ctx = sentence_around(text, pos)
        for level, keywords in _LEVEL_KEYWORDS.items():
            if any(k in ctx for k in keywords):
                return level
    return None


def extract_skills(text, source="resume", fuzzy=True):
    """Extract skills present in a body of text.

    Returns a list of dicts with keys: name, category, count, level, importance.
    """
    if not text:
        return []

    norm = normalize(text)
    hits = []
    for skill in _load_skills():
        positions = []
        count = 0
        for m in skill["regex"].finditer(norm):
            positions.append(m.start())
            count += 1
        if count == 0 and fuzzy:
            count, positions = _fuzzy_count(skill, norm)
        if count > 0:
            hits.append({
                "name": skill["name"],
                "category": skill["category"],
                "count": count,
                "positions": positions,
                "level": _detect_level(norm, positions),
            })
    return sorted(hits, key=lambda h: (-h["count"], h["name"].lower()))


def _fuzzy_count(skill, norm, threshold=0.88):
    """Fuzzy-match single-word aliases against tokens (handles misspellings)."""
    words = set(re.findall(r"[a-z0-9+.#]+", norm))
    total = 0
    positions = []
    for p in skill["patterns"]:
        if " " in p or len(p) < 4:
            continue
        matches = get_close_matches(p, words, n=1, cutoff=threshold)
        if matches:
            total += 1
            positions.append(norm.find(matches[0]))
    return total, positions


def classify_importance(text, skill_names):
    """Classify each job skill as critical / important / optional based on
    how it is described in the job description."""
    norm = normalize(text)
    result = {}
    for hit in _load_skills():
        name = hit["name"]
        if name not in skill_names:
            continue
        positions = [m.start() for m in hit["regex"].finditer(norm)]
        if not positions:
            continue
        optional = False
        critical = 0
        for pos in positions:
            ctx = sentence_around(norm, pos)
            if any(k in ctx for k in _PREFERRED_KEYWORDS):
                optional = True
                continue
            if any(k in ctx for k in _CRITICAL_KEYWORDS):
                critical += 1
        if optional:
            result[name] = "optional"
        elif critical >= 1 or len(positions) >= 2:
            result[name] = "critical"
        else:
            result[name] = "important"
    return result