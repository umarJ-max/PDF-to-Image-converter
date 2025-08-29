from flask import Flask, request, send_file, render_template_string, jsonify
import os
import tempfile
import zipfile
import fitz  # PyMuPDF
from PIL import Image
from werkzeug.utils import secure_filename
import io

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Store converted pages temporarily
converted_sessions = {}

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>PDF to Image Converter</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .upload-area { border: 2px dashed #ccc; padding: 40px; text-align: center; margin: 20px 0; }
        button { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; margin: 5px; }
        button:hover { background: #0056b3; }
        .progress { display: none; margin: 20px 0; }
        .pages-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; margin: 20px 0; }
        .page-item { border: 1px solid #ddd; padding: 15px; border-radius: 8px; text-align: center; }
        .page-preview { max-width: 100%; height: auto; border: 1px solid #ccc; }
        .download-all { text-align: center; margin: 20px 0; }
    </style>
</head>
<body>
    <h1>PDF to Image Converter</h1>
    <form id="uploadForm" enctype="multipart/form-data">
        <div class="upload-area" id="uploadArea">
            <input type="file" id="pdfFile" name="pdf" accept=".pdf" required>
            <p>Choose PDF file or drag and drop here</p>
        </div>
        <div>
            <label>Format: 
                <select name="format" id="format">
                    <option value="PNG">PNG</option>
                    <option value="JPEG">JPEG</option>
                </select>
            </label>
            <label>DPI: 
                <input type="number" name="dpi" id="dpi" value="200" min="72" max="300">
            </label>
        </div>
        <button type="submit">Convert PDF</button>
    </form>
    <div class="progress" id="progress">Converting...</div>
    <div class="result" id="result"></div>

    <script>
        const form = document.getElementById('uploadForm');
        const progress = document.getElementById('progress');
        const result = document.getElementById('result');

        let sessionId = null;

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(form);
            
            progress.style.display = 'block';
            result.innerHTML = '';
            
            try {
                const response = await fetch('/convert', {
                    method: 'POST',
                    body: formData
                });
                
                if (response.ok) {
                    const data = await response.json();
                    sessionId = data.session_id;
                    displayPages(data.pages, document.getElementById('format').value);
                } else {
                    const error = await response.text();
                    result.innerHTML = `<p style="color: red;">Error: ${error}</p>`;
                }
            } catch (error) {
                result.innerHTML = `<p style="color: red;">Error: ${error.message}</p>`;
            }
            
            progress.style.display = 'none';
        });

        function displayPages(pages, format) {
            let html = '<div class="download-all"><button onclick="downloadAll()">Download All as ZIP</button></div>';
            html += '<div class="pages-grid">';
            
            pages.forEach((page, index) => {
                html += `
                    <div class="page-item">
                        <h3>Page ${index + 1}</h3>
                        <img src="data:image/${format.toLowerCase()};base64,${page}" class="page-preview" alt="Page ${index + 1}">
                        <br>
                        <button onclick="downloadPage(${index}, '${format}')">Download Page ${index + 1}</button>
                    </div>
                `;
            });
            
            html += '</div>';
            result.innerHTML = html;
        }

        async function downloadPage(pageIndex, format) {
            const response = await fetch(`/download/${sessionId}/${pageIndex}`);
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `page_${pageIndex + 1}.${format.toLowerCase()}`;
            a.click();
        }

        async function downloadAll() {
            const response = await fetch(`/download-all/${sessionId}`);
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'all_pages.zip';
            a.click();
        }
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/convert', methods=['POST'])
def convert_pdf():
    if 'pdf' not in request.files:
        return 'No PDF file uploaded', 400
    
    file = request.files['pdf']
    if file.filename == '':
        return 'No file selected', 400
    
    if not file.filename.lower().endswith('.pdf'):
        return 'Please upload a PDF file', 400
    
    format_type = request.form.get('format', 'PNG')
    dpi = int(request.form.get('dpi', 200))
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Save uploaded PDF
        pdf_path = os.path.join(temp_dir, secure_filename(file.filename))
        file.save(pdf_path)
        
        try:
            import uuid
            import base64
            
            # Generate session ID
            session_id = str(uuid.uuid4())
            
            # Convert PDF to images using PyMuPDF
            pdf_doc = fitz.open(pdf_path)
            pages_data = []
            converted_images = []
            
            for page_num in range(pdf_doc.page_count):
                page = pdf_doc[page_num]
                # Render page to image with specified DPI
                mat = fitz.Matrix(dpi/72, dpi/72)
                pix = page.get_pixmap(matrix=mat)
                
                # Convert to PIL Image
                img_data = pix.tobytes("ppm")
                img = Image.open(io.BytesIO(img_data))
                
                # Save to memory for base64 encoding
                img_buffer = io.BytesIO()
                img.save(img_buffer, format=format_type)
                img_bytes = img_buffer.getvalue()
                
                # Store for session
                converted_images.append({
                    'data': img_bytes,
                    'format': format_type
                })
                
                # Create base64 for preview
                img_base64 = base64.b64encode(img_bytes).decode('utf-8')
                pages_data.append(img_base64)
            
            pdf_doc.close()
            
            # Store in session
            converted_sessions[session_id] = converted_images
            
            return jsonify({
                'session_id': session_id,
                'pages': pages_data
            })
            
        except Exception as e:
            return jsonify({'error': f'Conversion failed: {str(e)}'}), 500

# Vercel will handle the app running
@app.route('/download/<session_id>/<int:page_index>')
def download_page(session_id, page_index):
    if session_id not in converted_sessions:
        return 'Session not found', 404
    
    pages = converted_sessions[session_id]
    if page_index >= len(pages):
        return 'Page not found', 404
    
    page_data = pages[page_index]
    return send_file(
        io.BytesIO(page_data['data']),
        as_attachment=True,
        download_name=f'page_{page_index+1}.{page_data["format"].lower()}',
        mimetype=f'image/{page_data["format"].lower()}'
    )

@app.route('/download-all/<session_id>')
def download_all(session_id):
    if session_id not in converted_sessions:
        return 'Session not found', 404
    
    pages = converted_sessions[session_id]
    
    with tempfile.TemporaryDirectory() as temp_dir:
        zip_path = os.path.join(temp_dir, 'all_pages.zip')
        with zipfile.ZipFile(zip_path, 'w') as zip_file:
            for i, page_data in enumerate(pages):
                filename = f'page_{i+1:03d}.{page_data["format"].lower()}'
                zip_file.writestr(filename, page_data['data'])
        
        return send_file(zip_path, as_attachment=True, download_name='all_pages.zip')