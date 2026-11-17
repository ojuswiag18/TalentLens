"""Matching logic: compare resume vs job description for skills and keywords.

This module extracts MEANINGFUL skills, technologies, tools, qualifications,
and professional competencies — not generic filler words.
"""

import re
from collections import Counter

from src.text_processor import (
    extract_keywords,
    normalize,
    remove_stopwords,
    tokenize,
)

# ---------------------------------------------------------------------------
# Filler words that should NEVER appear as "missing keywords"
# ---------------------------------------------------------------------------
_FILLER_WORDS = {
    # Generic verbs
    "working", "performing", "communicating", "building", "creating",
    "developing", "implementing", "managing", "leading", "supporting",
    "ensuring", "providing", "maintaining", "delivering", "driving",
    "establishing", "collaborating", "facilitating", "monitoring",
    "evaluating", "conducting", "coordinating", "supervising",
    "assisting", "participating", "contributing", "overseeing",
    "preparing", "reviewing", "identifying", "analyzing", "preparing",
    "presenting", "demonstrating", "demonstrated", "utilizing",
    # Generic adjectives
    "excellent", "strong", "solid", "good", "great", "effective",
    "successful", "proven", "innovative", "dynamic", "results",
    "results-oriented", "self-motivated", "detail-oriented",
    "highly", "motivated", "dedicated", "passionate", "enthusiastic",
    "versatile", "adaptable", "resourceful", "independent",
    # Filler nouns
    "knowledge", "proficiency", "familiarity", "understanding",
    "ability", "experience", "experience with", "experience in",
    "experience working", "proficient", "skill", "skills",
    "competence", "capability", "expertise", "aptitude",
    "understanding of", "knowledge of", "background in",
    # Common JD filler
    "required", "preferred", "requirements", "qualifications",
    "responsibilities", "responsibility", "candidate", "candidates",
    "position", "role", "job", "team", "company", "organization",
    "department", "industry", "sector", "environment", "opportunity",
    "including", "involves", "involving", "related", "relevant",
    "such as", "e.g", "i.e", "etc", "plus", "bonus", "ideally",
    "looking", "seeking", "ideally", "benefits", "offer",
    "ability to", "must be", "should be", "shall be",
    "years of", "year of", "minimum", "least",
    # Generic verbs/nouns
    "like", "well", "also", "help", "need", "use", "used", "using",
    "make", "made", "take", "keep", "set", "get", "put", "run",
    "come", "go", "see", "find", "give", "tell", "call", "try",
    "ask", "work", "seem", "feel", "let", "begin", "start",
    "show", "hear", "play", "move", "live", "believe", "bring",
    "happen", "write", "provide", "sit", "stand", "lose", "pay",
    "meet", "include", "continue", "learn", "change", "follow",
    "stop", "speak", "read", "allow", "add", "spend", "grow",
    "open", "walk", "win", "offer", "remember", "love", "consider",
    "appear", "buy", "wait", "serve", "die", "send", "expect",
    "build", "stay", "fall", "cut", "reach", "kill", "remain",
    "suggest", "raise", "pass", "sell", "require", "report",
    "decide", "pull", "develop",
}

