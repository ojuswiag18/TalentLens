"""New feature analysis functions for TalentLens V2.

Provides: Job Description Insights, Hidden Strengths, Career Story Consistency,
What Could Improve My Score, Skill Dependency Map, Personalized Learning Path,
Resume Version Comparison, and Role Comparison.
"""

import re
from collections import Counter


# ---------------------------------------------------------------------------
# FEATURE 1 — Job Description Insights
# ---------------------------------------------------------------------------

def analyze_job_description(job_text, job_skills, matched_skills, missing_skills):
    """Analyze the job description for structural observations."""
    if not job_text:
        return {"insights": [], "overall_quality": "Insufficient Data"}

    text_lower = job_text.lower()
    total_job_skills = len(job_skills)
    missing_count = len(missing_skills)
    matched_count = len(matched_skills)
    critical_count = sum(1 for s in missing_skills if s.get("importance") == "critical")
    optional_count = sum(1 for s in job_skills if s.get("importance") == "optional")
    required_count = total_job_skills - optional_count

    # Skill breadth
    if total_job_skills >= 10:
        breadth = "Very High"
        breadth_desc = f"This job requires {total_job_skills} distinct skills — a very broad technical scope."
    elif total_job_skills >= 7:
        breadth = "High"
        breadth_desc = f"This job requires {total_job_skills} distinct skills — above average breadth."
    elif total_job_skills >= 4:
        breadth = "Moderate"
        breadth_desc = f"This job requires {total_job_skills} distinct skills — a focused but achievable scope."
    else:
        breadth = "Focused"
        breadth_desc = f"This job requires only {total_job_skills} distinct skills — a narrow, specialized role."

    # Technology breadth (unique categories)
    categories = set(s.get("category", "Other") for s in job_skills)
    if len(categories) >= 6:
        tech_breadth = "Very High"
        tech_desc = f"Spans {len(categories)} technology categories — this role touches many domains."
    elif len(categories) >= 4:
        tech_breadth = "High"
        tech_desc = f"Covers {len(categories)} technology categories — requires cross-domain knowledge."
    elif len(categories) >= 2:
        tech_breadth = "Moderate"
        tech_desc = f"Covers {len(categories)} technology categories — relatively focused domain."
    else:
        tech_breadth = "Narrow"
        tech_desc = f"Focused on {len(categories)} technology category — deep specialization expected."

    # Experience requirement
    exp_match = re.search(r"(\d+)\s*(?:\+\s*)?(?:yrs?|years?)", text_lower)
    if exp_match:
        years = int(exp_match.group(1))
        if years >= 7:
            exp_level = "Senior"
            exp_desc = f"Requests {years}+ years of experience — targeting senior candidates."
        elif years >= 4:
            exp_level = "Mid-Level"
            exp_desc = f"Requests {years}+ years of experience — targeting mid-level candidates."
        elif years >= 2:
            exp_level = "Junior+"
            exp_desc = f"Requests {years}+ years of experience — entry-level with some experience expected."
        else:
            exp_level = "Entry-Level"
            exp_desc = f"Requests {years} year(s) of experience — suitable for fresh graduates."
    elif any(w in text_lower for w in ["intern", "fresher", "entry level", "entry-level", "graduate"]):
        exp_level = "Entry-Level"
        exp_desc = "No specific years required — targets entry-level candidates or graduates."
    elif any(w in text_lower for w in ["senior", "lead", "principal", "staff"]):
        exp_level = "Senior"
        exp_desc = "Uses senior-level language — targets experienced professionals."
    else:
        exp_level = "Not Specified"
        exp_desc = "No explicit experience requirement found — scope is ambiguous."

    # Role clarity
    clarity_signals = 0
    if any(w in text_lower for w in ["responsibilities", "what you'll do", "role overview"]):
        clarity_signals += 1
    if any(w in text_lower for w in ["qualifications", "requirements", "what we're looking for"]):
        clarity_signals += 1
    if any(w in text_lower for w in ["nice to have", "preferred", "bonus"]):
        clarity_signals += 1
    if len(job_text) > 500:
        clarity_signals += 1

    if clarity_signals >= 3:
        clarity = "High"
        clarity_desc = "The job description is well-structured with clear responsibilities and requirements."
    elif clarity_signals >= 2:
        clarity = "Moderate"
        clarity_desc = "The job description covers key areas but could be more specific about expectations."
    else:
        clarity = "Low"
        clarity_desc = "The job description lacks structure — some expectations may be unclear."

    # Required vs preferred
    if required_count > 0 and optional_count > 0:
        req_pref = f"{required_count} required, {optional_count} preferred"
        req_pref_desc = f"Distinguishes {required_count} required skills from {optional_count} preferred ones."
    elif required_count > 0:
        req_pref = f"{required_count} required"
        req_pref_desc = "All listed skills appear to be required."
    else:
        req_pref = f"{total_job_skills} total"
        req_pref_desc = "No clear distinction between required and preferred skills."

    # Repeated keywords
    words = re.findall(r"[a-z]{4,}", text_lower)
    word_counts = Counter(words)
    repeated = [(w, c) for w, c in word_counts.most_common(10)
                if c >= 3 and w not in {"must", "should", "will", "using", "with", "team", "work"}]

    insights = [
        {"label": "Skill Requirements", "value": breadth, "desc": breadth_desc},
        {"label": "Technology Breadth", "value": tech_breadth, "desc": tech_desc},
        {"label": "Experience Requirement", "value": exp_level, "desc": exp_desc},
        {"label": "Role Clarity", "value": clarity, "desc": clarity_desc},
        {"label": "Skill Breakdown", "value": req_pref, "desc": req_pref_desc},
    ]

    if repeated:
        top_repeated = repeated[0]
        insights.append({
            "label": "Repeated Emphasis",
            "value": f'"{top_repeated[0]}" mentioned {top_repeated[1]}x',
            "desc": f'The term "{top_repeated[0]}" is emphasized repeatedly — it is a key focus area.',
        })

    if critical_count > 0:
        insights.append({
            "label": "Critical Gaps",
            "value": f"{critical_count} critical",
            "desc": f"You are missing {critical_count} skill(s) marked as critical — prioritize these first.",
        })

    return {"insights": insights}


