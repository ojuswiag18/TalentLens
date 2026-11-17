"""TalentLens — Flask application entry point."""

import os
import tempfile
import time
import uuid

from flask import Flask, jsonify, redirect, render_template, request, session, url_for

from config import Config
from src.analytics import build_analytics
from src.interview import generate_interview_questions
from src.matcher import match_keywords, match_skills, classify_skill_priority
from src.resource_recommender import get_resources, search_resources
from src.resume_parser import ResumeParseError, cleanup, extract_text
from src.insights import (
    analyze_career_consistency,
    analyze_job_description,
    build_skill_dependency_map,
    compare_analyses,
    compare_roles,
    find_hidden_strengths,
    generate_learning_path,
    simulate_multi_improvement,
)
from src.scorer import compute_scores, generate_suggestions, simulate_improvement
from src.skill_extractor import classify_importance, extract_skills
from src.text_processor import clean_text
from src.text_improver import improve_summary

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = app.config.get("SECRET_KEY", "talentlens-session-key")

# PDF storage directory
PDF_STORAGE = os.path.join(os.path.dirname(__file__), "data", "pdfs")
os.makedirs(PDF_STORAGE, exist_ok=True)

# Lightweight in-memory analysis store (token -> payload)
ANALYSIS_STORE = {}

# Server-side user session data (session_id -> {resume_text, job_description, filename, token})
SESSION_DATA = {}


def _store_analysis(payload):
    token = uuid.uuid4().hex
    ANALYSIS_STORE[token] = {"data": payload, "created_at": time.time()}
    return token


def _get_analysis(token):
    if not token:
        return None
    entry = ANALYSIS_STORE.get(token)
    if not entry:
        return None
    if time.time() - entry["created_at"] > Config.ANALYSIS_TTL:
        ANALYSIS_STORE.pop(token, None)
        return None
    return entry["data"]


def _prune_store():
    now = time.time()
    expired = [
        t for t, e in ANALYSIS_STORE.items()
        if now - e["created_at"] > Config.ANALYSIS_TTL
    ]
    for t in expired:
        ANALYSIS_STORE.pop(t, None)


def _get_session_id():
    """Get or create a session ID for the current user."""
    if "sid" not in session:
        session["sid"] = uuid.uuid4().hex
    return session["sid"]


def _store_session_data(resume_text, job_description, filename, token):
    """Store user data server-side, keyed by session ID."""
    sid = _get_session_id()
    SESSION_DATA[sid] = {
        "resume_text": resume_text,
        "job_description": job_description,
        "filename": filename or "",
        "token": token,
        "created_at": time.time(),
    }


def _get_resume_text_for_token(token):
    """Get the full resume text stored with a given analysis token.
    Looks in SESSION_DATA for any session that holds this token."""
    if not token:
        return None
    for sid, data in SESSION_DATA.items():
        if data.get("token") == token:
            return data.get("resume_text")
    # Fallback: check if the analysis payload itself has it
    entry = ANALYSIS_STORE.get(token)
    if entry:
        payload = entry.get("data", {})
        return payload.get("resume_text_excerpt", "")
    return None


def _get_session_data():
    """Retrieve user data from server-side session store."""
    sid = session.get("sid")
    if not sid:
        return None
    data = SESSION_DATA.get(sid)
    if not data:
        return None
    if time.time() - data["created_at"] > Config.ANALYSIS_TTL:
        SESSION_DATA.pop(sid, None)
        return None
    return data


def _clear_session_data():
    """Clear user data from server-side session store."""
    sid = session.get("sid")
    if sid:
        SESSION_DATA.pop(sid, None)


def _save_pdf(file_storage, original_filename):
    """Save an uploaded PDF to storage with a unique ID.
    Returns (file_id, original_filename) or (None, None) if not a PDF."""
    if not file_storage or not original_filename:
        return None, None
    ext = original_filename.rsplit(".", 1)[1].lower() if "." in original_filename else ""
    if ext != "pdf":
        return None, None
    file_id = uuid.uuid4().hex
    dest = os.path.join(PDF_STORAGE, file_id + ".pdf")
    file_storage.save(dest)
    return file_id, original_filename


def _get_pdf_path(file_id):
    """Get the path to a stored PDF by its file_id."""
    if not file_id:
        return None
    # Sanitize file_id to prevent path traversal
    safe_id = os.path.basename(file_id)
    path = os.path.join(PDF_STORAGE, safe_id + ".pdf")
    if os.path.isfile(path):
        return path
    return None


def _delete_pdf(file_id):
    """Delete a stored PDF by its file_id."""
    if not file_id:
        return
    path = _get_pdf_path(file_id)
    if path:
        try:
            os.remove(path)
        except OSError:
            pass


