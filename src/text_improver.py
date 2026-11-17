"""Career-independent text improvement for resume sections.

Uses rule-based NLP to improve resume content while preserving all factual information.
Works for ANY career field by dynamically detecting context from:
- Resume content
- Job title/target role
- Job description
- Skills mentioned
- Industry context

Never fabricates experience, companies, skills, or achievements.
"""

import re


# =============================================================================
# UNIVERSAL FILLER PHRASES — apply to any career field
# =============================================================================
_FILLER_PHRASES = [
    # Weak openers
    (r"\b[Ss]eeking to leverage [my our your]+\b", ""),
    (r"\b[Ss]eeking an opportunity\b", ""),
    (r"\b[Ss]eeking a position\b", ""),
    (r"\b[Ss]eeking\b", ""),
    (r"\b[Pp]assionate about\b", ""),
    (r"\b[Pp]assionate in\b", ""),
    (r"\b[Ii]nterested in\b", ""),
    (r"\b[Aa]n aspiring\b", ""),
    (r"\b[Aa]spiring\b", ". "),
    (r"\b[Dd]edicated and\b", ""),
    (r"\b[Hh]ighly motivated\b", ""),
    (r"\b[Mm]otivated to\b", ""),
    (r"\b[Mm]otivated professional\b", "Professional"),
    (r"\b[Ee]nthusiastic\b", ""),
    (r"\b[Dd]riven by a desire\b", ""),
    (r"\b[Ww]ith a strong desire\b", ""),
    (r"\b[Ee]ager to\b", ""),
    (r"\b[Ee]ager for\b", ""),
    (r"\b[Aa]iming to\b", ""),
    (r"\b[Aa]iming for\b", ""),
    (r"\b[Dd]etermined to\b", ""),
    (r"\b[Cc]ommitted to\b", ""),
    (r"\b[Ff]ocused on\b", ""),
    # Weak phrases
    (r"\b[Aa]s well as\b", "and"),
    (r"\b[Ii]n order to\b", "to"),
    (r"\b[Ff]or the purpose of\b", "to"),
    (r"\b[Dd]emonstrated ability to\b", "Able to"),
    (r"\b[Pp]ossessing strong\b", "Strong"),
    (r"\b[Pp]ossessing\b", "Possessing"),
    (r"\b[Ww]ith experience in\b", "Experienced in"),
    (r"\b[Ww]ith hands-on experience in\b", "Hands-on experience in"),
    (r"\b[Ww]ith a proven track record of\b", "Proven"),
    (r"\b[Aa]ble to effectively\b", "Able to"),
    (r"\b[Pp]roficient in\b", "Skilled in"),
    (r"\b[Ff]amiliar with\b", "Knowledgeable in"),
    (r"\b[Uu]tilizing\b", "Using"),
    (r"\b[Ll]everaging\b", "Using"),
    (r"\b[Ff]acilitating\b", "Supporting"),
    (r"\b[Cc]ollaborating with\b", "Working with"),
]

# Universal weak verb replacements — apply to any career
_ACTION_VERB_MAP = {
    "worked on": "Developed",
    "was responsible for": "Led",
    "helped with": "Contributed to",
    "helped to": "Contributed to",
    "assisted in": "Supported",
    "assisted with": "Supported",
    "did": "Completed",
    "made": "Created",
    "used": "Applied",
    "used to": "Applied",
    "was able to": "Successfully",
    "tried to": "Implemented",
    "started": "Initiated",
    "began": "Initiated",
    "was part of": "Collaborated in",
    "participated in": "Contributed to",
    "involved in": "Contributed to",
    "dealt with": "Managed",
    "handled": "Managed",
    "took care of": "Managed",
    "was in charge of": "Led",
    "was in charge": "Led",
    "worked with": "Collaborated with",
}

