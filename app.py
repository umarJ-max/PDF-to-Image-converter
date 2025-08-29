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
    <title>PDF to Image Converter - Umar J</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header { text-align: center; color: white; margin-bottom: 30px; }
        .header h1 { font-size: 2.5rem; margin-bottom: 10px; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
        .brand { font-size: 1.2rem; opacity: 0.9; font-weight: 300; }
        .main-card { background: white; border-radius: 20px; padding: 30px; box-shadow: 0 20px 40px rgba(0,0,0,0.1); }
        .upload-area { border: 3px dashed #667eea; padding: 50px; text-align: center; margin: 30px 0; border-radius: 15px; background: #f8f9ff; transition: all 0.3s ease; }
        .upload-area:hover { border-color: #764ba2; background: #f0f2ff; }
        .form-controls { display: flex; gap: 20px; justify-content: center; align-items: center; margin: 20px 0; flex-wrap: wrap; }
        .form-controls label { font-weight: 600; color: #333; }
        .form-controls select, .form-controls input { padding: 8px 12px; border: 2px solid #e1e5e9; border-radius: 8px; font-size: 14px; }
        .form-controls select:focus, .form-controls input:focus { outline: none; border-color: #667eea; }
        button { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 12px 25px; border: none; border-radius: 25px; cursor: pointer; margin: 5px; font-weight: 600; transition: all 0.3s ease; box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4); }
        button:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6); }
        .progress { display: none; text-align: center; margin: 20px 0; color: #667eea; font-weight: 600; }
        .pages-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 25px; margin: 30px 0; }
        .page-item { background: white; border: 1px solid #e1e5e9; padding: 20px; border-radius: 15px; text-align: center; box-shadow: 0 5px 15px rgba(0,0,0,0.08); transition: all 0.3s ease; }
        .page-item:hover { transform: translateY(-5px); box-shadow: 0 10px 25px rgba(0,0,0,0.15); }
        .page-item h3 { color: #333; margin-bottom: 15px; font-size: 1.1rem; }
        .page-preview { max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 3px 10px rgba(0,0,0,0.1); }
        .download-all { text-align: center; margin: 30px 0; }
        .footer { text-align: center; color: white; margin-top: 40px; opacity: 0.8; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>PDF to Image Converter</h1>
            <div class="brand">Powered by Umar J</div>
        </div>
        <div class="main-card">
    <form id="uploadForm" enctype="multipart/form-data">
        <div class="upload-area" id="uploadArea">
            <input type="file" id="pdfFile" name="pdf" accept=".pdf" required>
            <p>Choose PDF file or drag and drop here</p>
        </div>
        <div class="form-controls">
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
        </div>
        <div class="footer">
            <p>&copy; 2024 Umar J - Professional PDF Solutions</p>
        </div>
    </div>
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