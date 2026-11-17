"""Dynamic interview question generator.

Combines the comprehensive question bank with role-agnostic dynamic generation.
Questions are always derived from the actual job description.
"""

import re
import random
from collections import Counter

from src.interview_bank import detect_domain, get_questions_for_domain


# ---------------------------------------------------------------------------
# Skill-based question templates (fallback for unknown domains)
# ---------------------------------------------------------------------------

_SKILL_QUESTION_MAP = {
    "sql": {
        "beginner": [
            ("What is the purpose of a primary key in a database table?", "Understanding of relational database fundamentals"),
            ("What does SQL stand for and what is it used for?", "Basic knowledge of database query language"),
            ("What is the difference between WHERE and HAVING clauses?", "Understanding of SQL filtering mechanisms"),
        ],
        "intermediate": [
            ("How would you optimize a slow-performing SQL query?", "Query optimization and indexing knowledge"),
            ("Explain the difference between INNER JOIN, LEFT JOIN, and FULL OUTER JOIN.", "Understanding of join types and relational data"),
            ("What is database normalization and when might you denormalize?", "Database design trade-off reasoning"),
        ],
        "advanced": [
            ("How would you design a database schema for a complex application?", "Advanced database design and modeling"),
            ("Explain transaction isolation levels and their impact on concurrent access.", "Concurrency control and ACID properties"),
        ],
    },
    "python": {
        "beginner": [
            ("What is the difference between a list and a tuple in Python?", "Understanding of basic data structures"),
            ("What are functions and why are they useful?", "Modular programming concepts"),
        ],
        "intermediate": [
            ("How would you handle exceptions and errors in Python?", "Error handling and robust code design"),
            ("Explain the difference between a class and an instance.", "OOP concepts"),
        ],
        "advanced": [
            ("How would you implement a generator for processing large files?", "Memory-efficient programming and iterators"),
            ("Explain Python's GIL and its impact on multithreaded programs.", "Concurrency and runtime understanding"),
        ],
    },
    "javascript": {
        "beginner": [
            ("What is the difference between let, const, and var?", "Understanding of scoping rules"),
        ],
        "intermediate": [
            ("How does the event loop work in JavaScript?", "Asynchronous programming understanding"),
            ("What are closures and when would you use them?", "Lexical scoping and functional programming"),
        ],
        "advanced": [
            ("How would you architect a large-scale single-page application?", "Application architecture and state management"),
        ],
    },
    "machine learning": {
        "beginner": [
            ("What is the difference between supervised and unsupervised learning?", "Fundamental ML concepts"),
            ("What is overfitting and how can you prevent it?", "Model generalization basics"),
        ],
        "intermediate": [
            ("How would you evaluate a classification model's performance?", "Model evaluation methodology"),
            ("Explain the bias-variance tradeoff.", "Model complexity understanding"),
        ],
        "advanced": [
            ("How would you deploy a machine learning model to production?", "MLOps and production engineering"),
        ],
    },
    "data visualization": {
        "beginner": [
            ("What makes a good data visualization?", "Basic data storytelling concepts"),
        ],
        "intermediate": [
            ("How would you design an interactive dashboard for stakeholders?", "Dashboard design and UX"),
        ],
        "advanced": [
            ("How would you present complex analytical findings to a non-technical audience?", "Communication and data storytelling"),
        ],
    },
    "communication": {
        "beginner": [
            ("How do you ensure clear communication in a team setting?", "Communication fundamentals"),
        ],
        "intermediate": [
            ("How would you present complex findings to a non-technical audience?", "Stakeholder communication"),
        ],
        "advanced": [
            ("How would you handle a disagreement with a stakeholder?", "Conflict resolution"),
        ],
    },
    "project management": {
        "beginner": [
            ("What are the key phases of a project lifecycle?", "Project management fundamentals"),
        ],
        "intermediate": [
            ("How would you prioritize tasks when working on multiple projects?", "Time management and prioritization"),
        ],
        "advanced": [
            ("How would you manage a project with competing deadlines?", "Advanced resource management"),
        ],
    },
    "agile": {
        "beginner": [
            ("What is the difference between Scrum and Kanban?", "Agile methodology basics"),
        ],
        "intermediate": [
            ("How would you handle scope creep in an Agile project?", "Project management skills"),
        ],
        "advanced": [
            ("How would you scale Agile across multiple teams?", "Organizational Agile transformation"),
        ],
    },
}