# ---------------------------------------------------------------------------
# FEATURE 2 — Hidden Strengths
# ---------------------------------------------------------------------------

def find_hidden_strengths(resume_text, resume_skills, matched_skills, extra_skills, job_skills):
    """Identify skills the candidate demonstrates but doesn't strongly emphasize."""
    if not resume_text:
        return []

    text_lower = resume_text.lower()
    hidden = []
    matched_names = {s["name"].lower() for s in matched_skills}
    job_names = {s["name"].lower() for s in job_skills}

    # Look for skills mentioned in resume but with low count or not prominently matched
    for skill in resume_skills:
        name = skill["name"]
        count = skill.get("count", 0)
        category = skill.get("category", "")

        # Skill is in resume but not prominently matched to job
        if name.lower() not in matched_names and name.lower() in job_names:
            # Find evidence sentence
            evidence = _find_evidence(text_lower, name.lower())
            hidden.append({
                "skill": name,
                "category": category,
                "evidence": evidence,
                "recommendation": f"Consider highlighting {name} more clearly — it is relevant to this role.",
                "reason": f"Mentioned {count} time(s) but not prominently represented.",
            })

    # Look for extra skills that could be relevant to the job
    for skill in extra_skills:
        name = skill["name"]
        category = skill.get("category", "")
        # Check if any job skill shares the same category
        related_job = any(s.get("category") == category for s in job_skills if s["name"].lower() not in matched_names)
        if related_job and name.lower() not in matched_names:
            evidence = _find_evidence(text_lower, name.lower())
            if evidence:
                hidden.append({
                    "skill": name,
                    "category": category,
                    "evidence": evidence,
                    "recommendation": f"Your {name} experience ({category}) could strengthen your profile for this role.",
                    "reason": f"Transferable skill in a relevant category.",
                })

    return hidden[:8]


