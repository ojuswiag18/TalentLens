# TalentLens

TalentLens is a high-end AI-powered web application that analyzes a candidate's resume
against a target job description. It extracts skills, calculates a resume–job
compatibility score, detects skill gaps, and recommends learning resources for every
missing skill.

## Features

- PDF / TXT resume upload with validation (file type, size, readability)
- Resume text extraction via PyMuPDF with cleaning and normalization
- Skill extraction from both resume and job description (200+ skills with aliases)
- Skill matching with matched / missing / extra classification
- Skill gap severity classification: critical, important, optional
- Overall compatibility score from skills, keywords, experience, education, projects
- Keyword match analysis (TF-IDF style frequency + text similarity via cosine)
- Skill level gap personalization (e.g. Basic Python → Advanced Python)
- Prioritized improvement suggestions across 7 categories
- Curated learning resource database (documentation, videos, articles, courses)
- Resource search + per-skill resource pages and modals
- Interactive analytics dashboard with Chart.js
- Light / dark theme with localStorage persistence
- Privacy-first: uploads processed in memory, never stored, deleted after analysis

## Tech Stack

Python, Flask, PyMuPDF, scikit-learn (TF-IDF, cosine similarity), Chart.js,
HTML/CSS/JavaScript (Space Grotesk + Inter).

## Getting Started

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # or set SECRET_KEY
python app.py
```

Open http://127.0.0.1:5000

## Running Tests

```bash
pytest -q
```

## API

| Method | Endpoint                  | Description                                  |
|--------|---------------------------|----------------------------------------------|
| POST   | `/api/analyze`            | Analyze resume + job description (JSON or multipart) |
| GET    | `/api/analysis?token=`    | Fetch stored analysis                        |
| GET    | `/api/dashboard?token=`   | Dashboard analytics data                     |
| GET    | `/api/resources/<skill>`  | Learning resources for a skill               |
| GET    | `/api/resources/search?q=`| Search learning resources                    |

## Project Structure

```
app.py                  Flask application + API routes
config.py               Configuration
data/skills.csv         Skill dataset (name, category, aliases)
data/resources.csv      Curated learning resources
src/                    Backend modules (parsing, NLP, matching, scoring, resources, analytics)
templates/              Jinja templates (base, index, analyze, results, dashboard, resources, about)
static/css/             themes.css (light/dark variables), main.css
static/js/              theme.js, main.js, dashboard.js
tests/                  Unit tests
```

## Privacy

Resumes are processed in memory; uploaded files are written to a temporary file and
deleted immediately after text extraction. Resume contents are never logged or stored
permanently.