# ---------------------------------------------------------------------------
# Multi-word skill phrases to detect directly from JD text
# ---------------------------------------------------------------------------
_PHRASE_SKILLS = {
    # Data & Analytics
    "machine learning": "Machine Learning",
    "deep learning": "Deep Learning",
    "data analysis": "Data Analysis",
    "data analytics": "Data Analytics",
    "data visualization": "Data Visualization",
    "data engineering": "Data Engineering",
    "data mining": "Data Mining",
    "data science": "Data Science",
    "data warehousing": "Data Warehousing",
    "data storytelling": "Data Storytelling",
    "data processing": "Data Processing",
    "data cleaning": "Data Cleaning",
    "data quality": "Data Quality",
    "data governance": "Data Governance",
    "data modeling": "Data Modeling",
    "data pipeline": "Data Pipeline",
    "big data": "Big Data",
    "predictive analytics": "Predictive Analytics",
    "predictive modeling": "Predictive Modeling",
    "prescriptive analytics": "Prescriptive Analytics",
    "descriptive analytics": "Descriptive Analytics",
    "diagnostic analytics": "Diagnostic Analytics",
    "business intelligence": "Business Intelligence",
    "business analysis": "Business Analysis",
    "business analytics": "Business Analytics",
    "business strategy": "Business Strategy",
    "business development": "Business Development",
    "business process": "Business Process",
    "business requirements": "Business Requirements",
    "exploratory data analysis": "Exploratory Data Analysis",
    "statistical analysis": "Statistical Analysis",
    "statistical modeling": "Statistical Modeling",
    "statistical testing": "Statistical Testing",
    "hypothesis testing": "Hypothesis Testing",
    "time series": "Time Series",
    "time series analysis": "Time Series Analysis",
    "a/b testing": "A/B Testing",
    "ab testing": "A/B Testing",
    "natural language processing": "Natural Language Processing",
    "computer vision": "Computer Vision",
    "neural network": "Neural Networks",
    "neural networks": "Neural Networks",
    "reinforcement learning": "Reinforcement Learning",
    "feature engineering": "Feature Engineering",
    "recommendation system": "Recommendation Systems",
    "image processing": "Image Processing",
    "speech recognition": "Speech Recognition",
    "sentiment analysis": "Sentiment Analysis",
    "text mining": "Text Mining",
    "web scraping": "Web Scraping",
    "etl": "ETL",
    "extract transform load": "ETL",
    "ci/cd": "CI/CD",
    "continuous integration": "CI/CD",
    "continuous deployment": "CI/CD",
    "continuous delivery": "CI/CD",
    # Software Development
    "object oriented": "Object-Oriented Programming",
    "object-oriented": "Object-Oriented Programming",
    "object oriented programming": "Object-Oriented Programming",
    "functional programming": "Functional Programming",
    "microservices": "Microservices",
    "distributed systems": "Distributed Systems",
    "system design": "System Design",
    "software architecture": "Software Architecture",
    "software engineering": "Software Engineering",
    "software development": "Software Development",
    "web development": "Web Development",
    "mobile development": "Mobile Development",
    "api development": "API Development",
    "api design": "API Design",
    "rest api": "REST APIs",
    "restful api": "REST APIs",
    "rest apis": "REST APIs",
    "restful apis": "REST APIs",
    "full stack": "Full Stack Development",
    "full-stack": "Full Stack Development",
    "frontend": "Frontend Development",
    "front-end": "Frontend Development",
    "backend": "Backend Development",
    "back-end": "Backend Development",
    "version control": "Version Control",
    "code review": "Code Review",
    "test driven": "Test-Driven Development",
    "test-driven": "Test-Driven Development",
    "test automation": "Test Automation",
    "automated testing": "Test Automation",
    "unit testing": "Unit Testing",
    "integration testing": "Integration Testing",
    "agile methodologies": "Agile",
    "agile methodology": "Agile",
    "scrum methodology": "Scrum",
    "devops practices": "DevOps",
    "site reliability": "SRE",
    "infrastructure as code": "Infrastructure as Code",
    "cloud computing": "Cloud Computing",
    "cloud native": "Cloud Native",
    "cloud infrastructure": "Cloud Infrastructure",
    "cloud services": "Cloud Services",
    "database design": "Database Design",
    "database management": "Database Management",
    "database administration": "Database Administration",
    "data modeling": "Data Modeling",
    "data architecture": "Data Architecture",
    "information security": "Information Security",
    "network security": "Network Security",
    "cyber security": "Cybersecurity",
    "cybersecurity": "Cybersecurity",
    "penetration testing": "Penetration Testing",
    "vulnerability assessment": "Vulnerability Assessment",
    "incident response": "Incident Response",
    "threat detection": "Threat Detection",
    "security audit": "Security Audit",
    "compliance": "Compliance",
    "risk management": "Risk Management",
    "risk assessment": "Risk Assessment",
    # Professional & Soft Skills
    "project management": "Project Management",
    "stakeholder management": "Stakeholder Management",
    "stakeholder communication": "Stakeholder Communication",
    "team management": "Team Management",
    "team leadership": "Team Leadership",
    "time management": "Time Management",
    "conflict resolution": "Conflict Resolution",
    "problem solving": "Problem Solving",
    "critical thinking": "Critical Thinking",
    "decision making": "Decision Making",
    "decision-making": "Decision Making",
    "analytical skills": "Analytical Skills",
    "analytical thinking": "Analytical Thinking",
    "strategic planning": "Strategic Planning",
    "strategic thinking": "Strategic Thinking",
    "change management": "Change Management",
    "quality assurance": "Quality Assurance",
    "quality control": "Quality Control",
    "process improvement": "Process Improvement",
    "continuous improvement": "Continuous Improvement",
    "lean methodology": "Lean Methodology",
    "six sigma": "Six Sigma",
    "supply chain": "Supply Chain Management",
    "supply chain management": "Supply Chain Management",
    "operations management": "Operations Management",
    "financial analysis": "Financial Analysis",
    "financial modeling": "Financial Modeling",
    "financial reporting": "Financial Reporting",
    "budget management": "Budget Management",
    "cost analysis": "Cost Analysis",
    "revenue analysis": "Revenue Analysis",
    "market research": "Market Research",
    "market analysis": "Market Analysis",
    "competitive analysis": "Competitive Analysis",
    "customer relationship": "CRM",
    "customer relationship management": "CRM",
    "digital marketing": "Digital Marketing",
    "content marketing": "Content Marketing",
    "social media marketing": "Social Media Marketing",
    "search engine optimization": "SEO",
    "search engine marketing": "SEM",
    "email marketing": "Email Marketing",
    "brand management": "Brand Management",
    "public relations": "Public Relations",
    "media relations": "Media Relations",
    "crisis communication": "Crisis Communication",
    "internal communication": "Internal Communication",
    "corporate communication": "Corporate Communication",
    "technical writing": "Technical Writing",
    "grant writing": "Grant Writing",
    "content creation": "Content Creation",
    "content strategy": "Content Strategy",
    "ux design": "UX Design",
    "ui design": "UI Design",
    "user experience": "UX Design",
    "user interface": "UI Design",
    "user research": "User Research",
    "wireframing": "Wireframing",
    "prototyping": "Prototyping",
    "usability testing": "Usability Testing",
    "interaction design": "Interaction Design",
    "visual design": "Visual Design",
    "graphic design": "Graphic Design",
    "motion design": "Motion Design",
    "instructional design": "Instructional Design",
    "curriculum development": "Curriculum Development",
    "lesson planning": "Lesson Planning",
    "classroom management": "Classroom Management",
    "student assessment": "Student Assessment",
    "student engagement": "Student Engagement",
    "differentiated instruction": "Differentiated Instruction",
    "educational technology": "Educational Technology",
    "parent communication": "Parent Communication",
    "academic advising": "Academic Advising",
    "student affairs": "Student Affairs",
    "student records": "Student Records",
    "event management": "Event Management",
    "scheduling": "Scheduling",
    "coordination": "Coordination",
    "administrative support": "Administrative Support",
    "office management": "Office Management",
    "records management": "Records Management",
    "patient care": "Patient Care",
    "patient assessment": "Patient Assessment",
    "clinical diagnosis": "Clinical Diagnosis",
    "clinical decision": "Clinical Decision Making",
    "clinical research": "Clinical Research",
    "medical documentation": "Medical Documentation",
    "medical ethics": "Medical Ethics",
    "treatment planning": "Treatment Planning",
    "pharmacology": "Pharmacology",
    "surgical": "Surgery",
    "anesthesia": "Anesthesiology",
    "radiology": "Radiology",
    "pathology": "Pathology",
    "oncology": "Oncology",
    "cardiology": "Cardiology",
    "neurology": "Neurology",
    "pediatrics": "Pediatrics",
    "obstetrics": "Obstetrics",
    "emergency medicine": "Emergency Medicine",
    "family medicine": "Family Medicine",
    "internal medicine": "Internal Medicine",
    "public health": "Public Health",
    "epidemiology": "Epidemiology",
    "biostatistics": "Biostatistics",
    "health informatics": "Health Informatics",
    "electronic health": "Electronic Health Records",
    "hipaa": "HIPAA Compliance",
    "recruitment": "Recruitment",
    "talent acquisition": "Talent Acquisition",
    "talent management": "Talent Management",
    "employee relations": "Employee Relations",
    "performance management": "Performance Management",
    "performance review": "Performance Review",
    "compensation and benefits": "Compensation & Benefits",
    "onboarding": "Onboarding",
    "offboarding": "Offboarding",
    "training and development": "Training & Development",
    "learning and development": "Learning & Development",
    "employee engagement": "Employee Engagement",
    "workforce planning": "Workforce Planning",
    "organizational development": "Organizational Development",
    "diversity and inclusion": "Diversity & Inclusion",
    "dei": "Diversity & Inclusion",
    "labor law": "Labor Law",
    "employment law": "Employment Law",
    "collective bargaining": "Collective Bargaining",
    "financial planning": "Financial Planning",
    "investment analysis": "Investment Analysis",
    "portfolio management": "Portfolio Management",
    "asset management": "Asset Management",
    "risk assessment": "Risk Assessment",
    "audit": "Auditing",
    "internal audit": "Internal Audit",
    "external audit": "External Audit",
    "tax compliance": "Tax Compliance",
    "tax preparation": "Tax Preparation",
    "accounts payable": "Accounts Payable",
    "accounts receivable": "Accounts Receivable",
    "general ledger": "General Ledger",
    "financial statements": "Financial Statements",
    "balance sheet": "Balance Sheet",
    "cash flow": "Cash Flow Analysis",
    "cost accounting": "Cost Accounting",
    "management accounting": "Management Accounting",
    "forensic accounting": "Forensic Accounting",
    "cloud architecture": "Cloud Architecture",
    "aws services": "AWS",
    "azure services": "Azure",
    "gcp services": "GCP",
    "kubernetes": "Kubernetes",
    "containerization": "Docker",
    "infrastructure": "Infrastructure",
    "networking": "Networking",
    "tcp/ip": "TCP/IP",
    "dns": "DNS",
    "load balancing": "Load Balancing",
    "firewall": "Firewall",
    "encryption": "Encryption",
    "ssl/tls": "SSL/TLS",
    "oauth": "OAuth",
    "authentication": "Authentication",
    "authorization": "Authorization",
    "single sign-on": "SSO",
    "identity management": "Identity Management",
    "monitoring": "Monitoring",
    "logging": "Logging",
    "alerting": "Alerting",
    "terraform": "Terraform",
    "ansible": "Ansible",
    "puppet": "Puppet",
    "chef": "Chef",
    "prometheus": "Prometheus",
    "grafana": "Grafana",
    "splunk": "Splunk",
    "datadog": "Datadog",
    "new relic": "New Relic",
}