def _find_evidence(text, skill_name):
    """Find a sentence containing the skill name."""
    sentences = re.split(r'[.!?\n]', text)
    for s in sentences:
        if skill_name in s.lower() and len(s.strip()) > 10:
            return s.strip()[:200]
    return ""


# ---------------------------------------------------------------------------
# FEATURE 3 — Career Story Consistency
# ---------------------------------------------------------------------------

def analyze_career_consistency(resume_text, job_text, resume_skills, job_skills,
                                matched_skills, missing_skills, breakdown):
    """Analyze how consistently the resume supports the target role."""
    if not resume_text or not job_text:
        return {"score": 0, "strengths": [], "gaps": [],
                "explanation": "Insufficient data for consistency analysis."}

    text_lower = resume_text.lower()
    job_lower = job_text.lower()
    score = 0
    max_score = 100
    strengths = []
    gaps = []

    # 1. Skill alignment (40 points)
    skill_pct = breakdown.get("skills", 0)
    skill_pts = round(skill_pct * 0.4)
    score += skill_pts
    if skill_pct >= 70:
        strengths.append(f"Strong skill alignment — {len(matched_skills)} of {len(job_skills)} required skills matched.")
    elif skill_pct >= 40:
        strengths.append(f"Moderate skill alignment — {len(matched_skills)} of {len(job_skills)} skills matched.")
    else:
        gaps.append(f"Limited skill alignment — only {len(matched_skills)} of {len(job_skills)} skills matched.")

    # 2. Education relevance (15 points)
    edu_score = breakdown.get("education", 0)
    edu_pts = round(edu_score * 0.15)
    score += edu_pts
    edu_keywords = ["bachelor", "master", "degree", "university", "college", "b.tech", "b.sc", "m.sc", "mba", "phd"]
    has_edu = any(kw in text_lower for kw in edu_keywords)
    job_edu = any(kw in job_lower for kw in edu_keywords)
    if has_edu:
        strengths.append("Education section is present and documented.")
    elif job_edu:
        gaps.append("Education section is missing but may be expected for this role.")
    else:
        score += 5  # Neutral — job doesn't mention education either

    # 3. Project relevance (20 points)
    proj_score = breakdown.get("projects", 0)
    proj_pts = round(proj_score * 0.20)
    score += proj_pts
    if proj_score >= 60:
        strengths.append("Projects section demonstrates hands-on experience.")
    elif proj_score >= 30:
        gaps.append("Projects section could be strengthened with more specific examples.")
    else:
        gaps.append("Projects section is weak — add concrete project examples.")

    # 4. Experience relevance (15 points)
    exp_score = breakdown.get("experience", 0)
    exp_pts = round(exp_score * 0.15)
    score += exp_pts
    if exp_score >= 60:
        strengths.append("Experience section shows relevant professional background.")
    elif exp_score >= 30:
        gaps.append("Experience section could better highlight relevant accomplishments.")
    else:
        gaps.append("Limited professional experience signals detected.")

    # 5. Keyword alignment (10 points)
    kw_score = breakdown.get("keywords", 0)
    kw_pts = round(kw_score * 0.10)
    score += kw_pts

    score = max(0, min(100, score))

    if score >= 80:
        explanation = "Your resume tells a highly consistent story for this role — education, experience, projects, and skills all align well."
    elif score >= 60:
        explanation = "Your resume generally supports this role, but there are areas where the narrative could be strengthened."
    elif score >= 40:
        explanation = "Your resume has some alignment with this role, but several sections need improvement for a cohesive story."
    else:
        explanation = "Your resume has limited alignment with this role — significant gaps exist across multiple areas."

    return {
        "score": score,
        "strengths": strengths,
        "gaps": gaps,
        "explanation": explanation,
    }


# ---------------------------------------------------------------------------
# FEATURE 4 — What Could Improve My Score? (multi-skill simulation)
# ---------------------------------------------------------------------------