def run_analysis(resume_text, job_description):
    """Run the full analysis pipeline over resume + job description text."""
    resume_text = clean_text(resume_text)
    job_text = clean_text(job_description)

    resume_skills = extract_skills(resume_text, source="resume")
    job_skills = extract_skills(job_text, source="job")

    matched_skills, missing_skills, extra_skills = match_skills(resume_skills, job_skills)

    importance = classify_importance(job_text, {s["name"] for s in job_skills})
    for skill in missing_skills:
        skill["importance"] = importance.get(skill["name"], "important")

    level_rank = {"basic": 0, "intermediate": 1, "advanced": 2}
    level_gaps = []
    resume_map = {s["name"].lower(): s for s in resume_skills}
    for skill in matched_skills:
        resume_level = resume_map[skill["name"].lower()].get("level")
        job_level = skill.get("level")
        if not resume_level or not job_level or resume_level == job_level:
            continue
        if level_rank.get(resume_level, 0) < level_rank.get(job_level, 0):
            level_gaps.append({
                "name": skill["name"],
                "current_level": resume_level,
                "target_level": job_level,
            })

    matched_keywords, missing_keywords = match_keywords(resume_text, job_text)

    scores = compute_scores(
        resume_text,
        job_text,
        matched_skills,
        job_skills,
        matched_keywords,
        job_keywords=list(matched_keywords) + list(missing_keywords),
    )

    payload = {
        **scores,
        "resume_text_excerpt": resume_text[:800],
        "resume_word_count": len(resume_text.split()),
        "job_text": job_text,
        "job_word_count": len(job_text.split()),
        "resume_skills": [
            {"name": s["name"], "category": s["category"], "count": s["count"], "level": s.get("level")}
            for s in resume_skills
        ],
        "job_skills": [
            {"name": s["name"], "category": s["category"], "count": s["count"]}
            for s in job_skills
        ],
        "matched_skills": [
            {"name": s["name"], "category": s["category"], "count": s["count"]}
            for s in matched_skills
        ],
        "missing_skills": [
            {"name": s["name"], "category": s["category"], "importance": s["importance"],
             "job_count": s["count"], "target_level": s.get("level")}
            for s in missing_skills
        ],
        "extra_skills": [
            {"name": s["name"], "category": s["category"]}
            for s in extra_skills
        ],
        "keywords": {
            "matched": matched_keywords[:20],
            "missing": missing_keywords[:20],
        },
        "level_gaps": level_gaps,
    }

    # Classify missing skill priorities
    payload["skill_priority"] = classify_skill_priority(missing_skills, job_text)

    payload["suggestions"] = generate_suggestions(payload)

    analytics = build_analytics(payload)
    # Add analytics data as top-level keys for template access
    payload["skill_match"] = analytics["skill_match_chart"]["matched"]
    payload["missing_skills_count"] = analytics["skill_match_chart"]["missing"]
    payload["compatibility_labels"] = analytics["compatibility_breakdown"]["labels"]
    payload["compatibility_values"] = analytics["compatibility_breakdown"]["values"]
    payload["interview_stats"] = analytics["interview_stats"]

    payload["interview"] = generate_interview_questions(
        job_text, job_skills, matched_skills, missing_skills
    )

    # --- New V2 Features ---
    payload["job_insights"] = analyze_job_description(
        job_text, job_skills, matched_skills, missing_skills
    )
    payload["hidden_strengths"] = find_hidden_strengths(
        resume_text, resume_skills, matched_skills, extra_skills, job_skills
    )
    payload["career_consistency"] = analyze_career_consistency(
        resume_text, job_text, resume_skills, job_skills,
        matched_skills, missing_skills, scores["breakdown"]
    )
    payload["dependency_map"] = build_skill_dependency_map(
        job_skills, matched_skills, missing_skills, job_text
    )
    payload["learning_path"] = generate_learning_path(
        missing_skills, matched_skills, job_skills, level_gaps, job_text
    )

    if not job_skills:
        payload["warning"] = "We couldn't identify enough skills from the job description."
    elif not resume_skills:
        payload["warning"] = "We couldn't identify enough skills from this resume."
    elif not missing_skills:
        payload["success"] = "Great match! No major skill gaps were detected."

    return payload


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/analyze")
def analyze_page():
    # Restore persisted session data if available
    session_data = _get_session_data()
    return render_template(
        "analyze.html",
        session_data=session_data,
    )


@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    try:
        if request.is_json:
            data = request.get_json(silent=True) or {}
            resume_text = data.get("resume_text", "").strip()
            job_description = data.get("job_description", "").strip()
        else:
            file = request.files.get("resume")
            resume_text = (request.form.get("resume_text") or "").strip()
            job_description = (request.form.get("job_description") or "").strip()
            raw_resume_text = ""  # Preserves newlines for resume parsing
            if file and file.filename:
                tmp_path = None
                try:
                    suffix = "." + file.filename.rsplit(".", 1)[1].lower()
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                        file.save(tmp)
                        tmp_path = tmp.name
                    # Read raw text first (preserving newlines for resume parsing)
                    with open(tmp_path, "rb") as fh:
                        raw_resume_text = extract_text(fh, file.filename)
                    resume_text = raw_resume_text
                except ResumeParseError as exc:
                    return jsonify({"error": str(exc)}), 400
                finally:
                    cleanup(tmp_path)
    except ResumeParseError as exc:
        return jsonify({"error": str(exc)}), 400

    if not resume_text:
        return jsonify({"error": "Please upload a resume or paste resume text."}), 400
    if not job_description:
        return jsonify({"error": "Please enter a job description."}), 400

    try:
        _prune_store()
        payload = run_analysis(resume_text, job_description)
        token = _store_analysis(payload)
        # Persist to server-side session so the data survives navigation
        filename = ""
        pdf_file_id = None
        if request.files.get("resume") and request.files["resume"].filename:
            filename = request.files["resume"].filename
            # Save PDF to storage if it's a PDF file
            pdf_file_id, _ = _save_pdf(request.files["resume"], filename)
        _store_session_data(raw_resume_text or resume_text, job_description, filename, token)
        return jsonify({"token": token, "pdf_file_id": pdf_file_id, **payload})
    except Exception as exc:
        app.logger.exception("Analysis failed")
        return jsonify({"error": "An unexpected error occurred during analysis."}), 500


@app.route("/api/analysis")
def api_analysis():
    payload = _get_analysis(request.args.get("token"))
    if not payload:
        return jsonify({"error": "Analysis not found or expired."}), 404
    return jsonify(payload)


@app.route("/results")
def results_page():
    payload = _get_analysis(request.args.get("token"))
    if not payload:
        return redirect(url_for("analyze_page"))
    return render_template("results.html", analysis=payload)


@app.route("/dashboard")
def dashboard_page():
    payload = _get_analysis(request.args.get("token"))
    if not payload:
        return redirect(url_for("analyze_page"))
    analytics_data = build_analytics(payload)
    return render_template(
        "dashboard.html",
        analysis=payload,
        analytics=analytics_data,
        token=request.args.get("token"),
    )


@app.route("/api/dashboard")
def api_dashboard():
    payload = _get_analysis(request.args.get("token"))
    if not payload:
        return jsonify({"error": "Analysis not found or expired."}), 404
    return jsonify(build_analytics(payload))


@app.route("/resources")
def resources_page():
    return render_template("resources.html")


@app.route("/resources/<skill>")
def resource_page(skill):
    resources = get_resources(skill)
    return render_template("resources.html", skill=skill, resources=resources)


@app.route("/api/resources/<skill>")
def api_resources(skill):
    resources = get_resources(skill)
    return jsonify({"skill": skill, "resources": resources})


@app.route("/api/resources/search")
def api_resources_search():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "Please provide a search query."}), 400
    results = search_resources(query)
    return jsonify({"query": query, "results": results})


@app.route("/api/simulate-multi", methods=["POST"])
def api_simulate_multi():
    try:
        data = request.get_json(silent=True) or {}
        token = data.get("token", "").strip()
        skill_names = data.get("skill_names", [])
    except Exception:
        return jsonify({"error": "Invalid request body."}), 400

    if not token or not skill_names:
        return jsonify({"error": "Both token and skill_names are required."}), 400

    payload = _get_analysis(token)
    if not payload:
        return jsonify({"error": "Analysis not found or expired."}), 404

    try:
        result = simulate_multi_improvement(payload, skill_names)
        return jsonify(result)
    except Exception as exc:
        app.logger.exception("Multi-simulation failed")
        return jsonify({"error": "An unexpected error occurred."}), 500


