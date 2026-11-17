from src.scorer import (
    compute_scores,
    education_score,
    experience_score,
    generate_suggestions,
    keyword_match_score,
    percentage,
    projects_score,
    skill_match_score,
    text_similarity,
)


def test_percentage():
    assert percentage(6, 8) == 75
    assert percentage(0, 5) == 0
    assert percentage(3, 0) == 0


def test_skill_match_score():
    assert skill_match_score(["a", "b"], ["a", "b", "c", "d"]) == 50
    assert skill_match_score([], ["a"]) == 0


def test_keyword_match_score():
    assert keyword_match_score(["a", "b"], ["a", "b", "c"]) == 67
    assert keyword_match_score([], []) == 0


def test_heuristic_scores():
    resume = """Python developer.
    Experience: 3 years as data engineer.
    B.Tech from University of Mumbai.
    Built a project deployed on GitHub, improved performance by 30%.
    """
    assert experience_score(resume) > 0
    assert education_score(resume) >= 60
    assert projects_score(resume) >= 60


def test_text_similarity():
    a = "I know python and pandas for data analysis"
    b = "candidate must know python and pandas for data analysis"
    assert text_similarity(a, b) > text_similarity("I like cooking", b)


def test_compute_scores_shape():
    resume = "Python SQL Pandas. 3 years experience. B.Tech. Built projects."
    job = "Python SQL Power BI required. Docker preferred."
    scores = compute_scores(
        resume, job,
        matched_skills=[{"name": "Python"}, {"name": "SQL"}],
        job_skills=[{"name": "Python"}, {"name": "SQL"}, {"name": "Power BI"}, {"name": "Docker"}],
        matched_keywords=["python", "sql"],
        job_keywords=["python", "sql", "power", "docker", "required", "preferred"],
    )
    assert scores["overall_score"] >= 0 and scores["overall_score"] <= 100
    assert set(scores["breakdown"]) == {"skills", "keywords", "experience", "education", "projects"}


def test_generate_suggestions():
    analysis = {
        "skill_match": 40,
        "matched_skills": ["Python"],
        "job_skills": ["Python", "SQL", "Power BI"],
        "missing_skills": [
            {"name": "SQL", "importance": "critical"},
            {"name": "Power BI", "importance": "important"},
        ],
        "keywords": {"matched": [], "missing": ["data"]},
        "breakdown": {"skills": 40, "keywords": 30, "experience": 50, "education": 70, "projects": 40},
    }
    suggestions = generate_suggestions(analysis)
    assert any(s["priority"] == "high" for s in suggestions)
    assert any("SQL" in s["text"] for s in suggestions if s["category"] == "skills")