def simulate_multi_improvement(analysis, skill_names):
    """Simulate the combined effect of adding multiple missing skills."""
    from src.scorer import skill_match_score, keyword_match_score, _WEIGHTS

    current_overall = analysis.get("overall_score", 0)
    job_skills = analysis.get("job_skills", [])
    matched_skills = list(analysis.get("matched_skills", []))
    matched_keywords = list(analysis.get("keywords", {}).get("matched", []))
    missing_keywords = list(analysis.get("keywords", {}).get("missing", []))
    job_keywords = matched_keywords + missing_keywords
    breakdown = dict(analysis.get("breakdown", {}))

    # Build simulated matched lists
    sim_matched = list(matched_skills)
    sim_matched_kw = list(matched_keywords)
    contributions = []

    missing_skills = analysis.get("missing_skills", [])
    missing_map = {s["name"].lower(): s for s in missing_skills}

    for name in skill_names:
        info = missing_map.get(name.lower())
        if not info:
            continue
        old_skills = skill_match_score(sim_matched, job_skills)
        sim_matched.append({"name": name, "category": info.get("category", "")})
        new_skills = skill_match_score(sim_matched, job_skills)
        skill_delta = new_skills - old_skills

        # Keyword boost
        kw_boost = 0
        if name.lower() in [k.lower() for k in missing_keywords]:
            sim_matched_kw.append(name.lower())
            old_kw = keyword_match_score(sim_matched_kw, job_keywords)
            new_kw = keyword_match_score(
                [k for k in sim_matched_kw], job_keywords)
            kw_boost = new_kw - old_kw

        total_contrib = round(skill_delta * _WEIGHTS["skills"] + kw_boost * _WEIGHTS["keywords"])
        contributions.append({
            "skill": name,
            "importance": info.get("importance", "important"),
            "skill_delta": skill_delta,
            "kw_boost": kw_boost,
            "contribution": total_contrib,
        })

    sim_skills_score = skill_match_score(sim_matched, job_skills)
    sim_kw_score = keyword_match_score(sim_matched_kw, job_keywords)

    sim_breakdown = {
        "skills": sim_skills_score,
        "keywords": sim_kw_score,
        "experience": breakdown.get("experience", 0),
        "education": breakdown.get("education", 0),
        "projects": breakdown.get("projects", 0),
    }

    sim_overall = round(sum(sim_breakdown[k] * _WEIGHTS[k] for k in sim_breakdown))
    sim_overall = max(0, min(100, sim_overall))

    return {
        "current_score": current_overall,
        "simulated_score": sim_overall,
        "delta": sim_overall - current_overall,
        "contributions": sorted(contributions, key=lambda c: -c["contribution"]),
        "current_breakdown": breakdown,
        "simulated_breakdown": sim_breakdown,
    }


# ---------------------------------------------------------------------------
# FEATURE 5 — Skill Dependency Map
# ---------------------------------------------------------------------------