@app.route("/api/compare-resume", methods=["POST"])
def api_compare_resume():
    try:
        data = request.get_json(silent=True) or {}
        old_token = data.get("old_token", "").strip()
        new_token = data.get("new_token", "").strip()
    except Exception:
        return jsonify({"error": "Invalid request body."}), 400

    old_payload = _get_analysis(old_token)
    new_payload = _get_analysis(new_token)
    if not old_payload or not new_payload:
        return jsonify({"error": "One or both analyses not found or expired."}), 404

    try:
        result = compare_analyses(old_payload, new_payload)
        return jsonify(result)
    except Exception as exc:
        app.logger.exception("Comparison failed")
        return jsonify({"error": "An unexpected error occurred."}), 500


@app.route("/api/analyze-for-role", methods=["POST"])
def api_analyze_for_role():
    """Analyze a new job description using the resume from an existing token.
    Used by the role comparison feature to reuse the current resume."""
    try:
        data = request.get_json(silent=True) or {}
        current_token = data.get("current_token", "").strip()
        job_description = data.get("job_description", "").strip()
        role_name = data.get("role_name", "").strip()
    except Exception:
        return jsonify({"error": "Invalid request body."}), 400

    if not current_token:
        return jsonify({"error": "Current analysis token is required."}), 400
    if not job_description:
        return jsonify({"error": "Job description is required."}), 400

    resume_text = _get_resume_text_for_token(current_token)
    if not resume_text:
        return jsonify({"error": "Could not find resume text for the current analysis."}), 400

    try:
        _prune_store()
        payload = run_analysis(resume_text, job_description)
        new_token = _store_analysis(payload)
        return jsonify({
            "token": new_token,
            "role_name": role_name or "Unknown Role",
            **payload,
        })
    except Exception as exc:
        app.logger.exception("Role analysis failed")
        return jsonify({"error": "An unexpected error occurred during analysis."}), 500


@app.route("/api/compare-roles", methods=["POST"])
def api_compare_roles():
    try:
        data = request.get_json(silent=True) or {}
        tokens = data.get("tokens", [])  # list of {token, role_name}
    except Exception:
        return jsonify({"error": "Invalid request body."}), 400

    if not tokens or len(tokens) < 2:
        return jsonify({"error": "At least two role analyses are required."}), 400

    analyses = []
    for item in tokens:
        t = item.get("token", "")
        name = item.get("role_name", "Unknown Role")
        p = _get_analysis(t)
        if p:
            analyses.append((name, p))

    if len(analyses) < 2:
        return jsonify({"error": "Could not find enough valid analyses."}), 400

    try:
        result = compare_roles(analyses)
        return jsonify(result)
    except Exception as exc:
        app.logger.exception("Role comparison failed")
        return jsonify({"error": "An unexpected error occurred."}), 500


from flask import send_file


@app.route("/api/pdf/<file_id>")
def api_view_pdf(file_id):
    """Serve a stored PDF for viewing."""
    path = _get_pdf_path(file_id)
    if not path:
        return jsonify({"error": "PDF not found."}), 404
    return send_file(path, mimetype="application/pdf")


@app.route("/api/pdf/<file_id>/download")
def api_download_pdf(file_id):
    """Download a stored PDF with the original filename."""
    path = _get_pdf_path(file_id)
    if not path:
        return jsonify({"error": "PDF not found."}), 404
    # Get original filename from the request or use a default
    original_name = request.args.get("name", "resume.pdf")
    return send_file(path, mimetype="application/pdf", as_attachment=True, download_name=original_name)


@app.route("/api/pdf/<file_id>", methods=["DELETE"])
def api_delete_pdf(file_id):
    """Delete a stored PDF."""
    _delete_pdf(file_id)
    return jsonify({"ok": True})


@app.route("/api/clear-session", methods=["POST"])
def api_clear_session():
    """Clear the current user's session data."""
    _clear_session_data()
    session.pop("sid", None)
    return jsonify({"ok": True})


@app.route("/api/simulate", methods=["POST"])
def api_simulate():
    try:
        data = request.get_json(silent=True) or {}
        token = data.get("token", "").strip()
        skill_name = data.get("skill_name", "").strip()
    except Exception:
        return jsonify({"error": "Invalid request body."}), 400

    if not token or not skill_name:
        return jsonify({"error": "Both token and skill_name are required."}), 400

    payload = _get_analysis(token)
    if not payload:
        return jsonify({"error": "Analysis not found or expired."}), 404

    # Verify the skill is actually missing
    missing_names = {s["name"].lower() for s in payload.get("missing_skills", [])}
    if skill_name.lower() not in missing_names:
        return jsonify({"error": f"'{skill_name}' is not a missing skill in this analysis."}), 400

    try:
        result = simulate_improvement(payload, skill_name)
        return jsonify(result)
    except Exception as exc:
        app.logger.exception("Simulation failed")
        return jsonify({"error": "An unexpected error occurred during simulation."}), 500


@app.route("/interview")
def interview_page():
    """Interview preparation page using the current analysis."""
    # Try to get the current analysis from session
    session_data = _get_session_data()
    analysis = None
    if session_data and session_data.get("token"):
        analysis = _get_analysis(session_data["token"])
    return render_template("interview.html", analysis=analysis)


# ---------------------------------------------------------------------------
# Resume Builder
# ---------------------------------------------------------------------------

# In-memory store for saved resume versions: {version_id: {data, created_at}}
RESUME_VERSIONS = {}

# Session-keyed saved resumes: {session_id: {resume_id: {data, created_at}}}
SAVED_RESUMES = {}


def _store_resume_version(data):
    """Store a resume version and return its ID."""
    vid = uuid.uuid4().hex
    RESUME_VERSIONS[vid] = {"data": data, "created_at": time.time()}
    return vid


def _get_resume_version(vid):
    """Retrieve a stored resume version."""
    if not vid:
        return None
    entry = RESUME_VERSIONS.get(vid)
    if not entry:
        return None
    if time.time() - entry["created_at"] > Config.ANALYSIS_TTL:
        RESUME_VERSIONS.pop(vid, None)
        return None
    return entry["data"]


def _save_resume_to_session(resume_id, data):
    """Save a resume to the user's session store."""
    sid = _get_session_id()
    if sid not in SAVED_RESUMES:
        SAVED_RESUMES[sid] = {}
    SAVED_RESUMES[sid][resume_id] = {
        "data": data,
        "created_at": time.time(),
        "updated_at": time.time(),
    }


