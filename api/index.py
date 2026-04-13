import os
import io
import uuid
import base64
import tempfile
import zipfile

from flask import Flask, request, send_file, render_template_string, jsonify
import fitz  # PyMuPDF
from PIL import Image
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB

converted_sessions = {}

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>PDF to Image</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet" />
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    :root {
      --bg:      #f4f1ec;
      --white:   #ffffff;
      --ink:     #1a1814;
      --ink2:    #3d3a33;
      --muted:   #8c8880;
      --border:  #e2ddd6;
      --border2: #ccc8c0;
      --accent:  #d4501a;
      --acc-lt:  #fdf1ec;
      --green:   #1a8c4e;
      --grn-lt:  #ebfaf2;
      --shadow:  0 2px 20px rgba(0,0,0,0.06), 0 1px 4px rgba(0,0,0,0.04);
      --r:       16px;
      --sans:    'Plus Jakarta Sans', sans-serif;
      --mono:    'DM Mono', monospace;
    }

    html, body { height: 100%; }

    body {
      font-family: var(--sans);
      background: var(--bg);
      color: var(--ink);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 48px 16px 56px;
      -webkit-font-smoothing: antialiased;
    }

    .page {
      width: 100%; max-width: 640px;
      display: flex; flex-direction: column; gap: 16px;
    }

    /* ── Header ── */
    .hdr { margin-bottom: 8px; }
    .hdr-eyebrow {
      font-size: 0.68rem; font-weight: 700;
      letter-spacing: 2px; text-transform: uppercase;
      color: var(--accent); margin-bottom: 8px; display: block;
    }
    .hdr-title {
      font-size: clamp(1.7rem, 4vw, 2.2rem);
      font-weight: 800; letter-spacing: -0.5px;
      color: var(--ink); line-height: 1.15; margin-bottom: 8px;
    }
    .hdr-sub { font-size: 0.88rem; color: var(--muted); line-height: 1.6; }

    /* ── Card ── */
    .card {
      background: var(--white);
      border: 1px solid var(--border);
      border-radius: var(--r);
      box-shadow: var(--shadow);
    }

    /* ── Upload zone ── */
    .upload-card { padding: 28px; }

    .drop-zone {
      border: 2px dashed var(--border2);
      border-radius: 12px;
      padding: 48px 24px;
      text-align: center;
      cursor: pointer;
      transition: border-color 0.18s, background 0.18s;
      position: relative;
      margin-bottom: 20px;
    }
    .drop-zone:hover, .drop-zone.drag-over {
      border-color: var(--accent);
      background: var(--acc-lt);
    }
    .drop-zone input[type="file"] {
      position: absolute; inset: 0;
      opacity: 0; cursor: pointer; width: 100%; height: 100%;
    }
    .drop-icon {
      font-size: 2.4rem; margin-bottom: 12px; display: block; line-height: 1;
    }
    .drop-title {
      font-weight: 700; font-size: 1rem;
      color: var(--ink); margin-bottom: 4px;
    }
    .drop-sub { font-size: 0.8rem; color: var(--muted); }

    /* File chosen state */
    .file-chosen {
      display: none;
      align-items: center; gap: 12px;
      padding: 12px 16px;
      background: var(--grn-lt);
      border: 1px solid rgba(26,140,78,0.2);
      border-radius: 10px;
      margin-bottom: 20px;
    }
    .file-chosen.show { display: flex; }
    .file-chosen-icon { font-size: 1.4rem; flex-shrink: 0; }
    .file-chosen-name {
      flex: 1; min-width: 0;
      font-size: 0.85rem; font-weight: 600;
      color: var(--green); white-space: nowrap;
      overflow: hidden; text-overflow: ellipsis;
    }
    .file-chosen-size { font-size: 0.75rem; color: var(--muted); flex-shrink: 0; }
    .btn-change {
      font-size: 0.72rem; font-weight: 600;
      color: var(--muted); background: none;
      border: 1px solid var(--border);
      padding: 4px 10px; border-radius: 50px;
      cursor: pointer; flex-shrink: 0;
      transition: all 0.15s;
    }
    .btn-change:hover { border-color: var(--accent); color: var(--accent); }

    /* ── Options row ── */
    .options-row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
      margin-bottom: 20px;
    }
    .opt-block label {
      font-size: 0.68rem; font-weight: 700;
      letter-spacing: 1.2px; text-transform: uppercase;
      color: var(--muted); margin-bottom: 7px; display: block;
    }
    .opt-select, .opt-input {
      width: 100%; padding: 10px 13px;
      border: 1.5px solid var(--border);
      border-radius: 9px;
      font-family: var(--sans); font-size: 0.9rem; font-weight: 600;
      color: var(--ink); background: var(--bg);
      outline: none; cursor: pointer;
      transition: border-color 0.15s;
      appearance: none; -webkit-appearance: none;
    }
    .opt-select:focus, .opt-input:focus { border-color: var(--accent); background: var(--white); }
    .opt-input { font-family: var(--mono); }

    /* ── Convert button ── */
    .btn-convert {
      width: 100%; padding: 14px;
      background: var(--accent); color: #fff;
      border: none; border-radius: 10px;
      font-family: var(--sans); font-size: 0.97rem; font-weight: 700;
      cursor: pointer; letter-spacing: 0.2px;
      box-shadow: 0 4px 18px rgba(212,80,26,0.28);
      transition: background 0.15s, transform 0.12s, box-shadow 0.15s;
    }
    .btn-convert:hover { background: #bc4015; box-shadow: 0 6px 24px rgba(212,80,26,0.38); }
    .btn-convert:active { transform: scale(0.98); }
    .btn-convert:disabled { background: #c4bfb8; box-shadow: none; cursor: not-allowed; }

    /* ── Progress card ── */
    .progress-card {
      padding: 24px 28px;
      display: none;
    }
    .progress-card.show { display: block; }

    .progress-label {
      font-size: 0.82rem; font-weight: 600; color: var(--ink2);
      margin-bottom: 10px;
      display: flex; justify-content: space-between;
    }
    .progress-track {
      width: 100%; height: 5px;
      background: var(--border);
      border-radius: 3px; overflow: hidden;
      margin-bottom: 8px;
    }
    .progress-fill {
      height: 100%; width: 0;
      background: var(--accent);
      border-radius: 3px;
      transition: width 0.6s ease;
      animation: progressPulse 1.8s ease-in-out infinite;
    }
    @keyframes progressPulse {
      0%,100% { opacity: 1; }
      50%      { opacity: 0.65; }
    }
    .progress-sub { font-size: 0.72rem; color: var(--muted); }

    /* ── Error card ── */
    .error-card {
      padding: 16px 20px;
      border-color: #fcc;
      background: #fff5f5;
      display: none;
    }
    .error-card.show { display: block; }
    .error-card p { font-size: 0.85rem; color: #c0392b; font-weight: 500; }

    /* ── Results ── */
    .results-card { padding: 24px 28px; display: none; }
    .results-card.show { display: block; }

    .results-top {
      display: flex; align-items: center; justify-content: space-between;
      margin-bottom: 20px;
      flex-wrap: wrap; gap: 10px;
    }
    .results-title-row { display: flex; align-items: center; gap: 10px; }
    .results-title {
      font-weight: 800; font-size: 1rem; color: var(--ink);
    }
    .results-count {
      font-size: 0.72rem; font-weight: 700;
      background: var(--bg); border: 1px solid var(--border);
      color: var(--muted); padding: 3px 10px; border-radius: 50px;
    }
    .btn-dl-all {
      display: flex; align-items: center; gap: 7px;
      padding: 9px 18px;
      background: var(--ink); color: #fff;
      border: none; border-radius: 9px;
      font-family: var(--sans); font-size: 0.82rem; font-weight: 700;
      cursor: pointer;
      transition: opacity 0.15s, transform 0.12s;
      white-space: nowrap;
    }
    .btn-dl-all:hover { opacity: 0.82; transform: translateY(-1px); }

    /* ── Pages grid ── */
    .pages-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
      gap: 14px;
    }

    .page-card {
      border: 1px solid var(--border);
      border-radius: 12px;
      overflow: hidden;
      background: var(--white);
      box-shadow: var(--shadow);
      transition: box-shadow 0.2s, transform 0.2s;
    }
    .page-card:hover { box-shadow: 0 8px 28px rgba(0,0,0,0.1); transform: translateY(-3px); }

    .page-thumb-wrap {
      position: relative;
      background: var(--bg);
      aspect-ratio: 3/4;
      overflow: hidden;
    }
    .page-thumb {
      width: 100%; height: 100%;
      object-fit: contain;
      display: block;
    }
    .page-num-badge {
      position: absolute; top: 8px; left: 8px;
      font-family: var(--mono); font-size: 0.62rem; font-weight: 500;
      background: rgba(0,0,0,0.55);
      color: #fff; padding: 2px 7px; border-radius: 4px;
    }

    .page-footer {
      padding: 10px 12px;
      display: flex; align-items: center; justify-content: space-between;
      border-top: 1px solid var(--border);
    }
    .page-label {
      font-size: 0.75rem; font-weight: 600; color: var(--ink2);
    }
    .btn-dl-page {
      font-size: 0.7rem; font-weight: 700;
      color: var(--accent); background: var(--acc-lt);
      border: 1px solid rgba(212,80,26,0.2);
      padding: 4px 10px; border-radius: 6px;
      cursor: pointer; text-decoration: none;
      transition: all 0.15s;
    }
    .btn-dl-page:hover { background: var(--accent); color: #fff; border-color: var(--accent); }

    /* Reset link */
    .reset-row {
      text-align: center; padding: 4px 0;
    }
    .btn-reset {
      font-size: 0.78rem; color: var(--muted); background: none; border: none;
      cursor: pointer; text-decoration: underline; text-underline-offset: 3px;
      transition: color 0.15s;
    }
    .btn-reset:hover { color: var(--ink); }

    /* ── Footer ── */
    footer {
      text-align: center; font-size: 0.72rem; color: var(--muted);
      margin-top: 8px;
    }
    footer a { color: var(--ink2); font-weight: 700; text-decoration: none; }
    footer a:hover { color: var(--accent); }

    @media (max-width: 480px) {
      body { padding: 28px 12px 48px; }
      .upload-card { padding: 20px 16px; }
      .options-row { grid-template-columns: 1fr; }
      .pages-grid { grid-template-columns: repeat(2, 1fr); gap: 10px; }
      .results-card { padding: 18px 14px; }
      .results-top { flex-direction: column; align-items: flex-start; }
    }
  </style>
</head>
<body>

<div class="page">

  <!-- Header -->
  <header class="hdr">
    <span class="hdr-eyebrow">Converter</span>
    <h1 class="hdr-title">PDF → Image</h1>
    <p class="hdr-sub">Upload a PDF and convert every page to PNG or JPEG. Preview, then download individually or all at once.</p>
  </header>

  <!-- Upload card -->
  <div class="card upload-card">

    <!-- Drop zone -->
    <div class="drop-zone" id="dropZone">
      <input type="file" id="pdfFile" accept=".pdf" />
      <span class="drop-icon">📄</span>
      <p class="drop-title">Drop your PDF here</p>
      <p class="drop-sub">or click to browse · max 16 MB</p>
    </div>

    <!-- File chosen indicator -->
    <div class="file-chosen" id="fileChosen">
      <span class="file-chosen-icon">✅</span>
      <span class="file-chosen-name" id="chosenName">—</span>
      <span class="file-chosen-size" id="chosenSize"></span>
      <button class="btn-change" onclick="resetFile()">Change</button>
    </div>

    <!-- Options -->
    <div class="options-row">
      <div class="opt-block">
        <label for="format">Output format</label>
        <select class="opt-select" id="format">
          <option value="PNG">PNG — lossless</option>
          <option value="JPEG">JPEG — smaller</option>
        </select>
      </div>
      <div class="opt-block">
        <label for="dpi">Resolution (DPI)</label>
        <input type="number" class="opt-input" id="dpi" value="200" min="72" max="300" />
      </div>
    </div>

    <button class="btn-convert" id="convertBtn" onclick="doConvert()" disabled>
      Convert PDF
    </button>
  </div>

  <!-- Progress -->
  <div class="card progress-card" id="progressCard">
    <div class="progress-label">
      <span id="progressLabel">Converting pages…</span>
      <span id="progressPct"></span>
    </div>
    <div class="progress-track">
      <div class="progress-fill" id="progressFill" style="width:40%"></div>
    </div>
    <p class="progress-sub">Processing in your browser — this may take a moment for large files</p>
  </div>

  <!-- Error -->
  <div class="card error-card" id="errorCard">
    <p id="errorMsg"></p>
  </div>

  <!-- Results -->
  <div class="card results-card" id="resultsCard">
    <div class="results-top">
      <div class="results-title-row">
        <span class="results-title">Converted pages</span>
        <span class="results-count" id="pageCount">—</span>
      </div>
      <button class="btn-dl-all" onclick="downloadAll()">
        ↓ Download all as ZIP
      </button>
    </div>
    <div class="pages-grid" id="pagesGrid"></div>
  </div>

  <!-- Reset -->
  <div class="reset-row" id="resetRow" style="display:none">
    <button class="btn-reset" onclick="resetAll()">↑ Convert another file</button>
  </div>

  <footer>
    Made with ♥ by <a href="https://github.com/umarJ-max" target="_blank">Umar J</a>
  </footer>

</div>

<script>
  let selectedFile = null;
  let sessionId    = null;
  let pageCount    = 0;
  let currentFmt   = 'PNG';

  const dropZone   = document.getElementById('dropZone');
  const fileInput  = document.getElementById('pdfFile');
  const fileChosen = document.getElementById('fileChosen');
  const chosenName = document.getElementById('chosenName');
  const chosenSize = document.getElementById('chosenSize');
  const convertBtn = document.getElementById('convertBtn');
  const progressCard = document.getElementById('progressCard');
  const progressLabel= document.getElementById('progressLabel');
  const progressFill = document.getElementById('progressFill');
  const errorCard  = document.getElementById('errorCard');
  const errorMsg   = document.getElementById('errorMsg');
  const resultsCard= document.getElementById('resultsCard');
  const pagesGrid  = document.getElementById('pagesGrid');
  const resetRow   = document.getElementById('resetRow');

  // ── File selection ──────────────────────────────────────────────────────
  fileInput.addEventListener('change', e => { if (e.target.files[0]) pickFile(e.target.files[0]); });

  dropZone.addEventListener('dragover',  e => { e.preventDefault(); dropZone.classList.add('drag-over'); });
  dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
  dropZone.addEventListener('drop', e => {
    e.preventDefault(); dropZone.classList.remove('drag-over');
    const f = e.dataTransfer.files[0];
    if (f && f.type === 'application/pdf') pickFile(f);
  });

  function pickFile(f) {
    selectedFile = f;
    chosenName.textContent = f.name;
    chosenSize.textContent = (f.size / 1024 / 1024).toFixed(1) + ' MB';
    dropZone.style.display  = 'none';
    fileChosen.classList.add('show');
    convertBtn.disabled = false;
    // reset any old results
    hideResults();
  }

  function resetFile() {
    selectedFile = null;
    fileInput.value = '';
    dropZone.style.display = '';
    fileChosen.classList.remove('show');
    convertBtn.disabled = true;
    hideResults();
  }

  function hideResults() {
    progressCard.classList.remove('show');
    errorCard.classList.remove('show');
    resultsCard.classList.remove('show');
    resetRow.style.display = 'none';
  }

  // ── Convert ─────────────────────────────────────────────────────────────
  async function doConvert() {
    if (!selectedFile) return;

    currentFmt = document.getElementById('format').value;
    const dpi  = document.getElementById('dpi').value;

    convertBtn.disabled = true;
    progressCard.classList.add('show');
    progressLabel.textContent = 'Uploading and converting…';
    progressFill.style.width  = '20%';
    errorCard.classList.remove('show');
    resultsCard.classList.remove('show');
    resetRow.style.display = 'none';

    const formData = new FormData();
    formData.append('pdf', selectedFile);
    formData.append('format', currentFmt);
    formData.append('dpi', dpi);

    try {
      progressFill.style.width = '45%';
      progressLabel.textContent = 'Processing pages…';

      const res  = await fetch('/convert', { method: 'POST', body: formData });
      progressFill.style.width = '85%';

      if (!res.ok) {
        const txt = await res.text();
        throw new Error(txt || 'Conversion failed');
      }

      const data = await res.json();
      if (data.error) throw new Error(data.error);

      sessionId  = data.session_id;
      pageCount  = data.pages.length;

      progressFill.style.width = '100%';
      progressLabel.textContent = 'Done!';

      setTimeout(() => {
        progressCard.classList.remove('show');
        showResults(data.pages);
      }, 500);

    } catch(err) {
      progressCard.classList.remove('show');
      errorMsg.textContent = err.message || 'Something went wrong. Please try again.';
      errorCard.classList.add('show');
      convertBtn.disabled = false;
    }
  }

  // ── Show results ─────────────────────────────────────────────────────────
  function showResults(pages) {
    document.getElementById('pageCount').textContent = pages.length + ' page' + (pages.length !== 1 ? 's' : '');
    pagesGrid.innerHTML = '';

    pages.forEach((b64, i) => {
      const card = document.createElement('div');
      card.className = 'page-card';

      const mime = currentFmt === 'JPEG' ? 'image/jpeg' : 'image/png';
      const src  = `data:${mime};base64,${b64}`;

      card.innerHTML = `
        <div class="page-thumb-wrap">
          <img class="page-thumb" src="${src}" alt="Page ${i+1}" loading="lazy" />
          <span class="page-num-badge">p.${i+1}</span>
        </div>
        <div class="page-footer">
          <span class="page-label">Page ${i+1}</span>
          <a class="btn-dl-page" href="#" onclick="downloadPage(${i}, event)">↓ Save</a>
        </div>
      `;
      pagesGrid.appendChild(card);
    });

    resultsCard.classList.add('show');
    resetRow.style.display = 'block';
    convertBtn.disabled = false;

    setTimeout(() => resultsCard.scrollIntoView({ behavior: 'smooth', block: 'start' }), 80);
  }

  // ── Downloads ────────────────────────────────────────────────────────────
  async function downloadPage(idx, e) {
    e.preventDefault();
    const res  = await fetch(`/download/${sessionId}/${idx}`);
    const blob = await res.blob();
    const url  = URL.createObjectURL(blob);
    const a    = Object.assign(document.createElement('a'), {
      href: url, download: `page_${idx+1}.${currentFmt.toLowerCase()}`
    });
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  async function downloadAll() {
    const res  = await fetch(`/download-all/${sessionId}`);
    const blob = await res.blob();
    const url  = URL.createObjectURL(blob);
    const a    = Object.assign(document.createElement('a'), {
      href: url, download: 'pages.zip'
    });
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  function resetAll() {
    resetFile();
    sessionId = null;
  }
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/convert", methods=["POST"])
def convert_pdf():
    if "pdf" not in request.files:
        return "No PDF file uploaded", 400

    file = request.files["pdf"]
    if not file or file.filename == "":
        return "No file selected", 400

    if not file.filename.lower().endswith(".pdf"):
        return "Please upload a PDF file", 400

    fmt = request.form.get("format", "PNG").upper()
    if fmt not in ("PNG", "JPEG"):
        fmt = "PNG"

    try:
        dpi = max(72, min(300, int(request.form.get("dpi", 200))))
    except ValueError:
        dpi = 200

    with tempfile.TemporaryDirectory() as tmp:
        pdf_path = os.path.join(tmp, secure_filename(file.filename))
        file.save(pdf_path)

        try:
            session_id   = str(uuid.uuid4())
            pdf_doc      = fitz.open(pdf_path)
            pages_b64    = []
            session_imgs = []

            for page_num in range(pdf_doc.page_count):
                page = pdf_doc[page_num]
                mat  = fitz.Matrix(dpi / 72, dpi / 72)
                pix  = page.get_pixmap(matrix=mat)

                img = Image.open(io.BytesIO(pix.tobytes("ppm")))
                buf = io.BytesIO()
                img.save(buf, format=fmt)
                img_bytes = buf.getvalue()

                session_imgs.append({"data": img_bytes, "format": fmt})
                pages_b64.append(base64.b64encode(img_bytes).decode("utf-8"))

            pdf_doc.close()
            converted_sessions[session_id] = session_imgs

            return jsonify({"session_id": session_id, "pages": pages_b64})

        except Exception as e:
            return jsonify({"error": f"Conversion failed: {str(e)}"}), 500


@app.route("/download/<session_id>/<int:page_index>")
def download_page(session_id, page_index):
    if session_id not in converted_sessions:
        return "Session not found", 404
    pages = converted_sessions[session_id]
    if page_index >= len(pages):
        return "Page not found", 404
    p = pages[page_index]
    return send_file(
        io.BytesIO(p["data"]),
        as_attachment=True,
        download_name=f'page_{page_index + 1}.{p["format"].lower()}',
        mimetype=f'image/{p["format"].lower()}'
    )


@app.route("/download-all/<session_id>")
def download_all(session_id):
    if session_id not in converted_sessions:
        return "Session not found", 404
    pages = converted_sessions[session_id]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for i, p in enumerate(pages):
            zf.writestr(f'page_{i + 1:03d}.{p["format"].lower()}', p["data"])
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name="pages.zip")


if __name__ == "__main__":
    app.run(debug=True)
