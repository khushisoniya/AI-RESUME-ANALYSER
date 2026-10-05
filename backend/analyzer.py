"""Resume parsing + analysis.

What is real here:
  * Text extraction   : pypdf (PDF), python-docx (DOCX)
  * NLP (rule based)  : regex section detection, contact extraction, skill lexicon matching
  * ML (unsupervised) : TF-IDF vectorisation + cosine similarity (scikit-learn) between resume and job description
  * Score             : a transparent weighted formula (see analyze()). No trained classifier is used,
                        because the synopsis lists LogReg/RF/SVM/XGBoost as *optional* and no dataset is supplied.
"""
import io
import re

from docx import Document
from pypdf import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class ResumeError(Exception):
    """Problem with the upload or input; the message is safe to show to the user."""


SKILLS = ["python", "java", "javascript", "typescript", "c++", "c#", "go", "rust", "php", "ruby", "kotlin", "swift",
          "sql", "mysql", "postgresql", "mongodb", "sqlite", "html", "css", "react", "angular", "vue", "node.js",
          "express", "flask", "django", "fastapi", "spring", "bootstrap", "tailwind", "jquery", "rest api", "graphql",
          "machine learning", "deep learning", "nlp", "natural language processing", "computer vision",
          "data analysis", "data science", "pandas", "numpy", "scikit-learn", "tensorflow", "keras", "pytorch",
          "matplotlib", "seaborn", "tableau", "power bi", "excel", "statistics", "opencv", "nltk", "spacy",
          "xgboost", "tf-idf", "git", "github", "docker", "kubernetes", "aws", "azure", "gcp", "linux", "ci/cd",
          "jenkins", "agile", "scrum", "jira", "testing", "unit testing", "selenium", "data structures",
          "algorithms", "oop", "dbms", "operating systems", "computer networks", "cloud computing", "cybersecurity"]
SOFT = ["communication", "leadership", "teamwork", "problem solving", "time management", "adaptability",
        "creativity", "critical thinking", "collaboration", "presentation"]
VERBS = ["developed", "built", "designed", "implemented", "created", "led", "managed", "analysed", "analyzed",
         "improved", "optimized", "optimised", "deployed", "automated", "engineered", "integrated", "tested",
         "achieved", "reduced", "increased", "launched", "trained", "collaborated"]
HEADINGS = {
    "education": r"education|academics?|academic (?:qualifications?|background)|qualifications?",
    "skills": r"(?:technical |key |core )?skills|technologies|tech stack",
    "projects": r"(?:academic |personal |mini )?projects?",
    "experience": r"(?:work |professional )?experience|internships?|employment",
    "certifications": r"certifications?|courses|licen[cs]es",
    "achievements": r"achievements?|awards|honou?rs",
    "summary": r"(?:professional |career )?summary|objective|career objective|profile|about me",
}


def extract_text(data: bytes, ext: str) -> str:
    try:
        if ext == "pdf":
            text = "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(data)).pages)
        else:
            text = "\n".join(p.text for p in Document(io.BytesIO(data)).paragraphs)
    except Exception:
        raise ResumeError("This file could not be read. It may be corrupted or password-protected.")
    text = re.sub(r"[^\S\n]+", " ", text.replace("\x00", "")).strip()  # sanitise
    if len(text) < 80:
        raise ResumeError("No readable text found. Scanned or image-only resumes are not supported yet (OCR is future scope).")
    return text


def has_term(low: str, term: str) -> bool:
    return re.search(r"(?<![a-z0-9+#])" + re.escape(term) + r"(?![a-z0-9+#])", low) is not None


def find_skills(text: str, vocab=SKILLS):
    low = text.lower()
    return [s for s in vocab if has_term(low, s)]


def split_sections(text: str):
    sections, current = {}, None
    for line in text.split("\n"):
        s = line.strip().strip(":").strip()
        if not s:
            continue
        hit = None
        if len(s) <= 40:
            for name, pat in HEADINGS.items():
                if re.fullmatch(pat, s, re.I):
                    hit = name
                    break
        if hit:
            current = hit
            sections.setdefault(hit, [])
        elif current:
            sections[current].append(s)
    return sections


def extract_profile(text: str):
    email = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
    phone = None
    for m in re.finditer(r"\+?\d[\d\s\-()]{8,}\d", text):
        if 10 <= len(re.sub(r"\D", "", m.group())) <= 13:
            phone = m.group().strip()
            break
    links = re.findall(r"(?:https?://)?(?:www\.)?(?:linkedin\.com|github\.com)/[\w\-./]+", text, re.I)
    name = "Not detected"
    for line in text.split("\n")[:5]:
        w = line.strip().split()
        if 2 <= len(w) <= 4 and all(re.fullmatch(r"[A-Za-z.'-]+", x) for x in w):
            name = line.strip()
            break
    return {"name": name, "email": email.group() if email else None, "phone": phone, "links": links[:3]}