# Known skill dependency relationships (source -> prerequisites)
_SKILL_DEPENDENCIES = {
    "Machine Learning": ["Python", "Statistics", "Pandas", "NumPy", "Scikit-learn"],
    "Deep Learning": ["Python", "Machine Learning", "TensorFlow", "PyTorch"],
    "Natural Language Processing": ["Python", "Machine Learning", "Deep Learning"],
    "Computer Vision": ["Python", "Machine Learning", "Deep Learning"],
    "Data Analysis": ["Python", "SQL", "Pandas", "Microsoft Excel"],
    "Data Engineering": ["SQL", "Python", "Apache Spark", "Apache Kafka", "Docker"],
    "Data Science": ["Python", "SQL", "Machine Learning", "Pandas", "Statistics"],
    "Power BI": ["SQL", "Microsoft Excel", "Data Visualization"],
    "Tableau": ["SQL", "Microsoft Excel", "Data Visualization"],
    "React": ["JavaScript", "HTML", "CSS"],
    "Angular": ["JavaScript", "TypeScript", "HTML", "CSS"],
    "Vue": ["JavaScript", "HTML", "CSS"],
    "Node.js": ["JavaScript"],
    "Django": ["Python", "SQL", "HTML"],
    "Flask": ["Python", "HTML"],
    "FastAPI": ["Python"],
    "Kubernetes": ["Docker", "Linux"],
    "AWS": ["Linux", "Docker"],
    "Azure": ["Docker"],
    "Google Cloud Platform": ["Docker", "Linux"],
    "Apache Spark": ["Python", "SQL"],
    "PySpark": ["Python", "Apache Spark", "SQL"],
    "TensorFlow": ["Python"],
    "PyTorch": ["Python"],
    "Scikit-learn": ["Python"],
    "XGBoost": ["Python", "Machine Learning"],
    "Hadoop": ["Java", "SQL"],
    "Spark": ["Python", "Scala"],
    # Teaching
    "Classroom Management": ["Lesson Planning"],
    "Student Assessment": ["Lesson Planning", "Curriculum Development"],
    "Curriculum Development": ["Lesson Planning"],
    "Educational Technology": ["Lesson Planning"],
    # Healthcare
    "Clinical Diagnosis": ["Patient Assessment"],
    "Treatment Planning": ["Patient Assessment", "Clinical Diagnosis"],
    "Patient Care": ["Patient Assessment", "Treatment Planning"],
    "Medical Documentation": ["Patient Assessment"],
    # HR
    "Performance Management": ["Recruitment"],
    "Employee Relations": ["Recruitment"],
    "Talent Acquisition": ["Recruitment"],
    "Training & Development": ["Performance Management"],
    # Software Development
    "API Development": ["JavaScript", "Python"],
    "Version Control": ["Git"],
    "CI/CD": ["Docker", "Version Control"],
    "Cloud Computing": ["Linux", "Docker"],
    "Testing": ["Python", "JavaScript"],
    "Microservices": ["Docker", "API Development"],
    # Coordination / Admin
    "Event Management": ["Scheduling", "Communication"],
    "Scheduling": ["Communication"],
    "Student Records": ["Communication"],
    "Parent Communication": ["Communication"],
    "Teacher Coordination": ["Communication", "Scheduling"],
    # Analytics broadly
    "Reporting": ["Data Visualization", "SQL"],
    "Business Intelligence": ["Data Visualization", "SQL"],
    "Statistics": [],
    "Python": [],
    "SQL": [],
    "JavaScript": [],
    "HTML": [],
    "CSS": [],
    "Docker": [],
    "Linux": [],
    "Java": [],
    "Git": [],
    "Microsoft Excel": [],
    "Communication": [],
    "Data Visualization": [],
    "Pandas": ["Python"],
    "NumPy": ["Python"],
    "Scikit-learn": ["Python", "Machine Learning"],
    "TensorFlow": ["Python", "Machine Learning"],
    "PyTorch": ["Python", "Machine Learning"],
}

# Layer classification: which tier each skill belongs to
_LAYER_MAP = {
    # Foundation (no deps)
    "Python": 0, "SQL": 0, "JavaScript": 0, "HTML": 0, "CSS": 0,
    "Java": 0, "Docker": 0, "Linux": 0, "Git": 0, "Statistics": 0,
    "Microsoft Excel": 0, "Communication": 0, "Data Visualization": 0,
    "Lesson Planning": 0, "Patient Assessment": 0, "Recruitment": 0,
    "Scheduling": 0,
    # Core (depends on foundation)
    "Pandas": 1, "NumPy": 1, "Machine Learning": 2, "Power BI": 1,
    "Tableau": 1, "React": 1, "Angular": 1, "Vue": 1, "Node.js": 1,
    "Django": 1, "Flask": 1, "FastAPI": 1, "Apache Spark": 1,
    "TensorFlow": 2, "PyTorch": 2, "Scikit-learn": 2,
    "Data Analysis": 1, "Data Science": 2, "Data Engineering": 2,
    "SQL": 0, "Reporting": 1, "Business Intelligence": 1,
    "Classroom Management": 1, "Student Assessment": 2,
    "Curriculum Development": 2, "Educational Technology": 1,
    "Clinical Diagnosis": 2, "Treatment Planning": 2,
    "Patient Care": 2, "Medical Documentation": 1,
    "Performance Management": 1, "Employee Relations": 1,
    "Talent Acquisition": 1, "Training & Development": 2,
    "Parent Communication": 1, "Student Records": 1,
    "Teacher Coordination": 2, "Event Management": 2,
    # Advanced (depends on core)
    "Deep Learning": 3, "Natural Language Processing": 3,
    "Computer Vision": 3, "XGBoost": 3,
    "Hadoop": 2, "Spark": 2, "Kubernetes": 3,
    "AWS": 2, "Azure": 2, "Google Cloud Platform": 2,
    "API Development": 1, "Version Control": 1,
    "CI/CD": 3, "Cloud Computing": 2, "Testing": 1,
    "Microservices": 3,
    # Role-specific / Application
    "PySpark": 2,
}


