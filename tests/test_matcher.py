from src.matcher import match_keywords, match_skills


def test_match_skills_basic():
    resume = [
        {"name": "Python", "category": "Programming Languages"},
        {"name": "SQL", "category": "Programming Languages"},
        {"name": "Pandas", "category": "Data Processing & Engineering"},
    ]
    job = [
        {"name": "Python", "category": "Programming Languages"},
        {"name": "SQL", "category": "Programming Languages"},
        {"name": "Power BI", "category": "Data Visualization"},
    ]
    matched, missing, extra = match_skills(resume, job)

    assert {s["name"] for s in matched} == {"Python", "SQL"}
    assert {s["name"] for s in missing} == {"Power BI"}
    assert {s["name"] for s in extra} == {"Pandas"}


def test_match_skills_no_overlap():
    resume = [{"name": "Docker", "category": "Cloud & DevOps"}]
    job = [{"name": "Tableau", "category": "Data Visualization"}]
    matched, missing, _ = match_skills(resume, job)
    assert matched == []
    assert missing == [{"name": "Tableau", "category": "Data Visualization"}]


def test_match_keywords():
    resume = "I have strong experience with Python and machine learning dashboards."
    job = "Python machine learning dashboards required. Docker preferred."
    matched, missing = match_keywords(resume, job)
    # New system returns canonical skill names, not raw words
    matched_lower = [m.lower() for m in matched]
    assert "machine learning" in matched_lower or "machine learning" in [m.lower() for m in matched]
    assert "python" in matched_lower or "python" in [m.lower() for m in matched]
    # Docker is in job but not in resume — should be missing
    missing_lower = [m.lower() for m in missing]
    assert "docker" in missing_lower or "docker" in [m.lower() for m in missing]


def test_match_keywords_empty():
    assert match_keywords("", "job text") == ([], [])
    assert match_keywords("resume", "") == ([], [])