def _update_resume_in_session(resume_id, data):
    """Update an existing resume in the user's session store."""
    sid = _get_session_id()
    if sid in SAVED_RESUMES and resume_id in SAVED_RESUMES[sid]:
        SAVED_RESUMES[sid][resume_id]["data"] = data
        SAVED_RESUMES[sid][resume_id]["updated_at"] = time.time()
        return True
    return False


def _get_saved_resumes_list():
    """Get list of all saved resumes for the current session."""
    sid = session.get("sid")
    if not sid or sid not in SAVED_RESUMES:
        return []
    result = []
    for rid, entry in SAVED_RESUMES[sid].items():
        d = entry["data"]
        result.append({
            "id": rid,
            "name": d.get("resume_data", {}).get("personal", {}).get("name", "Untitled Resume"),
            "template": d.get("template", "modern"),
            "created_at": entry["created_at"],
            "updated_at": entry["updated_at"],
        })
    result.sort(key=lambda x: x["updated_at"], reverse=True)
    return result


def _get_saved_resume(resume_id):
    """Get a specific saved resume from the session store."""
    sid = session.get("sid")
    if not sid or sid not in SAVED_RESUMES:
        return None
    entry = SAVED_RESUMES[sid].get(resume_id)
    if not entry:
        return None
    return entry["data"]


def _delete_saved_resume(resume_id):
    """Delete a saved resume from the session store."""
    sid = session.get("sid")
    if sid and sid in SAVED_RESUMES and resume_id in SAVED_RESUMES[sid]:
        del SAVED_RESUMES[sid][resume_id]
        return True
    return False


def _build_resume_from_analysis(analysis, token=None):
    """Build the initial resume data structure from analysis results."""
    resume_text = analysis.get("resume_text_excerpt", "")
    resume_text_full = ""
    # Try to find full resume text from session data
    lookup_token = token or analysis.get("token")
    for sid, sdata in SESSION_DATA.items():
        if lookup_token and sdata.get("token") == lookup_token:
            resume_text_full = sdata.get("resume_text", "")
            break

    text = resume_text_full or resume_text

    # Extract sections from resume text using simple heuristics
    sections = _parse_resume_sections(text)

    # Build skills list from analysis
    skills = []
    for s in analysis.get("matched_skills", []):
        skills.append({"name": s["name"], "category": s.get("category", "")})
    for s in analysis.get("missing_skills", [])[:5]:
        skills.append({"name": s["name"], "category": s.get("category", ""), "missing": True})
    for s in analysis.get("resume_skills", []):
        if not any(sk["name"].lower() == s["name"].lower() for sk in skills):
            skills.append({"name": s["name"], "category": s.get("category", "")})

    return {
        "personal": sections.get("personal", {}),
        "summary": sections.get("summary", ""),
        "experience": sections.get("experience", []),
        "projects": sections.get("projects", []),
        "skills": skills,
        "education": sections.get("education", []),
        "certifications": sections.get("certifications", []),
        "achievements": sections.get("achievements", []),
        "additional": sections.get("additional", []),
    }


def _parse_resume_sections(text):
    """Parse resume text into structured sections."""
    lines = text.split("\n")
    sections = {
        "personal": {},
        "summary": "",
        "experience": [],
        "projects": [],
        "skills": [],
        "education": [],
        "certifications": [],
        "achievements": [],
        "additional": [],
    }

    if not lines:
        return sections

    # First line is usually the name
    name_line = lines[0].strip()
    if name_line:
        sections["personal"]["name"] = name_line

    # Look for contact info in first few lines
    for line in lines[:10]:
        low = line.lower()
        if "@" in line and not sections["personal"].get("email"):
            # Strip common labels like "Email: "
            val = line.strip()
            for prefix in ["email:", "email -", "e-mail:"]:
                if low.startswith(prefix):
                    val = line.strip()[len(prefix):].strip()
            sections["personal"]["email"] = val
        elif any(p in low for p in ["phone", "tel"]) and not sections["personal"].get("phone"):
            val = line.strip()
            for prefix in ["phone:", "tel:", "telephone:", "mobile:", "cell:"]:
                if low.startswith(prefix):
                    val = line.strip()[len(prefix):].strip()
            sections["personal"]["phone"] = val
        elif line.strip().startswith("+") and not sections["personal"].get("phone"):
            sections["personal"]["phone"] = line.strip()
        elif any(p in low for p in ["linkedin", "github"]) and not sections["personal"].get("linkedin"):
            val = line.strip()
            for prefix in ["linkedin:", "linkedin -", "github:", "github -"]:
                if low.startswith(prefix):
                    val = line.strip()[len(prefix):].strip()
            sections["personal"]["linkedin"] = val

    # Section detection
    section_headers = {
        "summary": ["summary", "objective", "profile", "about"],
        "experience": ["experience", "work experience", "employment", "professional experience"],
        "projects": ["projects", "project work", "personal projects"],
        "skills": ["skills", "technical skills", "technologies", "competencies"],
        "education": ["education", "academic background", "qualifications"],
        "certifications": ["certifications", "certificates", "licenses"],
        "achievements": ["achievements", "awards", "honors"],
    }

    current_section = None
    section_content = []

    for line in lines[1:]:
        stripped = line.strip()
        low = stripped.lower().rstrip(":")

        # Check if this line is a section header
        matched_section = None
        for sec_key, headers in section_headers.items():
            for header in headers:
                if low == header or low == header + ":":
                    matched_section = sec_key
                    break
            if matched_section:
                break

        if matched_section:
            # Save previous section content
            if current_section and section_content:
                _save_section(sections, current_section, section_content)
            current_section = matched_section
            section_content = []
        elif current_section and stripped:
            section_content.append(stripped)

    # Save last section
    if current_section and section_content:
        _save_section(sections, current_section, section_content)

    return sections