def similarity(text: str, jd: str):
    vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True)
    m = vec.fit_transform([text.lower(), jd.lower()])
    cos = float(cosine_similarity(m[0], m[1])[0, 0])
    terms = vec.get_feature_names_out()
    r, j = m[0].toarray()[0], m[1].toarray()[0]
    missing = [terms[i] for i in j.argsort()[::-1]
               if j[i] > 0 and r[i] == 0 and " " not in terms[i] and len(terms[i]) > 2][:10]
    return cos, missing


def analyze(text: str, jd: str = ""):
    jd = (jd or "").strip()
    if jd and len(jd.split()) < 15:
        raise ResumeError("The job description is too short. Paste at least a few lines, or leave it empty.")
    sections = split_sections(text)
    profile = extract_profile(text)
    skills = find_skills(text)
    soft = find_skills(text, SOFT)
    words = len(text.split())
    low = text.lower()
    verbs = sum(1 for v in VERBS if has_term(low, v))
    found = {k: bool(sections.get(k)) for k in ["summary", "education", "skills", "projects", "experience", "certifications"]}

    # --- scoring: transparent weighted formula ---
    w = {"education": 7, "skills": 7, "projects": 6, "experience": 6, "certifications": 4}
    structure = sum(v for k, v in w.items() if found[k])
    ats = (5 if profile["email"] else 0) + (4 if profile["phone"] else 0) + (3 if profile["links"] else 0) \
        + (4 if 250 <= words <= 1000 else 2 if 120 <= words < 250 or 1000 < words <= 1400 else 0) \
        + min(verbs, 5) * 4 // 5
    skill_pts = round(min(len(skills), 12) / 12 * 20)
    breakdown = [{"label": "Structure", "got": structure, "max": 30},
                 {"label": "ATS readiness", "got": ats, "max": 20},
                 {"label": "Skill coverage", "got": skill_pts, "max": 20}]
    match, missing_skills, missing_kw = None, [], []
    if jd:
        cos, missing_kw = similarity(text, jd)
        jd_skills = find_skills(jd)
        missing_skills = [s for s in jd_skills if s not in skills]
        overlap = (len(jd_skills) - len(missing_skills)) / len(jd_skills) if jd_skills else 0.0
        pts = round(30 * (0.4 * min(cos / 0.5, 1) + 0.6 * overlap))
        breakdown.append({"label": "Job match", "got": pts, "max": 30})
        match = {"cosine": round(cos, 3), "skill_overlap": round(overlap, 3), "jd_skills": len(jd_skills)}
        score = structure + ats + skill_pts + pts
    else:
        score = round((structure + ats + skill_pts) / 70 * 100)

    strengths, weaknesses, tips = [], [], []
    if len(skills) >= 8: strengths.append(f"{len(skills)} recognisable technical skills are listed.")
    if found["projects"]: strengths.append("A projects section is present, which shows applied work.")
    if verbs >= 4: strengths.append("Action verbs are used to describe work.")
    if profile["email"] and profile["phone"]: strengths.append("Email and phone are easy to find.")
    if match and match["skill_overlap"] >= 0.6: strengths.append("Most skills in the job description appear in your resume.")
    for k in ["education", "skills", "projects", "experience", "certifications", "summary"]:
        if not found[k]:
            weaknesses.append(f"No clear '{k}' section was detected.")
            tips.append(f"Add a section headed exactly '{k.capitalize()}' so ATS parsers can find it.")
    if not profile["email"]: weaknesses.append("No email address detected."); tips.append("Put your email in the first lines.")
    if not profile["phone"]: weaknesses.append("No phone number detected.")
    if not profile["links"]: tips.append("Add your GitHub or LinkedIn URL.")
    if words < 250: weaknesses.append(f"Only {words} words; the resume looks thin."); tips.append("Describe each project in 2 to 3 bullets: what you built and the result.")
    if words > 1000: weaknesses.append(f"{words} words is long for a fresher resume."); tips.append("Trim to one page where possible.")
    if verbs < 4: tips.append("Start bullets with action verbs such as built, designed, deployed, reduced.")
    if len(skills) < 6: weaknesses.append("Few technical skills were recognised.")
    if missing_skills: tips.append("If you genuinely have them, add: " + ", ".join(missing_skills[:6]) + ".")
    if jd and not missing_skills: strengths.append("No skills from the job description are missing.")

    return {
        "score": int(max(0, min(100, score))), "breakdown": breakdown, "jd_used": bool(jd), "match": match,
        "profile": profile, "found": found, "words": words,
        "sections": {k: sections.get(k, [])[:8] for k in ["education", "projects", "experience", "certifications"]},
        "skills": skills, "soft_skills": soft, "missing_skills": missing_skills, "missing_keywords": missing_kw,
        "strengths": strengths, "weaknesses": weaknesses, "suggestions": tips,
        "engine": {"parsing": "pypdf / python-docx + regex", "nlp": "rule-based section and skill detection",
                   "ml": "TF-IDF + cosine similarity (unsupervised; no trained classifier)",
                   "score": "weighted formula: structure 30, ATS 20, skills 20, job match 30"},
    }
