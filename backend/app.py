import os

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory

from analyzer import ResumeError, analyze, extract_text

load_dotenv()
MAX_MB = int(os.getenv("MAX_UPLOAD_MB", "5"))
FRONTEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")

app = Flask(__name__, static_folder=FRONTEND, static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = MAX_MB * 1024 * 1024


@app.get("/")
def index():
    return send_from_directory(FRONTEND, "index.html")


@app.get("/api/health")
def health():
    return jsonify(status="ok", max_upload_mb=MAX_MB)


@app.post("/api/analyze")
def analyze_route():
    f = request.files.get("resume")
    if not f or not f.filename:
        return jsonify(error="No file received. Choose a PDF or DOCX resume."), 400
    ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else ""
    if ext not in ("pdf", "docx"):
        return jsonify(error="Unsupported file type. Upload a .pdf or .docx file."), 415
    data = f.read()
    if not data:
        return jsonify(error="The file is empty."), 400
    ok = data[:4] == b"%PDF" if ext == "pdf" else data[:2] == b"PK"  # content must match extension
    if not ok:
        return jsonify(error=f"This file is not a valid .{ext} document."), 400
    try:
        return jsonify(analyze(extract_text(data, ext), request.form.get("jd", "")))
    except ResumeError as e:
        return jsonify(error=str(e)), 422
    except Exception:
        app.logger.exception("analysis failed")
        return jsonify(error="The analysis failed unexpectedly. Check the backend terminal for details."), 500


@app.errorhandler(413)
def too_large(_):
    return jsonify(error=f"File is too large. Maximum size is {MAX_MB} MB."), 413


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=os.getenv("FLASK_DEBUG") == "1")
