import sys
import os

# Make sure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, send_file, render_template, jsonify
import tempfile
import zipfile
import fitz  # PyMuPDF
from PIL import Image
from werkzeug.utils import secure_filename
import io
import uuid

# Point Flask at the templates folder one level up (project root/templates)
template_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates')

app = Flask(__name__, template_folder=template_dir)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB

converted_sessions = {}


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/convert', methods=['POST'])
def convert_pdf():
    if 'pdf' not in request.files:
        return 'No PDF file uploaded', 400

    file = request.files['pdf']
    if not file or file.filename == '':
        return 'No file selected', 400

    if not file.filename.lower().endswith('.pdf'):
        return 'Please upload a PDF file', 400

    fmt = request.form.get('format', 'PNG').upper()
    if fmt not in ('PNG', 'JPEG'):
        fmt = 'PNG'

    try:
        dpi = max(72, min(300, int(request.form.get('dpi', 200))))
    except ValueError:
        dpi = 200

    with tempfile.TemporaryDirectory() as tmp:
        pdf_path = os.path.join(tmp, secure_filename(file.filename))
        file.save(pdf_path)

        try:
            import base64
            session_id  = str(uuid.uuid4())
            pdf_doc     = fitz.open(pdf_path)
            pages_b64   = []
            session_imgs = []

            for page_num in range(pdf_doc.page_count):
                page = pdf_doc[page_num]
                mat  = fitz.Matrix(dpi / 72, dpi / 72)
                pix  = page.get_pixmap(matrix=mat)

                img  = Image.open(io.BytesIO(pix.tobytes("ppm")))
                buf  = io.BytesIO()
                img.save(buf, format=fmt)
                img_bytes = buf.getvalue()

                session_imgs.append({'data': img_bytes, 'format': fmt})
                pages_b64.append(base64.b64encode(img_bytes).decode('utf-8'))

            pdf_doc.close()
            converted_sessions[session_id] = session_imgs

            return jsonify({'session_id': session_id, 'pages': pages_b64})

        except Exception as e:
            return jsonify({'error': f'Conversion failed: {str(e)}'}), 500


@app.route('/download/<session_id>/<int:page_index>')
def download_page(session_id, page_index):
    if session_id not in converted_sessions:
        return 'Session not found', 404
    pages = converted_sessions[session_id]
    if page_index >= len(pages):
        return 'Page not found', 404
    p = pages[page_index]
    return send_file(
        io.BytesIO(p['data']),
        as_attachment=True,
        download_name=f'page_{page_index + 1}.{p["format"].lower()}',
        mimetype=f'image/{p["format"].lower()}'
    )


@app.route('/download-all/<session_id>')
def download_all(session_id):
    if session_id not in converted_sessions:
        return 'Session not found', 404
    pages = converted_sessions[session_id]

    with tempfile.TemporaryDirectory() as tmp:
        zip_path = os.path.join(tmp, 'pages.zip')
        with zipfile.ZipFile(zip_path, 'w') as zf:
            for i, p in enumerate(pages):
                zf.writestr(f'page_{i + 1:03d}.{p["format"].lower()}', p['data'])
        return send_file(zip_path, as_attachment=True, download_name='pages.zip')


if __name__ == '__main__':
    app.run(debug=True)