# Keyword-to-skill-category mapping
_CATEGORY_KEYWORDS = {
    "sql": ["sql", "mysql", "postgresql", "database"],
    "python": ["python"],
    "javascript": ["javascript", "js", "react", "angular", "vue", "node"],
    "machine learning": ["machine learning", "ml", "scikit", "tensorflow", "pytorch"],
    "data visualization": ["visualization", "chart", "dashboard", "tableau", "power bi"],
    "communication": ["communication", "presentation"],
    "project management": ["project management", "project manager"],
    "agile": ["agile", "scrum", "kanban"],
}


def _get_skill_category(skill_name):
    """Map a skill name to a question template category."""
    name_lower = skill_name.lower()
    if name_lower in _SKILL_QUESTION_MAP:
        return name_lower
    for cat in _SKILL_QUESTION_MAP:
        if cat in name_lower or name_lower in cat:
            return cat
    for cat, kws in _CATEGORY_KEYWORDS.items():
        if any(kw in name_lower for kw in kws):
            return cat
    return None


# ---------------------------------------------------------------------------
# Role-specific question templates (from JD keywords)
# ---------------------------------------------------------------------------

_ROLE_KEYWORD_PATTERNS = {
    "dashboard": [("How would you approach designing a dashboard for this role?", "intermediate", "Product thinking and user-centricity")],
    "report": [("How would you ensure the accuracy of reports you produce?", "beginner", "Quality assurance and attention to detail")],
    "analysis": [("Describe your process for turning raw data into actionable insights.", "intermediate", "End-to-end analytical workflow")],
    "stakeholder": [("How would you communicate complex findings to non-technical stakeholders?", "intermediate", "Communication and storytelling")],
    "lesson plan": [("What are the key elements of an effective lesson plan?", "beginner", "Instructional design fundamentals")],
    "student": [("How would you handle a student who is consistently disengaged?", "intermediate", "Classroom management and student engagement")],
    "curriculum": [("How would you approach developing a curriculum for a new subject?", "advanced", "Curriculum design and educational planning")],
    "classroom": [("How would you manage a classroom with diverse learning needs?", "intermediate", "Classroom management strategies")],
    "patient": [("What are the key steps when taking a patient's medical history?", "beginner", "Clinical skills and patient communication")],
    "clinical": [("How would you prioritize treatment when multiple patients need urgent attention?", "advanced", "Clinical decision-making under pressure")],
    "recruitment": [("How would you source candidates for a hard-to-fill position?", "intermediate", "Talent acquisition strategies")],
    "employee": [("How would you handle an employee conflict in the workplace?", "intermediate", "Conflict resolution and mediation")],
    "performance": [("How would you conduct an effective performance review?", "intermediate", "Performance management")],
    "budget": [("How would you develop an annual budget for a department?", "intermediate", "Budgeting and financial planning")],
    "campaign": [("How would you measure the success of a marketing campaign?", "intermediate", "Marketing analytics")],
    "team": [("How would you handle a situation where a team member is not contributing?", "intermediate", "Team management and leadership")],
    "deadline": [("How do you prioritize tasks when facing multiple deadlines?", "beginner", "Time management")],
    "problem": [("Describe your approach to solving complex problems.", "beginner", "Problem-solving methodology")],
    "decision": [("Describe your approach to making important decisions.", "intermediate", "Decision-making framework")],
    "ethics": [("How would you handle an ethical dilemma in your role?", "advanced", "Professional ethics and judgment")],
    "quality": [("How do you ensure quality in your work?", "beginner", "Quality assurance mindset")],
    "learn": [("How do you stay current with developments in your field?", "beginner", "Continuous learning")],
    "training": [("How would you approach training team members on a new tool?", "intermediate", "Training and knowledge transfer")],
    "customer": [("How would you handle a dissatisfied customer?", "intermediate", "Customer service and problem resolution")],
}


