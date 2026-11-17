"""Analytics aggregation for the interactive dashboard."""

from collections import Counter


def build_analytics(analysis):
    """Turn a full analysis result into dashboard-ready datasets."""
    resume_skills = analysis.get("resume_skills", [])
    missing = analysis.get("missing_skills", [])
    matched = analysis.get("matched_skills", [])
    job_skills = analysis.get("job_skills", [])
    keywords = analysis.get("keywords", {})
    breakdown = analysis.get("breakdown", {})

    category_counts = Counter(s.get("category", "Other") for s in resume_skills)
    gap_counts = Counter(s.get("importance", "important") for s in missing)

    interview = analysis.get("interview", {})

    return {
        "metrics": {
            "overall": analysis.get("overall_score", 0),
            "skill_match": analysis.get("skill_match", 0),
            "keyword_match": analysis.get("keyword_match", 0),
            "text_similarity": analysis.get("text_similarity", 0),
            "matched_skills": len(matched),
            "missing_skills": len(missing),
            "total_job_skills": len(job_skills),
            "resume_skills": len(resume_skills),
        },
        "skill_match_chart": {
            "matched": len(matched),
            "missing": len(missing),
        },
        "skill_distribution": {
            "labels": list(category_counts.keys()),
            "values": list(category_counts.values()),
        },
        "skill_gap_chart": {
            "critical": gap_counts.get("critical", 0),
            "important": gap_counts.get("important", 0),
            "optional": gap_counts.get("optional", 0),
        },
        "keyword_chart": {
            "matched": len(keywords.get("matched", [])),
            "missing": len(keywords.get("missing", [])),
        },
        "compatibility_breakdown": {
            "labels": list(breakdown.keys()),
            "values": list(breakdown.values()),
        },
        "breakdown": breakdown,
        "interview_stats": {
            "technical": len(interview.get("technical", [])),
            "role_specific": len(interview.get("role_specific", [])),
            "scenario": len(interview.get("scenario", [])),
        },
    }