# Map common skill aliases to canonical names
_SKILL_ALIASES = {
    # Abbreviations
    "ml": "Machine Learning",
    "dl": "Deep Learning",
    "nlp": "Natural Language Processing",
    "cv": "Computer Vision",
    "ai": "Artificial Intelligence",
    "js": "JavaScript",
    "ts": "TypeScript",
    "py": "Python",
    "rb": "Ruby",
    "k8s": "Kubernetes",
    "tf": "TensorFlow",
    "torch": "PyTorch",
    "sklearn": "Scikit-learn",
    "scikit learn": "Scikit-learn",
    "np": "NumPy",
    "pd": "Pandas",
    "ga4": "Google Analytics",
    "gcp": "Google Cloud Platform",
    "aws": "AWS",
    "ms excel": "Microsoft Excel",
    "powerbi": "Power BI",
    "ms office": "Microsoft Office",
    "g suite": "Google Workspace",
    "d3.js": "D3.js",
    "ci/cd": "CI/CD",
    "vs code": "VS Code",
    "vscode": "VS Code",
    "visual studio code": "VS Code",
    "sql server": "SQL Server",
    "elastic search": "Elasticsearch",
    "amazon s3": "Amazon S3",
    "amazon web services": "AWS",
    "google bigquery": "BigQuery",
    "amazon redshift": "Amazon Redshift",
    "microsoft azure": "Azure",
    "apache spark": "Apache Spark",
    "apache airflow": "Apache Airflow",
    "apache kafka": "Apache Kafka",
    "apache hive": "Apache Hive",
    "data build tool": "dbt",
    "huggingface": "Hugging Face",
    "lang chain": "LangChain",
    "open ai": "OpenAI",
    "prompt engineering": "Prompt Engineering",
    "six sigma": "Six Sigma",
    "ms powerpoint": "PowerPoint",
    "microsoft powerpoint": "PowerPoint",
    "ms word": "Microsoft Word",
    "microsoft word": "Microsoft Word",
    "adobe photoshop": "Adobe Photoshop",
    "adobe illustrator": "Adobe Illustrator",
    "adobe xd": "Adobe XD",
    "premiere pro": "Adobe Premiere Pro",
    "after effects": "Adobe After Effects",
    "r programming": "R",
    "c programming": "C",
    "c++ programming": "C++",
    "c lang": "C",
    "go lang": "Go",
    "golang": "Go",
    "ruby on rails": "Ruby on Rails",
    "rails": "Ruby on Rails",
    "spring boot": "Spring Boot",
    "google sheets": "Google Sheets",
    "google docs": "Google Docs",
    "google slides": "Google Slides",
    "facebook ads": "Facebook Ads",
    "meta ads": "Meta Ads",
    "google analytics": "Google Analytics",
    "google ads": "Google Ads",
    # Full tool/platform names (single-word keys)
    "python": "Python",
    "java": "Java",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "ruby": "Ruby",
    "php": "PHP",
    "swift": "Swift",
    "kotlin": "Kotlin",
    "scala": "Scala",
    "r": "R",
    "go": "Go",
    "rust": "Rust",
    "c": "C",
    "c++": "C++",
    "c#": "C#",
    "matlab": "MATLAB",
    "html": "HTML",
    "css": "CSS",
    "bash": "Bash",
    "sql": "SQL",
    "excel": "Microsoft Excel",
    "tableau": "Tableau",
    "power bi": "Power BI",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "jenkins": "Jenkins",
    "ansible": "Ansible",
    "terraform": "Terraform",
    "linux": "Linux",
    "git": "Git",
    "github": "GitHub",
    "gitlab": "GitLab",
    "jira": "Jira",
    "figma": "Figma",
    "postman": "Postman",
    "django": "Django",
    "flask": "Flask",
    "fastapi": "FastAPI",
    "spring": "Spring",
    "laravel": "Laravel",
    "react": "React",
    "angular": "Angular",
    "vue": "Vue",
    "node": "Node.js",
    "node.js": "Node.js",
    "next.js": "Next.js",
    "express": "Express",
    "bootstrap": "Bootstrap",
    "wordpress": "WordPress",
    "shopify": "Shopify",
    "salesforce": "Salesforce",
    "hubspot": "HubSpot",
    "mailchimp": "Mailchimp",
    "semrush": "SEMrush",
    "ahrefs": "Ahrefs",
    "hootsuite": "Hootsuite",
    "canva": "Canva",
    "notion": "Notion",
    "trello": "Trello",
    "asana": "Asana",
    "slack": "Slack",
    "zoom": "Zoom",
    "sharepoint": "SharePoint",
    "snowflake": "Snowflake",
    "databricks": "Databricks",
    "looker": "Looker",
    "qlik": "Qlik",
    "mongodb": "MongoDB",
    "mysql": "MySQL",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "redis": "Redis",
    "elasticsearch": "Elasticsearch",
    "cassandra": "Cassandra",
    "sqlite": "SQLite",
    "oracle": "Oracle",
    "pandas": "Pandas",
    "numpy": "NumPy",
    "scikit-learn": "Scikit-learn",
    "tensorflow": "TensorFlow",
    "pytorch": "PyTorch",
    "keras": "Keras",
    "hadoop": "Hadoop",
    "spark": "Apache Spark",
    "pyspark": "PySpark",
    "airflow": "Apache Airflow",
    "kafka": "Apache Kafka",
    "dbt": "dbt",
    "matplotlib": "Matplotlib",
    "seaborn": "Seaborn",
    "plotly": "Plotly",
    "bokeh": "Bokeh",
    "blender": "Blender",
    "autocad": "AutoCAD",
    "revit": "Revit",
    "solidworks": "SolidWorks",
    "chatgpt": "ChatGPT",
    "openai": "OpenAI",
    "agile": "Agile",
    "scrum": "Scrum",
    "kanban": "Kanban",
    "lean": "Lean",
    "itil": "ITIL",
    "xgboost": "XGBoost",
    "lightgbm": "LightGBM",
    "nltk": "NLTK",
    "spacy": "spaCy",
    "prometheus": "Prometheus",
    "grafana": "Grafana",
    "splunk": "Splunk",
    "datadog": "Datadog",
}