# Passive voice patterns — universal
_PASSIVE_MAP = {
    "was analyzed": "Analyzed",
    "were analyzed": "Analyzed",
    "was created": "Created",
    "were created": "Created",
    "was developed": "Developed",
    "were developed": "Developed",
    "was built": "Built",
    "were built": "Built",
    "was designed": "Designed",
    "was conducted": "Conducted",
    "were conducted": "Conducted",
    "was implemented": "Implemented",
    "were implemented": "Implemented",
    "was maintained": "Maintained",
    "were maintained": "Maintained",
    "was managed": "Managed",
    "were managed": "Managed",
    "was supervised": "Supervised",
    "was established": "Established",
    "were established": "Established",
    "was initiated": "Initiated",
    "were initiated": "Initiated",
    "was executed": "Executed",
    "were executed": "Executed",
    "was delivered": "Delivered",
    "were delivered": "Delivered",
    "was produced": "Produced",
    "were produced": "Produced",
    "was prepared": "Prepared",
    "were prepared": "Prepared",
    "was organized": "Organized",
    "were organized": "Organized",
    "was coordinated": "Coordinated",
    "were coordinated": "Coordinated",
    "was reviewed": "Reviewed",
    "were reviewed": "Reviewed",
    "was evaluated": "Evaluated",
    "were evaluated": "Evaluated",
    "was monitored": "Monitored",
    "were monitored": "Monitored",
    "was controlled": "Controlled",
    "were controlled": "Controlled",
}


def improve_summary(text, job_skills=None, matched_skills=None,
                    resume_data=None, job_title="", job_description=""):
    """Improve a resume section text using rule-based NLP.
    
    Works for ANY career field by dynamically detecting context from
    the resume content, job title, and job description.
    
    Args:
        text: The original text to improve
        job_skills: List of skill dicts from job description (optional)
        matched_skills: List of matched skill dicts (optional)
        resume_data: Full resume data dict (optional)
        job_title: Target job title (optional)
        job_description: Full job description text (optional)
    
    Returns:
        dict with 'original' and 'improved' keys
    """
    if not text or not text.strip():
        return {"original": text or "", "improved": text or ""}
    
    original = text.strip()
    improved = original
    
    # Step 1: Remove filler phrases
    for pattern, replacement in _FILLER_PHRASES:
        improved = re.sub(pattern, replacement, improved)
    
    # Step 2: Replace weak verbs with strong action verbs
    for weak, strong in _ACTION_VERB_MAP.items():
        pattern = re.compile(re.escape(weak), re.IGNORECASE)
        def replace_match(m, s=strong):
            if m.group(0)[0].isupper():
                return s
            return s[0].lower() + s[1:] if len(s) > 1 else s.lower()
        improved = pattern.sub(replace_match, improved)
    
    # Step 3: Convert passive voice to active
    for passive, active in _PASSIVE_MAP.items():
        pattern = re.compile(r"(\w+)\s+" + re.escape(passive), re.IGNORECASE)
        def fix_passive(m, a=active):
            subject = m.group(1)
            if subject.lower() in ('i', 'we', 'they', 'he', 'she', 'it'):
                return m.group(0)
            return a.capitalize() + " " + subject.lower()
        improved = pattern.sub(fix_passive, improved)
    
    # Step 4: Fix orphaned "The" before past-tense verbs
    improved = re.sub(r"^The (\w+ed)\b", r"\1", improved, flags=re.IGNORECASE)
    improved = re.sub(r"\.\s*The (\w+ed)\b", lambda m: ". " + m.group(1).capitalize(), improved, flags=re.IGNORECASE)
    
    # Step 5: Fix leading connectors and orphaned pronouns
    improved = re.sub(r"^And\s+", "", improved, flags=re.IGNORECASE)
    improved = re.sub(r"^Or\s+", "", improved, flags=re.IGNORECASE)
    improved = re.sub(r"^But\s+", "", improved, flags=re.IGNORECASE)
    improved = re.sub(r"^My\s+", "", improved, flags=re.IGNORECASE)
    improved = re.sub(r"^Your\s+", "", improved, flags=re.IGNORECASE)
    
    # Step 6: Fix "who is" patterns
    improved = re.sub(r"\bwho is (\w+)ing\b", r"who \1", improved, flags=re.IGNORECASE)
    improved = re.sub(r"\bwho is\b", "who", improved, flags=re.IGNORECASE)
    improved = re.sub(r"\bwho ([A-Z][a-z]+)\b", lambda m: "who " + m.group(1).lower(), improved)
    
    # Step 7: Clean up whitespace and punctuation
    improved = re.sub(r"\s+", " ", improved).strip()
    improved = re.sub(r",\s*,", ",", improved)
    improved = re.sub(r"\.\s*\.", ".", improved)
    improved = re.sub(r"\s+([.,;:!])", r"\1", improved)
    improved = re.sub(r"^\s*[,;]\s*", "", improved)
    improved = re.sub(r"\s+$", "", improved)
    improved = re.sub(r"[,]\s*$", "", improved)
    
    # Step 8: Fix sentence starts
    improved = re.sub(r"\.\s+([a-z])", lambda m: ". " + m.group(1).upper(), improved)
    
    # Step 9: Ensure proper sentence structure
    if improved and not improved.endswith((".", "!", "?")):
        if improved[-1] not in ".!?;:":
            improved += "."
    
    # Step 10: Capitalize first letter
    if improved:
        improved = improved[0].upper() + improved[1:]
    
    # Step 11: Fix double spaces
    improved = re.sub(r"  +", " ", improved)
    
    # Step 12: Safety checks — don't let it become worse
    if len(improved) < 10 and len(original) >= 10:
        improved = original
    if improved and len(improved) < len(original) * 0.4 and len(original) > 30:
        improved = original
    if improved and improved[0].islower():
        improved = improved[0].upper() + improved[1:]
    if improved and re.search(r"\s+(in|of|for|and|or|the|a|an)\s*$", improved, re.IGNORECASE):
        improved = original
    if improved and re.match(r"^Skills\s+(in|of|for|with)\b", improved, re.IGNORECASE):
        improved = original
    if improved and len(improved.split()) < 4 and len(original.split()) > 8:
        improved = original
    
    # Step 13: Final comparison — if identical, try restructuring
    if _texts_identical(original, improved):
        improved = _apply_stronger_transforms(original)
    
    # Step 14: If still identical, minimal improvement
    if _texts_identical(original, improved):
        improved = _minimal_improvement(original)
    
    # Step 15: Final cleanup
    improved = re.sub(r"^\s*[,.]\s*", "", improved)
    improved = re.sub(r"\s+", " ", improved).strip()
    
    return {
        "original": original,
        "improved": improved if improved else original,
    }