# ---------------------------------------------------------------------------
# Scenario templates (domain-based fallback)
# ---------------------------------------------------------------------------

_SCENARIO_TEMPLATES = {
    "Data Analyst": [
        ("You notice a significant discrepancy in your analysis results. Walk me through your debugging process.", "advanced", "Debugging methodology and systematic thinking"),
        ("You are asked to deliver a report with a very tight deadline. How do you approach it?", "intermediate", "Prioritization and delivery under pressure"),
        ("Your analysis contradicts what the stakeholder expected. How do you handle this?", "advanced", "Data-driven decision-making and communication"),
        ("You are given a dataset with many missing values. What is your approach?", "intermediate", "Data quality and imputation strategies"),
        ("How would you validate the results of an A/B test?", "advanced", "Statistical rigor and experimental design"),
        ("A stakeholder asks for a metric you believe is misleading. What do you do?", "advanced", "Ethics and professional judgment"),
    ],
    "Teacher": [
        ("A significant number of students are failing to meet learning objectives. How would you respond?", "advanced", "Reflective practice and instructional adjustment"),
        ("How would you handle a parent who disagrees with your assessment of their child?", "intermediate", "Parent communication and diplomacy"),
        ("You have a student with a learning disability in your classroom. How do you adapt your teaching?", "intermediate", "Inclusive education and differentiation"),
        ("How would you integrate technology into your lessons effectively?", "intermediate", "Educational technology integration"),
        ("A student accuses you of being unfair. How do you handle the situation?", "intermediate", "Conflict resolution and fairness"),
    ],
    "Doctor": [
        ("How would you handle a situation where you made a medical error?", "advanced", "Patient safety and accountability"),
        ("A patient refuses recommended treatment. How do you proceed?", "intermediate", "Patient autonomy and shared decision-making"),
        ("You disagree with a colleague's treatment plan for a patient. What do you do?", "advanced", "Interprofessional collaboration and advocacy"),
        ("How would you manage your workload during a particularly busy shift?", "intermediate", "Time management and prioritization in clinical settings"),
    ],
    "HR Executive": [
        ("An employee reports harassment. Walk me through the process you would follow.", "intermediate", "Investigation and compliance procedures"),
        ("How would you handle a situation where two team members have a serious conflict?", "intermediate", "Mediation and conflict resolution"),
        ("You need to reduce headcount. How would you approach this sensitively?", "advanced", "Change management and empathy"),
        ("How would you build a more inclusive workplace culture?", "advanced", "DEI strategy and culture change"),
    ],
    "Software Developer": [
        ("How would you handle a production outage at 2 AM?", "intermediate", "Incident response and on-call practices"),
        ("You discover a critical bug right before a release. What do you do?", "intermediate", "Risk assessment and decision-making"),
        ("How would you approach refactoring a legacy codebase?", "advanced", "Technical debt and code quality"),
        ("How would you handle a technical disagreement with a senior engineer?", "intermediate", "Professional communication and technical debate"),
    ],
    "general": [
        ("Describe a time you had to learn a new skill or tool quickly.", "intermediate", "Learning agility and adaptability"),
        ("How would you handle a situation where you disagree with your manager's decision?", "intermediate", "Professional communication and conflict resolution"),
        ("Tell me about a time you had to work with incomplete information.", "intermediate", "Problem-solving under constraints"),
        ("How would you prioritize your tasks on a busy day?", "beginner", "Time management and prioritization"),
        ("Describe a time you made a mistake at work. How did you handle it?", "intermediate", "Accountability and growth mindset"),
    ],
}


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

def _keyword_in_text(keywords, text):
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in keywords)