def _save_section(sections, section_name, lines):
    """Save parsed section content into structured format."""
    if section_name == "summary":
        sections["summary"] = " ".join(lines)
    elif section_name == "skills":
        sections["skills"] = lines
    elif section_name == "experience":
        entries = []
        current_entry = None
        for line in lines:
            has_dates = any(y in line for y in ["20", "19", "present", "current"])
            has_separator = "|" in line or " - " in line or "\u2014" in line
            is_bullet = line.startswith("-") or line.startswith("•")
            is_new_job = (has_dates or has_separator) and (not current_entry or current_entry.get("_has_header"))
            if is_new_job:
                if current_entry and current_entry.get("title"):
                    entries.append({
                        "title": current_entry.get("title", ""),
                        "company": current_entry.get("company", ""),
                        "dates": current_entry.get("dates", ""),
                        "description": " ".join(current_entry.get("desc_lines", [])),
                        "bullets": current_entry.get("bullets", []),
                    })
                parts = [p.strip() for p in line.replace("\u2014", "|").split("|")]
                title = parts[0] if parts else ""
                company = parts[1] if len(parts) > 1 else ""
                dates = parts[2] if len(parts) > 2 else ""
                if not dates and has_dates:
                    dates = line.strip()
                    title = current_entry.get("title", "") if current_entry else ""
                    company = current_entry.get("company", "") if current_entry else ""
                current_entry = {"title": title, "company": company, "dates": dates, "desc_lines": [], "bullets": [], "_has_header": True}
            elif is_bullet and current_entry:
                bullet_text = line.lstrip("- •").strip()
                current_entry["bullets"].append(bullet_text)
            elif current_entry:
                current_entry["desc_lines"].append(line)
            else:
                current_entry = {"title": line, "company": "", "dates": "", "desc_lines": [], "bullets": [], "_has_header": True}
        if current_entry and current_entry.get("title"):
            entries.append({
                "title": current_entry.get("title", ""),
                "company": current_entry.get("company", ""),
                "dates": current_entry.get("dates", ""),
                "description": " ".join(current_entry.get("desc_lines", [])),
                "bullets": current_entry.get("bullets", []),
            })
        sections[section_name] = entries if entries else lines
    elif section_name == "projects":
        entries = []
        current_entry = None
        for line in lines:
            is_header = not line.startswith("-") and not line.startswith("•") and not current_entry
            if is_header:
                if current_entry:
                    entries.append({"name": current_entry.get("name", ""), "description": " ".join(current_entry.get("desc_lines", []))})
                current_entry = {"name": line, "desc_lines": []}
            elif current_entry:
                current_entry["desc_lines"].append(line.lstrip("- •").strip())
        if current_entry:
            entries.append({"name": current_entry.get("name", ""), "description": " ".join(current_entry.get("desc_lines", []))})
        sections[section_name] = entries if entries else lines
    else:
        sections[section_name] = lines


def _generate_pdf(resume_data, template_name, job_title):
    """Generate a professional A4 PDF resume using fpdf2.
    
    Uses the centralized template configuration from src.resume_templates
    to ensure consistency with Live Preview and DOCX exports.
    """
    from fpdf import FPDF
    from src.resume_templates import get_template, get_section_order, get_section_label

    tmpl = get_template(template_name)
    pal = tmpl["colors_rgb"]
    cfg = tmpl["sizes"]
    spc = tmpl["spacing"]
    font_name = tmpl["fonts"]["pdf"]

    # A4 geometry (mm)
    PAGE_W, PAGE_H = 210, 297
    MARGIN = 20
    CONTENT_W = PAGE_W - 2 * MARGIN  # 170 mm

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=MARGIN)
    pdf.set_margins(MARGIN, MARGIN, MARGIN)
    pdf.add_page()

    personal = resume_data.get("personal", {})
    name = personal.get("name", "Resume")
    title_line = job_title if job_title and job_title.lower() != "resume" else ""

    def _safe(text):
        return str(text).encode("latin-1", errors="replace").decode("latin-1")

    def _line(text, font_style="", font_size=None, align="L", color=None):
        """Write one line, resetting x to the left margin each time."""
        size = font_size or cfg["body"]
        pdf.set_font(font_name, font_style, size)
        pdf.set_text_color(*(color or pal["text"]))
        pdf.set_x(MARGIN)
        pdf.multi_cell(w=CONTENT_W, h=spc["line_h"], text=_safe(text), align=align)

    def _section(title):
        """Section heading with coloured underline — matches Live Preview style."""
        pdf.ln(spc["section_before"])
        pdf.set_font(font_name, "B", cfg["heading"])
        pdf.set_text_color(*pal["heading"])
        pdf.set_x(MARGIN)
        pdf.multi_cell(w=CONTENT_W, h=spc["section_heading_h"], text=_safe(title.upper()), align="L")
        # Underline
        y2 = pdf.get_y()
        pdf.set_draw_color(*pal["accent"])
        pdf.set_line_width(0.6)
        pdf.line(MARGIN, y2, PAGE_W - MARGIN, y2)
        pdf.ln(spc["section_after"])
        pdf.set_text_color(*pal["text"])

    def _check_page(needed_mm=20):
        if pdf.get_y() > PAGE_H - MARGIN - needed_mm:
            pdf.add_page()

    def _extract_skill_names(skills):
        return [s["name"] if isinstance(s, dict) else str(s) for s in skills]

    # ================================================================
    # HEADER — matches Live Preview exactly
    # ================================================================
    # Name
    name_size = cfg["name_executive"] if template_name == "executive" else cfg["name"]
    pdf.set_font(font_name, "B", name_size)
    pdf.set_text_color(*pal["text"])
    pdf.set_x(MARGIN)
    pdf.cell(w=CONTENT_W, h=spc["header_ln"], text=_safe(name), align="C")
    pdf.ln(spc["header_ln"])

    # Professional title
    if title_line:
        pdf.set_font(font_name, "", cfg["title"])
        pdf.set_text_color(*pal["accent"])
        pdf.set_x(MARGIN)
        pdf.cell(w=CONTENT_W, h=spc["title_ln"], text=_safe(title_line), align="C")
        pdf.ln(spc["title_ln"])
        pdf.set_text_color(*pal["text"])

    # Contact line — same fields as Live Preview
    contact_parts = []
    for field in ["email", "phone", "linkedin", "github"]:
        if personal.get(field):
            contact_parts.append(personal[field])
    if contact_parts:
        pdf.set_font(font_name, "", cfg["contact"])
        pdf.set_text_color(*pal["muted"])
        pdf.set_x(MARGIN)
        pdf.cell(w=CONTENT_W, h=spc["line_h"], text=_safe("  |  ".join(contact_parts)), align="C")
        pdf.ln(spc["contact_ln"])
        pdf.set_text_color(*pal["text"])

    # Separator
    pdf.set_draw_color(*pal["separator"])
    pdf.set_line_width(0.3)
    pdf.line(MARGIN, pdf.get_y(), PAGE_W - MARGIN, pdf.get_y())
    pdf.ln(spc["separator_after"])

    # ================================================================
    # SECTIONS — iterate in canonical order, same as Live Preview
    # ================================================================
    for section_key in get_section_order():
        if section_key == "summary":
            if resume_data.get("summary"):
                _section(get_section_label(section_key))
                _line(resume_data["summary"])
                pdf.ln(spc["body_after"])

        elif section_key == "experience":
            if resume_data.get("experience"):
                _section(get_section_label(section_key))
                for exp in resume_data["experience"]:
                    if isinstance(exp, dict):
                        _check_page(30)
                        if exp.get("title"):
                            _line(exp["title"], "B", cfg["body"])
                        meta_parts = []
                        if exp.get("company"):
                            meta_parts.append(exp["company"])
                        if exp.get("dates"):
                            meta_parts.append(exp["dates"])
                        if meta_parts:
                            _line("  |  ".join(meta_parts), "I", cfg["meta"], color=pal["muted"])
                        if exp.get("bullets"):
                            for b in exp["bullets"]:
                                _line("  \u2022  " + b)
                        elif exp.get("description"):
                            _line(exp["description"])
                        pdf.ln(spc["experience_after"])
                    else:
                        _line("  \u2022  " + str(exp))

        elif section_key == "projects":
            if resume_data.get("projects"):
                _section(get_section_label(section_key))
                for proj in resume_data["projects"]:
                    if isinstance(proj, dict):
                        _check_page(20)
                        if proj.get("name"):
                            _line(proj["name"], "B", cfg["body"])
                        if proj.get("description"):
                            _line(proj["description"])
                        pdf.ln(spc["project_after"])
                    else:
                        _line("  \u2022  " + str(proj))

        elif section_key == "skills":
            if resume_data.get("skills"):
                _section(get_section_label(section_key))
                _line(", ".join(_extract_skill_names(resume_data["skills"])))
                pdf.ln(spc["body_after"])

        elif section_key == "education":
            if resume_data.get("education"):
                _section(get_section_label(section_key))
                for edu in resume_data["education"]:
                    _check_page(12)
                    if isinstance(edu, dict):
                        if edu.get("degree"):
                            _line(edu["degree"], "B", cfg["body"])
                        meta = edu.get("school", "") or edu.get("institution", "")
                        if edu.get("dates"):
                            meta += ("  |  " if meta else "") + edu["dates"]
                        if meta:
                            _line(meta, "I", cfg["meta"], color=pal["muted"])
                    else:
                        _line("  \u2022  " + str(edu))

        elif section_key == "certifications":
            if resume_data.get("certifications"):
                _section(get_section_label(section_key))
                for cert in resume_data["certifications"]:
                    _check_page(10)
                    _line("  \u2022  " + str(cert))

        elif section_key == "achievements":
            if resume_data.get("achievements"):
                _section(get_section_label(section_key))
                for ach in resume_data["achievements"]:
                    _check_page(10)
                    _line("  \u2022  " + str(ach))

        elif section_key == "languages":
            if resume_data.get("languages"):
                _section(get_section_label(section_key))
                lang_names = [l if isinstance(l, str) else l.get("name", str(l)) for l in resume_data["languages"]]
                _line(", ".join(lang_names))
                pdf.ln(spc["body_after"])

        elif section_key == "links":
            if resume_data.get("links"):
                _section(get_section_label(section_key))
                for link in resume_data["links"]:
                    _check_page(10)
                    link_text = link if isinstance(link, str) else link.get("url", link.get("name", str(link)))
                    _line("  \u2022  " + str(link_text))

    return bytes(pdf.output())