# Generic single words that should never be individual "skills"
_GENERIC_WORDS = {
    "analysis", "analytics", "management", "development", "engineering",
    "design", "planning", "strategy", "marketing", "operations",
    "research", "education", "training", "assessment", "evaluation",
    "implementation", "optimization", "automation", "integration",
    "administration", "architecture", "infrastructure", "framework",
    "methodology", "approach", "technique", "process", "system",
    "technology", "platform", "solution", "service", "application",
    "program", "project", "initiative", "program", "practice",
    "principle", "concept", "theory", "standard", "guideline",
    "procedure", "protocol", "policy", "regulation", "requirement",
}


def _skill_map(skills):
    """Build a lowercase name -> skill dict."""
    return {s["name"].lower(): s for s in skills}


def _normalize_skill_name(name):
    """Normalize a skill name for comparison."""
    return name.strip().lower()


def match_skills(resume_skills, job_skills):
    """Return matched, missing and extra skills between resume and job.

    Uses normalized name comparison with alias awareness.
    """
    resume_map = _skill_map(resume_skills)
    job_map = _skill_map(job_skills)

    matched = []
    missing = []
    for name, job_skill in job_map.items():
        if name in resume_map:
            hit = dict(job_skill)
            hit["level"] = job_skill.get("level")
            matched.append(hit)
        else:
            missing.append(dict(job_skill))

    extra = [dict(s) for name, s in resume_map.items() if name not in job_map]
    return matched, missing, extra


