# Redline: AI Resume Analyser

B.Tech CSE mini-project (IPS Academy, Indore; RGPV). Upload a PDF/DOCX resume, optionally paste a job description, and get a score, detected skills, missing skills and edit suggestions.

## What is real, and what is not
| Part | Implementation |
|---|---|
| Text extraction | `pypdf`, `python-docx` |
| NLP | Rule-based: regex section headings, contact extraction, skill lexicon matching |
| ML | TF-IDF (unigrams + bigrams) and **cosine similarity** via scikit-learn, resume vs job description |
| Score | Weighted formula: Structure 30 + ATS 20 + Skills 20 + Job match 30 (without a JD: the first 70 scaled to 100) |
| Not included | Trained classifier (LogReg/RF/SVM/XGBoost), login, admin panel, MySQL, multi-resume ranking, OCR |

The synopsis lists the classifiers as optional and provides no labelled dataset, so none is claimed. The 85-95% accuracy figure in the synopsis can only be reported after training and testing on a real dataset.

## Stack
Flask (Python 3.10+), scikit-learn, pypdf, python-docx; plain HTML/CSS/JS frontend served by Flask (no Node.js, no build step, one command to run).

## Folder structure
```
ai-resume-analyser/
  backend/  app.py  analyzer.py  requirements.txt  .env.example
  frontend/ index.html  style.css  app.js
  sample/   sample_resume.pdf  sample_job_description.txt
  docs/     AI_Resume_Analyser_Setup_Guide.pdf
  README.md
```

## Run (Windows)
```
cd backend
py -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python app.py
```
Open http://localhost:5000. No model or dataset files are needed. Full beginner guide: `docs/AI_Resume_Analyser_Setup_Guide.pdf`.

## API
- `GET /api/health`
- `POST /api/analyze` multipart: `resume` (file), `jd` (text, optional). Returns JSON; errors return `{"error": "..."}` with 400/413/415/422/500.

## Test
Upload `sample/sample_resume.pdf` with the sample job description (use the "Use a sample" link). Expected: score about 89, `nlp` listed as the missing skill. Also try a `.txt` file, an empty file and a renamed file to see each error message.

## Common errors
- `ModuleNotFoundError`: the venv is not active; run `venv\Scripts\activate` then `pip install -r requirements.txt`.
- Port 5000 busy: set `PORT=5001` in `.env`.
- "No readable text found": the PDF is scanned images.

## Viva summary
1. Upload: browser validates type/size, sends `FormData` to `/api/analyze`.
2. Server checks extension, magic bytes (`%PDF` / `PK`) and size, then extracts text and cleans it.
3. Parsing: regex finds headings (Education, Skills...), email, phone, links, name; a lexicon finds skills.
4. TF-IDF turns resume and JD into vectors; cosine similarity measures how alike they are; JD terms with weight in the JD but zero in the resume become "missing keywords".
5. Score = weighted sum (see table); rules generate strengths, weaknesses, suggestions.
6. JSON goes back; JavaScript renders it (all text is escaped before insertion).

## Future scope
Trained classifier on a Kaggle resume dataset (swap into `analyzer.py`), NER with spaCy, OCR, login + MySQL, recruiter ranking of many resumes, grammar check.