def _generate_docx(resume_data, template_name, job_title):
    """Generate a professional DOCX resume using python-docx.
    
    Uses the centralized template configuration from src.resume_templates
    to ensure consistency with Live Preview and PDF exports.
    """
    from docx import Document
    from docx.shared import Pt, RGBColor, Cm
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    from src.resume_templates import get_template, get_section_order, get_section_label

    tmpl = get_template(template_name)
    pal = tmpl["colors_rgb"]
    cfg = tmpl["sizes"]
    font_name = tmpl["fonts"]["docx"]

    doc = Document()

    # A4 margins (20mm)
    for section in doc.sections:
        section.left_margin = Cm(2.0)
        section.right_margin = Cm(2.0)
        section.top_margin = Cm(2.0)
        section.bottom_margin = Cm(2.0)
        section.page_width = Cm(21.0)
        section.page_height = Cm(29.7)

    accent = RGBColor(*pal["accent"])
    heading_color = RGBColor(*pal["heading"])
    text_color = RGBColor(*pal["text"])
    muted_color = RGBColor(*pal["muted"])
    separator_color = RGBColor(*pal["separator"])

    personal = resume_data.get("personal", {})
    name = personal.get("name", "Resume")
    title_line = job_title if job_title and job_title.lower() != "resume" else ""

    def _add_bottom_border(paragraph, color_rgb):
        pPr = paragraph._p.get_or_add_pPr()
        pBdr = pPr.makeelement(qn('w:pBdr'), {})
        bottom = pBdr.makeelement(qn('w:bottom'), {
            qn('w:val'): 'single',
            qn('w:sz'): '6',
            qn('w:space'): '1',
            qn('w:color'): '{:02X}{:02X}{:02X}'.format(*color_rgb),
        })
        pBdr.append(bottom)
        pPr.append(pBdr)

    # ================================================================
    # HEADER — matches Live Preview exactly
    # ================================================================
    # Name
    name_size = cfg["name_executive"] if template_name == "executive" else cfg["name"]
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run(name)
    run.bold = True
    run.font.size = Pt(name_size)
    run.font.name = font_name
    run.font.color.rgb = text_color

    # Title
    if title_line:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(4)
        run = p.add_run(title_line)
        run.font.size = Pt(cfg["title"])
        run.font.color.rgb = accent
        run.font.name = font_name

    # Contact — same fields as Live Preview
    contact_parts = []
    for field in ["email", "phone", "linkedin", "github"]:
        if personal.get(field):
            contact_parts.append(personal[field])
    if contact_parts:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(4)
        run = p.add_run("  |  ".join(contact_parts))
        run.font.size = Pt(cfg["contact"])
        run.font.color.rgb = muted_color
        run.font.name = font_name

    # Separator
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(6)
    _add_bottom_border(p, pal["separator"])

    def add_section_heading(title):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(4)
        run = p.add_run(title.upper())
        run.bold = True
        run.font.size = Pt(cfg["heading"])
        run.font.color.rgb = heading_color
        run.font.name = font_name
        _add_bottom_border(p, pal["accent"])

    def add_text(text, bold=False, italic=False, size=None, color=None):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(2)
        run = p.add_run(text)
        run.font.size = Pt(size or cfg["body"])
        run.font.name = font_name
        run.bold = bold
        run.italic = italic
        run.font.color.rgb = color or text_color
        return p

    def add_bullet(text):
        p = doc.add_paragraph(text, style="List Bullet")
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(1)
        for run in p.runs:
            run.font.size = Pt(cfg["body"])
            run.font.name = font_name
            run.font.color.rgb = text_color

    def _extract_skill_names(skills):
        return [s["name"] if isinstance(s, dict) else str(s) for s in skills]

    # ================================================================
    # SECTIONS — iterate in canonical order, same as Live Preview
    # ================================================================
    for section_key in get_section_order():
        if section_key == "summary":
            if resume_data.get("summary"):
                add_section_heading(get_section_label(section_key))
                add_text(resume_data["summary"])

        elif section_key == "experience":
            if resume_data.get("experience"):
                add_section_heading(get_section_label(section_key))
                for exp in resume_data["experience"]:
                    if isinstance(exp, dict):
                        if exp.get("title"):
                            add_text(exp["title"], bold=True)
                        meta_parts = []
                        if exp.get("company"):
                            meta_parts.append(exp["company"])
                        if exp.get("dates"):
                            meta_parts.append(exp["dates"])
                        if meta_parts:
                            add_text("  |  ".join(meta_parts), italic=True, size=cfg["meta"], color=muted_color)
                        if exp.get("bullets"):
                            for b in exp["bullets"]:
                                add_bullet(b)
                        elif exp.get("description"):
                            add_text(exp["description"])
                    else:
                        add_bullet(str(exp))

        elif section_key == "projects":
            if resume_data.get("projects"):
                add_section_heading(get_section_label(section_key))
                for proj in resume_data["projects"]:
                    if isinstance(proj, dict):
                        if proj.get("name"):
                            add_text(proj["name"], bold=True)
                        if proj.get("description"):
                            add_text(proj["description"])
                    else:
                        add_bullet(str(proj))

        elif section_key == "skills":
            if resume_data.get("skills"):
                add_section_heading(get_section_label(section_key))
                add_text(", ".join(_extract_skill_names(resume_data["skills"])))

        elif section_key == "education":
            if resume_data.get("education"):
                add_section_heading(get_section_label(section_key))
                for edu in resume_data["education"]:
                    if isinstance(edu, dict):
                        if edu.get("degree"):
                            add_text(edu["degree"], bold=True)
                        meta = edu.get("school", "") or edu.get("institution", "")
                        if edu.get("dates"):
                            meta += ("  |  " if meta else "") + edu["dates"]
                        if meta:
                            add_text(meta, italic=True, size=cfg["meta"], color=muted_color)
                    else:
                        add_bullet(str(edu))

        elif section_key == "certifications":
            if resume_data.get("certifications"):
                add_section_heading(get_section_label(section_key))
                for cert in resume_data["certifications"]:
                    add_bullet(str(cert))

        elif section_key == "achievements":
            if resume_data.get("achievements"):
                add_section_heading(get_section_label(section_key))
                for ach in resume_data["achievements"]:
                    add_bullet(str(ach))

        elif section_key == "languages":
            if resume_data.get("languages"):
                add_section_heading(get_section_label(section_key))
                lang_names = [l if isinstance(l, str) else l.get("name", str(l)) for l in resume_data["languages"]]
                add_text(", ".join(lang_names))

        elif section_key == "links":
            if resume_data.get("links"):
                add_section_heading(get_section_label(section_key))
                for link in resume_data["links"]:
                    link_text = link if isinstance(link, str) else link.get("url", link.get("name", str(link)))
                    add_bullet(str(link_text))

    from io import BytesIO
    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()