def _extract_meaningful_phrases(text):
    """Extract meaningful multi-word and single-word skills from text."""
    norm = text.lower()
    found = {}  # canonical_name -> count

    # 1. Match multi-word phrases first (longest first)
    sorted_phrases = sorted(_PHRASE_SKILLS.keys(), key=len, reverse=True)
    for phrase in sorted_phrases:
        canonical = _PHRASE_SKILLS[phrase]
        # Count occurrences using word boundaries
        pattern = r'\b' + re.escape(phrase) + r'\b'
        count = len(re.findall(pattern, norm))
        if count > 0:
            found[canonical] = found.get(canonical, 0) + count

    # 2. Match single-word aliases
    tokens = set(re.findall(r'[a-z0-9+#]+', norm))
    for token in tokens:
        if token in _SKILL_ALIASES:
            canonical = _SKILL_ALIASES[token]
            found[canonical] = found.get(canonical, 0) + 1
        elif token in _GENERIC_WORDS:
            continue  # skip generic words
        elif len(token) >= 3 and token not in _FILLER_WORDS:
            # Check if it looks like a tech term (has numbers, special chars,
            # or is capitalized-like)
            if re.search(r'[0-9+#]', token) or token in {
                "react", "vue", "angular", "django", "flask", "spring",
                "docker", "jenkins", "ansible", "terraform", "kubernetes",
                "graphql", "webpack", "babel", "eslint", "prettier",
                "mongodb", "redis", "elasticsearch", "cassandra",
                "hadoop", "spark", "kafka", "airflow", "dbt",
                "snowflake", "bigquery", "redshift", "looker",
                "tableau", "power", "figma", "sketch",
                "linux", "unix", "windows", "macos", "ios", "android",
                "swift", "kotlin", "rust", "scala", "go",
                "perl", "lua", "r", "julia", "matlab", "sas",
                "spss", "stata", "haskell", "erlang", "elixir",
                "clojure", "fsharp", "ocaml", "fortran", "cobol",
                "assembly", "verilog", "vhdl", "cuda", "opencl",
            }:
                # Check if already captured as part of a phrase
                already_captured = False
                for canonical in found:
                    if token in canonical.lower().split():
                        already_captured = True
                        break
                if not already_captured:
                    # Capitalize nicely
                    nice_name = token.upper() if len(token) <= 4 else token.title()
                    found[nice_name] = found.get(nice_name, 0) + 1

    return found


