"""Resource recommendation: matching missing skills to curated learning
resources with a quality-prioritized ordering."""

import csv
import re
from difflib import SequenceMatcher

from config import Config, RESOURCES_FILE
from src.skill_extractor import _load_skills

_RESOURCE_PRIORITY = {
    "Documentation": 1,
    "Course": 2,
    "Article": 3,
    "Video": 4,
    "Playlist": 5,
}

_resource_cache = None
_resource_signature = None


def _load_resources():
    """Load and cache the curated resource dataset."""
    global _resource_cache, _resource_signature
    signature = RESOURCES_FILE.stat().st_mtime_ns if RESOURCES_FILE.exists() else None
    if Config.CACHE_ENABLED and _resource_cache is not None and signature == _resource_signature:
        return _resource_cache

    resources = []
    with open(RESOURCES_FILE, "r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            resources.append({
                "skill": row["skill"].strip(),
                "resource_type": row["resource_type"].strip(),
                "title": row["title"].strip(),
                "url": row["url"].strip(),
                "difficulty": row["difficulty"].strip(),
                "provider": row["provider"].strip(),
            })
    _resource_cache = resources
    _resource_signature = signature
    return resources


def _fallback_resources(skill):
    """Generate sensible fallback resources for a skill with no curated entry."""
    slug = re.sub(r"[^a-z0-9]+", "+", skill.lower()).strip("+")
    return [
        {
            "skill": skill,
            "resource_type": "Video",
            "title": f"{skill} Full Course on YouTube",
            "url": f"https://www.youtube.com/results?search_query={slug}+full+course",
            "difficulty": "Beginner",
            "provider": "YouTube",
        },
        {
            "skill": skill,
            "resource_type": "Article",
            "title": f"{skill} Beginner Guide",
            "url": f"https://www.google.com/search?q={slug}+tutorial+beginner",
            "difficulty": "Beginner",
            "provider": "Web",
        },
        {
            "skill": skill,
            "resource_type": "Documentation",
            "title": f"Official {skill} Documentation",
            "url": f"https://www.google.com/search?q={slug}+official+documentation",
            "difficulty": "Intermediate",
            "provider": "Official",
        },
    ]


def _normalize(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def get_resources(skill, limit=None):
    """Return prioritized resources for a skill name (fuzzy skill matching)."""
    resources = _load_resources()
    skill_norm = _normalize(skill)

    exact = [r for r in resources if _normalize(r["skill"]) == skill_norm]
    if not exact:
        fuzzy = [
            r for r in resources
            if SequenceMatcher(None, skill_norm, _normalize(r["skill"])).ratio() >= 0.7
        ]
        exact = fuzzy
    if not exact:
        for dataset in _load_skills():
            if skill_norm == _normalize(dataset["name"]):
                exact = [r for r in resources if _normalize(r["skill"]) == _normalize(dataset["name"])]
                break

    if not exact:
        exact = _fallback_resources(skill)

    ordered = sorted(
        exact,
        key=lambda r: (
            _RESOURCE_PRIORITY.get(r["resource_type"], 9),
            {"Beginner": 0, "Intermediate": 1, "Advanced": 2}.get(r["difficulty"], 1),
        ),
    )
    return ordered[:limit] if limit else ordered


def search_resources(query):
    """Search resources across all skills and return grouped results."""
    query_norm = _normalize(query)
    resources = _load_resources()
    scored = []
    for r in resources:
        score = max(
            SequenceMatcher(None, query_norm, _normalize(r["skill"])).ratio(),
            SequenceMatcher(None, query_norm, _normalize(r["title"])).ratio(),
        )
        scored.append((score, r))
    scored.sort(key=lambda x: -x[0])
    return [r for score, r in scored if score >= 0.5][:30]