@app.route("/resume-builder")
def resume_builder_page():
    """Resume Builder page — loads current analysis if available."""
    session_data = _get_session_data()
    analysis = None
    token = request.args.get("token") or (session_data.get("token") if session_data else None)
    if token:
        analysis = _get_analysis(token)
    # Pre-parse resume data so the frontend doesn't need to re-parse stripped text
    resume_data = None
    if analysis:
        resume_data = _build_resume_from_analysis(analysis, token=token)

    # Quick Edit: load a previously saved resume
    resume_id = request.args.get("resume_id")
    saved_resume = None
    if resume_id:
        saved_resume = _get_saved_resume(resume_id)
        if saved_resume:
            resume_data = saved_resume.get("resume_data")
            # Use saved template if available
            saved_template = saved_resume.get("template", "modern")

    saved_resumes_list = _get_saved_resumes_list()
    saved_template_val = "modern"
    if saved_resume:
        saved_template_val = saved_resume.get("template", "modern")

    return render_template(
        "resume_builder.html",
        analysis=analysis,
        token=token,
        resume_data=resume_data,
        saved_resumes_list=saved_resumes_list,
        loaded_resume_id=resume_id if saved_resume else None,
        saved_template=saved_template_val if saved_resume else None,
    )


@app.route("/api/resume-builder/save", methods=["POST"])
def api_resume_builder_save():
    """Save a resume version."""
    try:
        data = request.get_json(silent=True) or {}
        resume_data = data.get("resume_data", {})
        job_title = data.get("job_title", "Resume")
        template_name = data.get("template", "modern")
        source_token = data.get("source_token", "")
        existing_resume_id = data.get("existing_resume_id", "")
    except Exception:
        return jsonify({"error": "Invalid request body."}), 400

    save_data = {
        "resume_data": resume_data,
        "job_title": job_title,
        "template": template_name,
        "source_token": source_token,
    }

    # Save to version store
    version_id = _store_resume_version(save_data)

    # Also save to session-keyed store for Quick Edit access
    if existing_resume_id:
        # Update existing saved resume
        _update_resume_in_session(existing_resume_id, save_data)
        resume_id = existing_resume_id
    else:
        # Create new saved resume
        resume_id = uuid.uuid4().hex
        _save_resume_to_session(resume_id, save_data)

    return jsonify({"version_id": version_id, "resume_id": resume_id, "ok": True})


@app.route("/api/resume-builder/saved", methods=["GET"])
def api_resume_builder_saved():
    """List all saved resumes for the current session."""
    return jsonify({"saved": _get_saved_resumes_list()})


@app.route("/api/resume-builder/delete", methods=["POST"])
def api_resume_builder_delete():
    """Delete a saved resume."""
    try:
        data = request.get_json(silent=True) or {}
        resume_id = data.get("resume_id", "")
    except Exception:
        return jsonify({"error": "Invalid request body."}), 400
    if not resume_id:
        return jsonify({"error": "resume_id is required."}), 400
    ok = _delete_saved_resume(resume_id)
    return jsonify({"ok": ok})


