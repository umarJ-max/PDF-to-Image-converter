# PDF to Image Converter

Upload a PDF and convert every page to PNG or JPEG. Preview thumbnails, then download pages individually or all at once as a ZIP.

## What it does

- Upload by click or drag-and-drop (max 16 MB)
- Choose PNG (lossless) or JPEG (smaller)
- Set DPI — 72 to 300 (default 200)
- Live progress bar during conversion
- Page thumbnails with per-page download
- "Download all as ZIP" button
- Auto-scrolls to results when ready

## Stack

Python · Flask · PyMuPDF (fitz) · Pillow · Deployed on Vercel via `@vercel/python`

## Files

```
app.py                  — Flask routes: /, /convert, /download, /download-all
templates/index.html    — full frontend
api/index.py            — Vercel entry point (imports app from app.py)
requirements.txt        — PyMuPDF, Pillow, Flask, Werkzeug
vercel.json             — routes everything through api/index.py
```

## Local dev

```bash
pip install -r requirements.txt
python app.py
```

Opens at `http://localhost:5000`

## Trash — delete from repo

`pdf_converter.py` — a dead CLI script, not used by the web app at all.