def _extract_soft_skills(text):
    """Extract meaningful soft skills from text."""
    norm = text.lower()
    found = {}
    soft_skill_phrases = {
        "communication skills": "Communication",
        "communication": "Communication",
        "leadership": "Leadership",
        "team management": "Team Management",
        "team leadership": "Team Leadership",
        "time management": "Time Management",
        "conflict resolution": "Conflict Resolution",
        "problem solving": "Problem Solving",
        "problem-solving": "Problem Solving",
        "critical thinking": "Critical Thinking",
        "decision making": "Decision Making",
        "decision-making": "Decision Making",
        "analytical skills": "Analytical Skills",
        "analytical thinking": "Analytical Thinking",
        "strategic thinking": "Strategic Thinking",
        "strategic planning": "Strategic Planning",
        "stakeholder management": "Stakeholder Management",
        "stakeholder communication": "Stakeholder Communication",
        "presentation skills": "Presentation",
        "presentations": "Presentation",
        "negotiation": "Negotiation",
        "negotiation skills": "Negotiation",
        "adaptability": "Adaptability",
        "flexibility": "Flexibility",
        "attention to detail": "Attention to Detail",
        "detail oriented": "Attention to Detail",
        "detail-oriented": "Attention to Detail",
        "organizational skills": "Organizational Skills",
        "time management": "Time Management",
        "multitasking": "Multitasking",
        "self motivated": "Self-Motivation",
        "self-motivated": "Self-Motivation",
        "teamwork": "Teamwork",
        "collaboration": "Collaboration",
        "mentoring": "Mentoring",
        "coaching": "Coaching",
        "empathy": "Empathy",
        "emotional intelligence": "Emotional Intelligence",
        "creativity": "Creativity",
        "innovation": "Innovation",
        "initiative": "Initiative",
        "accountability": "Accountability",
        "work ethic": "Work Ethic",
        "reliability": "Reliability",
        "patience": "Patience",
        "resilience": "Resilience",
        "persuasion": "Persuasion",
        "influence": "Influence",
        "networking": "Networking",
        "relationship building": "Relationship Building",
        "client relations": "Client Relations",
        "customer service": "Customer Service",
        "customer success": "Customer Success",
        "feedback": "Feedback",
        "active listening": "Active Listening",
        "open communication": "Open Communication",
        "cross-functional": "Cross-Functional Collaboration",
        "cross-functional collaboration": "Cross-Functional Collaboration",
    }

    for phrase, canonical in sorted(soft_skill_phrases.items(), key=lambda x: -len(x[0])):
        pattern = r'\b' + re.escape(phrase) + r'\b'
        if re.search(pattern, norm):
            if canonical not in found:
                found[canonical] = 1
    return found