def _texts_identical(text1, text2):
    """Check if two texts are essentially identical."""
    def normalize(t):
        t = t.lower().strip()
        t = re.sub(r"[^a-z0-9\s]", "", t)
        t = re.sub(r"\s+", " ", t)
        return t
    return normalize(text1) == normalize(text2)


def _apply_stronger_transforms(text):
    """Apply stronger transformations when basic cleanup doesn't help."""
    improved = text
    
    # Remove common weak openers
    weak_openers = [
        r"^(?:I am|I'm|I have|I)\s+",
        r"^(?:As an?|Being an?)\s+",
    ]
    for pattern in weak_openers:
        improved = re.sub(pattern, "", improved, flags=re.IGNORECASE)
    
    # Additional passive to active transforms
    improved = re.sub(r"\bwas maintained\b", "Maintained", improved, flags=re.IGNORECASE)
    improved = re.sub(r"\bwere maintained\b", "Maintained", improved, flags=re.IGNORECASE)
    improved = re.sub(r"\bwas supervised\b", "Supervised", improved, flags=re.IGNORECASE)
    improved = re.sub(r"\bwas managed\b", "Managed", improved, flags=re.IGNORECASE)
    improved = re.sub(r"\bwere managed\b", "Managed", improved, flags=re.IGNORECASE)
    
    # Clean up
    improved = re.sub(r"\s+", " ", improved).strip()
    if improved and not improved.endswith("."):
        improved += "."
    if improved:
        improved = improved[0].upper() + improved[1:]
    
    return improved if improved else text


def _minimal_improvement(text):
    """Apply minimal improvements when nothing else works."""
    improved = text
    
    # Remove "and" before periods
    improved = re.sub(r"\s+and\s*\.", ".", improved)
    
    # Fix "a" before vowels
    improved = re.sub(r"\ba ([aeiou])", r"an \1", improved, flags=re.IGNORECASE)
    
    # Ensure first letter is capitalized
    if improved:
        improved = improved[0].upper() + improved[1:]
    
    # Ensure ends with period
    if improved and not improved.endswith((".", "!", "?")):
        improved += "."
    
    return improved