def _generate_skill_questions(skill_names, matched_names):
    """Generate technical questions from skills."""
    questions = []
    seen = set()
    for skill_name in skill_names:
        cat = _get_skill_category(skill_name)
        if not cat or cat not in _SKILL_QUESTION_MAP:
            continue
        templates = _SKILL_QUESTION_MAP[cat]
        is_missing = skill_name.lower() not in {n.lower() for n in matched_names}
        for difficulty in ["beginner", "intermediate", "advanced"]:
            for q_text, q_eval in templates.get(difficulty, []):
                if q_text not in seen:
                    seen.add(q_text)
                    questions.append({
                        "question": q_text,
                        "answer": "",
                        "evaluation": q_eval,
                        "skill": skill_name,
                        "category": "Technical",
                        "difficulty": difficulty,
                    })
    return questions


def _generate_role_questions(job_text, skill_names):
    """Generate role-specific questions from JD context."""
    text_lower = job_text.lower()
    questions = []
    seen = set()
    for pattern, templates in _ROLE_KEYWORD_PATTERNS.items():
        if pattern in text_lower:
            for q_text, difficulty, q_eval in templates:
                if q_text not in seen:
                    seen.add(q_text)
                    questions.append({
                        "question": q_text,
                        "answer": "",
                        "evaluation": q_eval,
                        "skill": "",
                        "category": "Role-Specific",
                        "difficulty": difficulty,
                    })
    return questions


def _generate_scenario_questions(domain, job_text):
    """Generate scenario questions based on domain."""
    questions = []
    seen = set()
    scenarios = _SCENARIO_TEMPLATES.get(domain, []) + _SCENARIO_TEMPLATES.get("general", [])
    for q_text, difficulty, q_eval in scenarios:
        if q_text not in seen:
            seen.add(q_text)
            questions.append({
                "question": q_text,
                "answer": "",
                "evaluation": q_eval,
                "skill": "",
                "category": "Scenario-Based",
                "difficulty": difficulty,
            })
    return questions


def generate_interview_questions(job_text, job_skills, matched_skills=None, missing_skills=None):
    """Generate interview questions using the question bank + dynamic fallback.

    Priority:
    1. Use the comprehensive question bank if the domain is recognized
    2. Fall back to skill-based + role-based dynamic generation
    """
    skill_names = [s["name"] for s in job_skills] if job_skills else []
    matched_names = [s["name"] for s in matched_skills] if matched_skills else []
    missing_names = [s["name"] for s in missing_skills] if missing_skills else []

    # 1. Try to match a domain from the question bank
    domain = detect_domain(job_text)

    if domain and domain in __import__("src.interview_bank", fromlist=["QUESTION_BANK"]).QUESTION_BANK:
        # Use the comprehensive question bank
        bank_questions = get_questions_for_domain(domain)
        # Shuffle for variety
        shuffled = list(bank_questions)
        random.shuffle(shuffled)

        technical = [q for q in shuffled if q["type"] == "Technical"][:10]
        role_specific = [q for q in shuffled if q["type"] == "Role-Specific"][:10]
        scenario = [q for q in shuffled if q["type"] == "Scenario-Based"][:10]

        # Add evaluation format
        for q in technical + role_specific + scenario:
            if "evaluation" in q and isinstance(q["evaluation"], list):
                q["evaluation"] = " • ".join(q["evaluation"])

        all_questions = technical + role_specific + scenario
    else:
        # Fallback: dynamic generation for unknown roles
        technical = _generate_skill_questions(skill_names, matched_names)
        role_specific = _generate_role_questions(job_text, skill_names)
        scenario = _generate_scenario_questions("general", job_text)

        technical = technical[:10]
        role_specific = role_specific[:10]
        scenario = scenario[:10]

        all_questions = technical + role_specific + scenario

    return {
        "technical": technical,
        "role_specific": role_specific,
        "scenario": scenario,
        "all": all_questions,
        "domain": domain,
    }