def _classify_layer(name, deps_map):
    """Classify a skill into a layer based on its dependencies."""
    if name in _LAYER_MAP:
        return _LAYER_MAP[name]
    direct_deps = deps_map.get(name, [])
    if not direct_deps:
        return 0
    # Check if all deps are foundational (layer 0)
    max_dep_layer = 0
    for d in direct_deps:
        if d in _LAYER_MAP:
            max_dep_layer = max(max_dep_layer, _LAYER_MAP[d])
    return min(max_dep_layer + 1, 3)


def _find_why_matters(name, job_text):
    """Generate a short explanation of why a skill matters based on the JD."""
    if not job_text:
        return f"{name} is a relevant skill for this role."
    lower_text = job_text.lower()
    name_lower = name.lower()
    # Look for the skill in the JD and extract context
    sentences = [s.strip() for s in lower_text.replace('\n', ' ').split('.') if name_lower in s]
    if sentences:
        ctx = sentences[0][:120].strip()
        return f"{name} is referenced in the job description: \"{ctx}\""
    return f"{name} is a relevant requirement identified in this role's job description."


def build_skill_dependency_map(job_skills, matched_skills, missing_skills, job_text=""):
    """Build a rich dependency map with hierarchy, prerequisites, leads_to, and metadata."""
    matched_names = {s["name"] for s in matched_skills}
    missing_names = {s["name"] for s in missing_skills}

    # Collect all relevant skill names
    all_names = set()
    for s in job_skills:
        all_names.add(s["name"])
    # Also add prerequisite skills found in matched/missing
    for name, deps in _SKILL_DEPENDENCIES.items():
        if name in all_names:
            for d in deps:
                all_names.add(d)

    # Build node lookup
    skill_lookup = {}
    for s in job_skills:
        skill_lookup[s["name"]] = s

    nodes = []
    edges = []

    for name in sorted(all_names):
        if name in matched_names:
            status = "matched"
        elif name in missing_names:
            status = "missing"
        else:
            status = "supporting"
        layer = _classify_layer(name, _SKILL_DEPENDENCIES)
        cat = skill_lookup.get(name, {}).get("category", "")
        importance = ""
        for s in missing_skills:
            if s["name"] == name:
                importance = s.get("importance", "important")
                break
        nodes.append({
            "id": name, "status": status, "layer": layer,
            "category": cat, "importance": importance,
            "why_it_matters": _find_why_matters(name, job_text),
        })

    node_ids = {n["id"] for n in nodes}

    # Build edges from dependencies
    for name in node_ids:
        deps = _SKILL_DEPENDENCIES.get(name, [])
        for dep in deps:
            if dep in node_ids and dep != name:
                edges.append({"source": dep, "target": name})

    # Compute prerequisites and leads_to for each node
    prereqs = {n["id"]: [] for n in nodes}
    leads_to = {n["id"]: [] for n in nodes}
    for e in edges:
        leads_to.setdefault(e["source"], []).append(e["target"])
        prereqs.setdefault(e["target"], []).append(e["source"])
    for n in nodes:
        n["prerequisites"] = prereqs.get(n["id"], [])
        n["leads_to"] = leads_to.get(n["id"], [])

    # Recommended starting point: the most important missing skill with fewest unmet prereqs
    missing_nodes = [n for n in nodes if n["status"] == "missing"]
    recommended = None
    if missing_nodes:
        def _start_score(n):
            unmet = sum(1 for p in n["prerequisites"] if not any(x["id"] == p and x["status"] == "matched" for x in nodes))
            imp_w = {"critical": 0, "important": 1, "optional": 2}.get(n.get("importance", ""), 1)
            return (imp_w, unmet, -n["layer"])
        missing_nodes.sort(key=_start_score)
        rec = missing_nodes[0]
        # Build a reason based on prerequisites
        met_prereqs = [p for p in rec["prerequisites"] if any(x["id"] == p and x["status"] == "matched" for x in nodes)]
        unmet_prereqs = [p for p in rec["prerequisites"] if p not in met_prereqs]
        reason = f"Build this foundation before progressing to advanced skills in this role."
        if unmet_prereqs:
            reason = f"Learn {', '.join(unmet_prereqs)} first as a prerequisite, then progress to {rec['id']}."
        elif met_prereqs:
            reason = f"You already have {', '.join(met_prereqs)}. Next, build {rec['id']} to unlock further skills."
        recommended = {"skill": rec["id"], "reason": reason}

    # Build learning path from dependencies
    learning_path = []
    visited = set()
    # Start with matched skills (already have)
    for n in sorted(nodes, key=lambda x: x["layer"]):
        if n["status"] == "matched" and n["id"] not in visited:
            learning_path.append({"skill": n["id"], "status": "already_have", "layer": n["layer"]})
            visited.add(n["id"])
    # Then missing skills in dependency order (with cycle detection)
    def _add_missing(skill_id, path, visited_set, stack=None):
        if stack is None:
            stack = set()
        if skill_id in visited_set or skill_id in stack:
            return
        stack = stack | {skill_id}
        node = next((n for n in nodes if n["id"] == skill_id), None)
        if not node:
            return
        for prereq in node["prerequisites"]:
            _add_missing(prereq, path, visited_set, stack)
        if skill_id not in visited_set:
            path.append({"skill": skill_id, "status": "skill_gap", "layer": node["layer"]})
            visited_set.add(skill_id)
    for n in sorted(missing_nodes, key=lambda x: (x["layer"], x["id"])):
        _add_missing(n["id"], learning_path, visited)

    layer_names = {0: "Foundation", 1: "Core", 2: "Advanced", 3: "Specialized"}

    return {
        "nodes": nodes, "edges": edges,
        "recommended": recommended,
        "learning_path": learning_path,
        "layer_names": layer_names,
    }


