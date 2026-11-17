"""Scoring: skill match, keyword match, text similarity and overall
resume-job compatibility scores."""

import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.text_processor import clean_text, remove_stopwords, tokenize

# Weight distribution for the compatibility breakdown
_WEIGHTS = {
    "skills": 0.40,
    "keywords": 0.20,
    "experience": 0.15,
    "education": 0.10,
    "projects": 0.15,
}


def percentage(part, whole):
    if whole <= 0:
        return 0
    return round((part / whole) * 100)


def skill_match_score(matched_skills, job_skills):
    if not job_skills:
        return 0
    return percentage(len(matched_skills), len(job_skills))


def keyword_match_score(matched_keywords, job_keywords):
    total = len(job_keywords)
    if total == 0:
        return 0
    return percentage(len(matched_keywords), total)


def text_similarity(resume_text, job_text):
    """Cosine similarity between TF-IDF vectors of the two documents."""
    resume = clean_text(resume_text)
    job = clean_text(job_text)
    if not resume or not job:
        return 0.0
    try:
        vectorizer = TfidfVectorizer(
            tokenizer=lambda t: remove_stopwords(tokenize(t)),
            token_pattern=None,
            lowercase=True,
        )
        matrix = vectorizer.fit_transform([resume, job])
        sim = cosine_similarity(matrix[0:1], matrix[1:2])[0][0]
        return round(float(sim) * 100, 1)
    except ValueError:
        return 0.0


_EXPERIENCE_PATTERNS = [
    r"\d+\s*(?:yrs?|years?)\s*(?:of)?\s*(?:experience|work)",
    r"\b(?:experience|intern|internship|worked|work history|professional experience)\b",
    r"\b(?:junior|senior|lead|analyst|engineer|developer|intern)\b",
]
_EDUCATION_PATTERNS = [
    r"\b(?:b\.?sc|b\.?tech|b\.?e|bachelor|b\.?a)\b",
    r"\b(?:m\.?sc|m\.?tech|m\.?a|master|mba)\b",
    r"\b(?:ph\.?d|doctorate)\b",
    r"\b(?:university|college|institute|school|academy)\b",
]
_PROJECT_PATTERNS = [
    r"\b(?:project|projects)\b",
    r"\b(?:built|developed|created|implemented|designed)\b",
    r"\b(?:github|gitlab|portfolio|deployed)\b",
    r"\b(?:achievement|achieved|improved|increased|reduced)\b",
]


def _heuristic_score(text, patterns, base=35, boost=20):
    if not text:
        return 0
    text = text.lower()
    hits = sum(len(re.findall(p, text)) for p in patterns)
    if hits == 0:
        return base - 20
    return min(100, base + (hits - 1) * boost)


def experience_score(resume_text):
    return _heuristic_score(resume_text, _EXPERIENCE_PATTERNS, base=45, boost=18)


def education_score(resume_text):
    return _heuristic_score(resume_text, _EDUCATION_PATTERNS, base=40, boost=20)


def projects_score(resume_text):
    return _heuristic_score(resume_text, _PROJECT_PATTERNS, base=40, boost=22)


def generate_suggestions(analysis):
    """Build prioritized, categorized improvement suggestions.

    Each skill suggestion includes context about why the skill matters
    and uses non-absolute language ("if you have this skill...").
    """
    suggestions = []
    missing = analysis.get("missing_skills", [])
    breakdown = analysis.get("breakdown", {})
    skill_priority = analysis.get("skill_priority", [])

    # Build a priority lookup for missing skills
    priority_map = {sp["name"]: sp for sp in skill_priority} if skill_priority else {}

    critical = [s for s in missing if s.get("importance") == "critical"]
    important = [s for s in missing if s.get("importance") == "important"]

    # High-priority skill suggestions with context
    for skill in critical[:4]:
        sp = priority_map.get(skill["name"], {})
        reason = sp.get("reason", "it is a critical requirement for this role.")
        suggestions.append({
            "priority": "high",
            "category": "skills",
            "text": (
                f"{skill['name']} is a key requirement for this role but was not detected "
                f"in your resume. {reason} If you have relevant experience, consider adding "
                f"a project, coursework, certification, or practical example demonstrating it."
            ),
        })

    # Medium-priority skill suggestions
    for skill in important[:3]:
        sp = priority_map.get(skill["name"], {})
        reason = sp.get("reason", "it contributes significantly to this role.")
        suggestions.append({
            "priority": "medium",
            "category": "skills",
            "text": (
                f"{skill['name']} {reason} If you have relevant experience, "
                f"demonstrate it with a concrete example or relevant training."
            ),
        })

    if analysis.get("skill_match", 0) < 60:
        suggestions.append({
            "priority": "high",
            "category": "keywords",
            "text": (
                f"Your resume demonstrates {len(analysis.get('matched_skills', []))} of "
                f"{len(analysis.get('job_skills', []))} required skills. Prioritize learning the "
                f"missing ones to raise your skill match."
            ),
        })

    if breakdown.get("projects", 100) < 60:
        suggestions.append({
            "priority": "medium",
            "category": "projects",
            "text": (
                "Add measurable achievements to your project descriptions — "
                "e.g. 'improved query speed by 40%' instead of 'optimized queries'."
            ),
        })

    if breakdown.get("experience", 100) < 60:
        suggestions.append({
            "priority": "medium",
            "category": "experience",
            "text": (
                "Strengthen the experience section with action verbs, responsibilities "
                "and quantified outcomes for each role."
            ),
        })

    if breakdown.get("keywords", 100) < 60:
        suggestions.append({
            "priority": "medium",
            "category": "keywords",
            "text": (
                "Improve keyword alignment — mirror the job description's terminology "
                "in your skills and summary sections."
            ),
        })

    if breakdown.get("education", 100) < 60:
        suggestions.append({
            "priority": "low",
            "category": "education",
            "text": (
                "Make your education section explicit: degree, institution, year and "
                "relevant coursework."
            ),
        })

    suggestions.append({
        "priority": "low",
        "category": "formatting",
        "text": "Keep a clean single-column layout with standard section headings for better ATS parsing.",
    })
    suggestions.append({
        "priority": "low",
        "category": "ats",
        "text": "Avoid tables, images and graphics in your resume — ATS systems often fail to parse them.",
    })

    order = {"high": 0, "medium": 1, "low": 2}
    return sorted(suggestions, key=lambda s: order[s["priority"]])


