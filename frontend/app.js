const $ = s => document.querySelector(s);
const esc = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const MAX = 5 * 1024 * 1024;
const SAMPLE_JD = "We are hiring a Python Developer intern. You will build REST API services with Flask, work with SQL and MySQL databases, and use Git and GitHub daily. Experience with machine learning, NLP, pandas, numpy and scikit-learn is a strong plus. Knowledge of data structures, algorithms and Docker is preferred. Good communication and teamwork are expected.";
let file = null, last = null;

const show = v => { ["upload","loading","results"].forEach(x => $("#"+x).hidden = x !== v); window.scrollTo(0,0); };
const setErr = m => { const e = $("#err"); e.textContent = m || ""; e.hidden = !m; };

function pick(f) {
  setErr("");
  const ext = f && f.name.split(".").pop().toLowerCase();
  if (!f) return;
  if (!["pdf","docx"].includes(ext)) return setErr("Unsupported file type. Upload a .pdf or .docx file.");
  if (f.size === 0) return setErr("The file is empty.");
  if (f.size > MAX) return setErr("File is too large. Maximum size is 5 MB.");
  file = f; $("#drop").classList.add("has");
  $("#dropTitle").textContent = f.name; $("#dropSub").textContent = (f.size/1024).toFixed(0) + " KB · click to replace";
  $("#go").disabled = false;
}
const drop = $("#drop");
$("#file").addEventListener("change", e => pick(e.target.files[0]));
drop.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); $("#file").click(); } });
["dragenter","dragover"].forEach(t => drop.addEventListener(t, e => { e.preventDefault(); drop.classList.add("over"); }));
["dragleave","drop"].forEach(t => drop.addEventListener(t, e => { e.preventDefault(); drop.classList.remove("over"); }));
drop.addEventListener("drop", e => pick(e.dataTransfer.files[0]));
$("#sample").onclick = () => { $("#jd").value = SAMPLE_JD; };

$("#go").onclick = async () => {
  setErr(""); show("loading");
  const fd = new FormData(); fd.append("resume", file); fd.append("jd", $("#jd").value);
  try {
    const res = await fetch("/api/analyze", { method: "POST", body: fd });
    let data; try { data = await res.json(); } catch { throw new Error("The server sent an unexpected response."); }
    if (!res.ok) throw new Error(data.error || "Analysis failed.");
    last = data; render(data); show("results");
  } catch (e) {
    show("upload");
    setErr(e instanceof TypeError ? "Cannot reach the server. Make sure the backend is running (python app.py)." : e.message);
  }
};

const notes = (a, c, empty) => a.length ? a.map(t => `<div class="note ${c}">${esc(t)}</div>`).join("") : `<p class="empty">${empty}</p>`;
const chips = (a, c = "") => a.map(t => `<span class="chip ${c}">${esc(t)}</span>`).join("");
const list = a => a.length ? `<ul class="sec">${a.map(x => `<li>${esc(x)}</li>`).join("")}</ul>` : `<p class="empty">Nothing detected.</p>`;

function render(d) {
  const [band, col] = d.score >= 75 ? ["Strong", "var(--green)"] : d.score >= 55 ? ["Workable", "var(--amber)"] : ["Needs work", "var(--red)"];
  const p = d.profile;
  $("#results").innerHTML = `
  <div class="rtop">
    <div><div class="num">${d.score}<sup>/100</sup></div><span class="band" style="background:${col}">${band}</span></div>
    <div class="who"><p class="kicker">Analysis</p><h2>${esc(p.name)}</h2>
      <p>${esc(p.email || "no email found")} · ${esc(p.phone || "no phone found")}</p>${p.links.length ? `<p>${p.links.map(esc).join(" · ")}</p>` : ""}
      <div class="bars">${d.breakdown.map(b => `<div class="bar"><span>${esc(b.label)}</span><div class="t"><div data-w="${b.got/b.max*100}"></div></div><span>${b.got}/${b.max}</span></div>`).join("")}</div>
      ${d.jd_used ? `<p style="margin-top:14px">Cosine similarity with job description: <b>${d.match.cosine}</b> · JD skills covered: <b>${Math.round(d.match.skill_overlap*100)}%</b></p>` : `<p class="empty" style="margin-top:14px">No job description given, so the score is out of the 70 resume-only points, scaled to 100.</p>`}
    </div></div>
  <div class="grid">
    <div class="blk"><h3>What works</h3>${notes(d.strengths, "good", "No clear strengths detected yet.")}</div>
    <div class="blk"><h3>What hurts</h3>${notes(d.weaknesses, "bad", "No major problems detected.")}</div>
    <div class="blk full"><h3>Edits to make</h3>${notes(d.suggestions, "tip", "No edits suggested.")}</div>
    <div class="blk"><h3>Skills detected (${d.skills.length})</h3><div class="chips">${d.skills.length ? chips(d.skills) : '<span class="empty">None recognised.</span>'}</div>
      ${d.soft_skills.length ? `<h3 style="margin-top:18px">Soft skills</h3><div class="chips">${chips(d.soft_skills, "soft")}</div>` : ""}</div>
    <div class="blk"><h3>Missing for this job</h3>${d.jd_used ? `<div class="chips">${d.missing_skills.length ? chips(d.missing_skills, "miss") : '<span class="empty">No listed skills missing.</span>'}</div>
      ${d.missing_keywords.length ? `<h3 style="margin-top:18px">Keywords absent from resume</h3><div class="chips">${chips(d.missing_keywords, "soft")}</div>` : ""}` : '<p class="empty">Add a job description to see gaps.</p>'}</div>
    <div class="blk"><h3>Section check</h3><div class="checks">${Object.entries(d.found).map(([k,v]) => `<span class="${v ? "" : "no"}">${esc(k)}</span>`).join("")}</div></div>
    <div class="blk"><h3>Education</h3>${list(d.sections.education)}</div>
    <div class="blk"><h3>Projects</h3>${list(d.sections.projects)}</div>
    <div class="blk"><h3>Experience</h3>${list(d.sections.experience)}</div>
    <div class="blk full"><h3>Certifications</h3>${list(d.sections.certifications)}</div>
    <div class="blk full method"><h3>How this was computed</h3>
      <b>Parsing:</b> ${esc(d.engine.parsing)}<br><b>NLP:</b> ${esc(d.engine.nlp)}<br><b>ML:</b> ${esc(d.engine.ml)}<br><b>Score:</b> ${esc(d.engine.score)} · ${d.words} words read</div>
  </div>
  <div class="actions"><button class="btn ghost" id="dl">Download JSON</button><button class="btn ghost" onclick="window.print()">Print / save as PDF</button><button class="btn ghost" id="again">Analyse another</button></div>`;
  requestAnimationFrame(() => document.querySelectorAll(".bar .t div").forEach(el => el.style.width = el.dataset.w + "%"));
  $("#dl").onclick = () => { const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([JSON.stringify(last, null, 2)], {type: "application/json"})); a.download = "resume-analysis.json"; a.click(); };
  $("#again").onclick = () => { file = null; $("#file").value = ""; $("#go").disabled = true; drop.classList.remove("has"); $("#dropTitle").textContent = "Drop your resume here"; $("#dropSub").textContent = "or click to browse · .pdf .docx"; show("upload"); };
}