# ---------------------------------------------------------------------------
# FEATURE 6 — Personalized Learning Path
# ---------------------------------------------------------------------------

def generate_learning_path(missing_skills, matched_skills, job_skills, level_gaps, job_text=""):
    """Generate a prioritized learning sequence based on skill gaps and dependencies."""
    path = []
    step = 1

    # Priority 1: Critical missing skills
    critical = [s for s in missing_skills if s.get("importance") == "critical"]
    for skill in sorted(critical, key=lambda s: s.get("job_count", 0), reverse=True):
        path.append({
            "step": step,
            "skill": skill["name"],
            "category": skill.get("category", ""),
            "status": "Not Started",
            "priority": "critical",
            "reason": f"Critical requirement — {skill['name']} is essential for this role.",
        })
        step += 1

    # Priority 2: Important missing skills
    important = [s for s in missing_skills if s.get("importance") == "important"]
    for skill in sorted(important, key=lambda s: s.get("job_count", 0), reverse=True):
        path.append({
            "step": step,
            "skill": skill["name"],
            "category": skill.get("category", ""),
            "status": "Not Started",
            "priority": "important",
            "reason": f"Important for this role — will strengthen your profile.",
        })
        step += 1

    # Priority 3: Level gaps (improve existing skills)
    for gap in level_gaps[:3]:
        path.append({
            "step": step,
            "skill": f"{gap['name']} ({gap['target_level']})",
            "category": "Skill Improvement",
            "status": "Not Started",
            "priority": "improvement",
            "reason": f"Level up from {gap['current_level']} to {gap['target_level']}.",
        })
        step += 1

    # Priority 4: Optional missing skills
    optional = [s for s in missing_skills if s.get("importance") == "optional"]
    for skill in sorted(optional, key=lambda s: s.get("job_count", 0), reverse=True)[:2]:
        path.append({
            "step": step,
            "skill": skill["name"],
            "category": skill.get("category", ""),
            "status": "Not Started",
            "priority": "optional",
            "reason": "Preferred qualification — nice to have.",
        })
        step += 1

    # Final step: Project + Interview Prep
    path.append({
        "step": step,
        "skill": "Build a Portfolio Project",
        "category": "Application",
        "status": "Not Started",
        "priority": "application",
        "reason": "Apply your new skills in a real project to demonstrate competence.",
    })
    step += 1

    path.append({
        "step": step,
        "skill": "Interview Preparation",
        "category": "Application",
        "status": "Not Started",
        "priority": "final",
        "reason": "Practice answering role-specific and technical questions.",
    })

    return path