def match_keywords(resume_text, job_text, top_n=40):
    """Extract meaningful skills and keywords from job description and
    compare against resume.

    Returns (matched, missing) where each item is a meaningful skill/keyword
    rather than generic filler words.
    """
    if not resume_text or not job_text:
        return [], []

    # Extract meaningful skills from both texts
    job_skills = _extract_meaningful_phrases(job_text)
    job_soft_skills = _extract_soft_skills(job_text)
    job_skills.update(job_soft_skills)

    resume_skills = _extract_meaningful_phrases(resume_text)
    resume_soft_skills = _extract_soft_skills(resume_text)
    resume_skills.update(resume_soft_skills)

    resume_set = set(k.lower() for k in resume_skills)

    matched = []
    missing = []

    # Sort by occurrence count in job description (most important first)
    sorted_skills = sorted(job_skills.items(), key=lambda x: -x[1])

    for skill_name, count in sorted_skills:
        if skill_name.lower() in resume_set:
            matched.append(skill_name)
        else:
            missing.append(skill_name)

    # Limit to top N
    matched = matched[:top_n]
    missing = missing[:top_n]

    return matched, missing


def classify_skill_priority(missing_skills, job_text):
    """Classify each missing skill into HIGH / MEDIUM / LOW priority based
    on context in the job description.

    Returns a list of dicts: {name, priority, reason}
    """
    norm = job_text.lower()
    results = []

    for skill in missing_skills:
        skill_name = skill["name"] if isinstance(skill, dict) else skill
        skill_lower = skill_name.lower()
        importance = skill.get("importance", "important") if isinstance(skill, dict) else "important"

        # Count mentions in job description
        mention_count = norm.count(skill_lower)

        # Check context for priority signals
        high_signals = 0
        medium_signals = 0

        # Check if in "required" context
        required_patterns = [
            r'required.*' + re.escape(skill_lower),
            r'must.*' + re.escape(skill_lower),
            r'mandatory.*' + re.escape(skill_lower),
            r'essential.*' + re.escape(skill_lower),
            r'core.*' + re.escape(skill_lower),
            r'strong.*' + re.escape(skill_lower),
            r'solid.*' + re.escape(skill_lower),
            r'proficiency.*' + re.escape(skill_lower),
            re.escape(skill_lower) + r'.*required',
            re.escape(skill_lower) + r'.*must',
            re.escape(skill_lower) + r'.*essential',
        ]
        for pattern in required_patterns:
            if re.search(pattern, norm):
                high_signals += 1

        # Check for preferred/optional context
        optional_patterns = [
            r'preferred.*' + re.escape(skill_lower),
            r'nice to have.*' + re.escape(skill_lower),
            r'bonus.*' + re.escape(skill_lower),
            r'optional.*' + re.escape(skill_lower),
            r'plus.*' + re.escape(skill_lower),
            re.escape(skill_lower) + r'.*preferred',
            re.escape(skill_lower) + r'.*optional',
        ]
        for pattern in optional_patterns:
            if re.search(pattern, norm):
                medium_signals -= 1

        # Determine priority
        if importance == "critical" or high_signals >= 2 or mention_count >= 3:
            priority = "high"
        elif importance == "optional" or medium_signals < 0:
            priority = "low"
        elif mention_count >= 2 or high_signals >= 1:
            priority = "high"
        else:
            priority = "medium"

        # Generate reason
        reasons = []
        if mention_count >= 3:
            reasons.append(f"mentioned {mention_count} times in the job description")
        elif mention_count >= 2:
            reasons.append("mentioned multiple times in the job description")
        if high_signals >= 2:
            reasons.append("explicitly required for this role")
        elif high_signals >= 1:
            reasons.append("appears in required qualifications")
        if importance == "critical":
            reasons.append("classified as a critical requirement")
        if importance == "optional":
            reasons.append("listed as a preferred qualification")
            if priority == "medium":
                priority = "low"
        if not reasons:
            reasons.append("relevant to this role based on job description analysis")

        results.append({
            "name": skill_name,
            "priority": priority,
            "reason": ". ".join(reasons[:2]) + ".",
        })

    # Sort: high first, then medium, then low
    priority_order = {"high": 0, "medium": 1, "low": 2}
    results.sort(key=lambda x: priority_order.get(x["priority"], 2))

    return results