def compute_scores(resume_text, job_text, matched_skills, job_skills, matched_keywords, job_keywords):
    """Compute all scores and the compatibility breakdown."""
    skills_score = skill_match_score(matched_skills, job_skills)
    kw_score = keyword_match_score(matched_keywords, job_keywords)
    sim = text_similarity(resume_text, job_text)

    exp_score = experience_score(resume_text)
    edu_score = education_score(resume_text)
    proj_score = projects_score(resume_text)

    breakdown = {
        "skills": skills_score,
        "keywords": kw_score,
        "experience": exp_score,
        "education": edu_score,
        "projects": proj_score,
    }

    overall = round(sum(breakdown[k] * _WEIGHTS[k] for k in breakdown))
    overall = max(0, min(100, overall))

    return {
        "overall_score": overall,
        "skill_match": skills_score,
        "keyword_match": kw_score,
        "text_similarity": sim,
        "breakdown": breakdown,
    }


def simulate_improvement(analysis, skill_name):
    """Estimate the compatibility score if a missing skill were added.

    This uses the existing scoring weights to project the impact:
    - skill_match_score rises because matched count increases by 1
    - keyword_match_score may rise if the skill name is a missing keyword
    - experience / education / projects scores stay unchanged

    Returns a dict with the simulated score, delta, and an explanation.
    """
    current_overall = analysis.get("overall_score", 0)
    job_skills = analysis.get("job_skills", [])
    matched_skills = list(analysis.get("matched_skills", []))
    matched_keywords = list(analysis.get("keywords", {}).get("matched", []))
    missing_keywords = list(analysis.get("keywords", {}).get("missing", []))
    job_keywords = matched_keywords + missing_keywords
    breakdown = dict(analysis.get("breakdown", {}))
    resume_text = analysis.get("resume_text_excerpt", "")
    job_text = ""  # not needed for re-scoring — similarity stays constant

    # Determine the importance of this skill for the explanation
    missing_skills = analysis.get("missing_skills", [])
    skill_importance = "important"
    skill_category = ""
    for ms in missing_skills:
        if ms["name"].lower() == skill_name.lower():
            skill_importance = ms.get("importance", "important")
            skill_category = ms.get("category", "")
            break

    # 1. Simulate adding the skill to matched_skills
    simulated_matched = matched_skills + [{"name": skill_name, "category": skill_category}]
    sim_skills_score = skill_match_score(simulated_matched, job_skills)

    # 2. Simulate keyword improvement if skill name is a missing keyword
    skill_lower = skill_name.lower()
    sim_matched_kw = list(matched_keywords)
    sim_missing_kw = list(missing_keywords)
    keyword_boosted = False
    if skill_lower in [k.lower() for k in missing_keywords]:
        sim_matched_kw.append(skill_lower)
        sim_missing_kw = [k for k in sim_missing_kw if k.lower() != skill_lower]
        keyword_boosted = True

    sim_kw_score = keyword_match_score(sim_matched_kw, job_keywords)

    # 3. Keep other scores unchanged
    sim_breakdown = {
        "skills": sim_skills_score,
        "keywords": sim_kw_score,
        "experience": breakdown.get("experience", 0),
        "education": breakdown.get("education", 0),
        "projects": breakdown.get("projects", 0),
    }

    sim_overall = round(sum(sim_breakdown[k] * _WEIGHTS[k] for k in sim_breakdown))
    sim_overall = max(0, min(100, sim_overall))
    delta = sim_overall - current_overall

    # Build explanation
    importance_phrases = {
        "critical": "a critical requirement",
        "important": "an important requirement",
        "optional": "a preferred qualification",
    }
    importance_desc = importance_phrases.get(skill_importance, "an important requirement")

    explanation = (
        f"Adding strong, genuine evidence of {skill_name} experience could improve your "
        f"resume's alignment because {skill_name} is {importance_desc} in this job description. "
        f"This would raise your skill match from {breakdown.get('skills', 0)}% to {sim_skills_score}%."
    )
    if keyword_boosted:
        explanation += (
            f" Additionally, {skill_name} is also a missing keyword, so including it would "
            f"improve your keyword alignment from {breakdown.get('keywords', 0)}% to {sim_kw_score}%."
        )

    return {
        "current_score": current_overall,
        "simulated_score": sim_overall,
        "delta": delta,
        "skill_name": skill_name,
        "skill_importance": skill_importance,
        "explanation": explanation,
        "current_breakdown": breakdown,
        "simulated_breakdown": sim_breakdown,
    }