# ---------------------------------------------------------------------------
# FEATURE 7 — Resume Version Comparison
# ---------------------------------------------------------------------------

def compare_analyses(old_analysis, new_analysis):
    """Compare two analysis results to show improvement."""
    old_score = old_analysis.get("overall_score", 0)
    new_score = new_analysis.get("overall_score", 0)

    old_matched = {s["name"] for s in old_analysis.get("matched_skills", [])}
    new_matched = {s["name"] for s in new_analysis.get("matched_skills", [])}

    old_missing = {s["name"] for s in old_analysis.get("missing_skills", [])}
    new_missing = {s["name"] for s in new_analysis.get("missing_skills", [])}

    old_kw_matched = set(old_analysis.get("keywords", {}).get("matched", []))
    new_kw_matched = set(new_analysis.get("keywords", {}).get("matched", []))

    skills_added = sorted(new_matched - old_matched)
    skills_removed = sorted(old_matched - new_matched)
    skills_improved = sorted(old_matched & new_matched)  # Still matched
    remaining_gaps = sorted(new_missing)

    old_kw_pct = old_analysis.get("keyword_match", 0)
    new_kw_pct = new_analysis.get("keyword_match", 0)

    # Find new evidence (skills in new but not in old resume skills)
    old_resume_skills = {s["name"] for s in old_analysis.get("resume_skills", [])}
    new_resume_skills = {s["name"] for s in new_analysis.get("resume_skills", [])}
    new_evidence = sorted(new_resume_skills - old_resume_skills)

    return {
        "old_score": old_score,
        "new_score": new_score,
        "old_matched": len(old_matched),
        "new_matched": len(new_matched),
        "old_missing": len(old_missing),
        "new_missing": len(new_missing),
        "old_keyword_match": old_kw_pct,
        "new_keyword_match": new_kw_pct,
        "skills_added": skills_added,
        "skills_removed": skills_removed,
        "skills_improved": skills_improved,
        "new_evidence": new_evidence,
        "remaining_gaps": remaining_gaps,
    }


# ---------------------------------------------------------------------------
# FEATURE 8 — Role Comparison
# ---------------------------------------------------------------------------

def compare_roles(analyses):
    """Compare the same resume across multiple job descriptions.

    analyses: list of (role_name, analysis_payload) tuples
    """
    results = []
    for role_name, analysis in analyses:
        results.append({
            "role": role_name,
            "overall_score": analysis.get("overall_score", 0),
            "skill_match": analysis.get("skill_match", 0),
            "keyword_match": analysis.get("keyword_match", 0),
            "matched_count": len(analysis.get("matched_skills", [])),
            "missing_count": len(analysis.get("missing_skills", [])),
            "matched_skills": [s["name"] for s in analysis.get("matched_skills", [])[:8]],
            "missing_skills": [s["name"] for s in analysis.get("missing_skills", [])[:8]],
            "breakdown": analysis.get("breakdown", {}),
            "token": analysis.get("token", ""),
        })

    results.sort(key=lambda r: -r["overall_score"])

    strongest = results[0] if results else None
    reason = ""
    if strongest:
        b = strongest["breakdown"]
        top_factor = max(b, key=b.get)
        reason = f"Highest {top_factor} alignment ({b[top_factor]}%) drives the strongest match."

    return {
        "roles": results,
        "strongest": strongest,
        "strongest_reason": reason,
    }