@app.route("/api/resume-builder/recalculate", methods=["POST"])
def api_resume_builder_recalculate():
    """Recalculate ATS score with edited resume."""
    try:
        data = request.get_json(silent=True) or {}
        resume_data = data.get("resume_data", {})
        source_token = data.get("source_token", "")
    except Exception:
        return jsonify({"error": "Invalid request body."}), 400

    # Get the job description from the source analysis
    analysis = _get_analysis(source_token)
    if not analysis:
        return jsonify({"error": "Source analysis not found."}), 404

    # Reconstruct resume text from edited data
    resume_text = _resume_data_to_text(resume_data)
    job_text = analysis.get("job_text", "")

    if not resume_text or not job_text:
        return jsonify({"error": "Insufficient data for recalculation."}), 400

    try:
        new_payload = run_analysis(resume_text, job_text)
        return jsonify({
            "overall_score": new_payload.get("overall_score", 0),
            "matched_skills": new_payload.get("matched_skills", []),
            "missing_skills": new_payload.get("missing_skills", []),
            "keyword_match": new_payload.get("keyword_match", 0),
            "breakdown": new_payload.get("breakdown", {}),
        })
    except Exception as exc:
        app.logger.exception("ATS recalculation failed")
        return jsonify({"error": "Recalculation failed."}), 500


@app.route("/api/resume-builder/improve-summary", methods=["POST"])
def api_resume_builder_improve_summary():
    """Generate an improved version of a resume section.
    
    Accepts full resume context to enable career-independent improvements.
    """
    try:
        data = request.get_json(silent=True) or {}
        text = data.get("text", "").strip()
        source_token = data.get("source_token", "")
        resume_data = data.get("resume_data", {})
        job_title = data.get("job_title", "")
        job_description = data.get("job_description", "")
    except Exception:
        return jsonify({"error": "Invalid request body."}), 400

    if not text:
        return jsonify({"error": "No text provided."}), 400

    # Get additional context from analysis if available
    job_skills = []
    matched_skills = []
    if source_token:
        analysis = _get_analysis(source_token)
        if analysis:
            job_skills = analysis.get("job_skills", [])
            matched_skills = analysis.get("matched_skills", [])
            if not job_title:
                job_title = analysis.get("job_skills", [{}])[0].get("name", "") if analysis.get("job_skills") else ""
            if not job_description:
                job_description = analysis.get("job_text", "")

    result = improve_summary(
        text,
        job_skills=job_skills,
        matched_skills=matched_skills,
        resume_data=resume_data,
        job_title=job_title,
        job_description=job_description,
    )
    return jsonify(result)


def _resume_data_to_text(resume_data):
    """Convert structured resume data back to plain text for ATS analysis."""
    lines = []
    personal = resume_data.get("personal", {})
    if personal.get("name"):
        lines.append(personal["name"])
    for field in ["email", "phone", "linkedin"]:
        if personal.get(field):
            lines.append(personal[field])
    lines.append("")

    if resume_data.get("summary"):
        lines.append("Summary")
        lines.append(resume_data["summary"])
        lines.append("")

    if resume_data.get("experience"):
        lines.append("Experience")
        for exp in resume_data["experience"]:
            if isinstance(exp, dict):
                lines.append(exp.get("title", "") + " " + exp.get("company", ""))
                if exp.get("description"):
                    lines.append(exp["description"])
                for b in exp.get("bullets", []):
                    lines.append("- " + b)
            else:
                lines.append("- " + str(exp))
        lines.append("")

    if resume_data.get("projects"):
        lines.append("Projects")
        for proj in resume_data["projects"]:
            if isinstance(proj, dict):
                lines.append(proj.get("name", ""))
                if proj.get("description"):
                    lines.append(proj["description"])
            else:
                lines.append("- " + str(proj))
        lines.append("")

    if resume_data.get("skills"):
        lines.append("Skills")
        for s in resume_data["skills"]:
            name = s["name"] if isinstance(s, dict) else str(s)
            lines.append(name)
        lines.append("")

    if resume_data.get("education"):
        lines.append("Education")
        for e in resume_data["education"]:
            lines.append(str(e))
        lines.append("")

    return "\n".join(lines)


@app.route("/api/resume-builder/download-pdf", methods=["POST"])
def api_resume_builder_download_pdf():
    """Generate and download a PDF resume."""
    try:
        data = request.get_json(silent=True) or {}
        resume_data = data.get("resume_data", {})
        template_name = data.get("template", "modern")
        job_title = data.get("job_title", "Resume")
    except Exception:
        return jsonify({"error": "Invalid request body."}), 400

    try:
        pdf_bytes = _generate_pdf(resume_data, template_name, job_title)
        name = resume_data.get("personal", {}).get("name", "Resume")
        safe_name = name.replace(" ", "_").replace("/", "_")
        filename = f"{safe_name}_{job_title.replace(' ', '_')}_Resume.pdf"
        from io import BytesIO
        return send_file(
            BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename,
        )
    except Exception as exc:
        app.logger.exception("PDF generation failed")
        return jsonify({"error": "PDF generation failed."}), 500


@app.route("/api/resume-builder/download-docx", methods=["POST"])
def api_resume_builder_download_docx():
    """Generate and download a DOCX resume."""
    try:
        data = request.get_json(silent=True) or {}
        resume_data = data.get("resume_data", {})
        template_name = data.get("template", "modern")
        job_title = data.get("job_title", "Resume")
    except Exception:
        return jsonify({"error": "Invalid request body."}), 400

    try:
        docx_bytes = _generate_docx(resume_data, template_name, job_title)
        name = resume_data.get("personal", {}).get("name", "Resume")
        safe_name = name.replace(" ", "_").replace("/", "_")
        filename = f"{safe_name}_{job_title.replace(' ', '_')}_Resume.docx"
        from io import BytesIO
        return send_file(
            BytesIO(docx_bytes),
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            as_attachment=True,
            download_name=filename,
        )
    except Exception as exc:
        app.logger.exception("DOCX generation failed")
        return jsonify({"error": "DOCX generation failed."}), 500


@app.route("/about")
def about_page():
    return render_template("about.html")


@app.route("/history")
def history_page():
    return render_template("history.html")


@app.errorhandler(404)
def not_found(_):
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(_):
    return render_template("500.html"), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=10000, debug=True)