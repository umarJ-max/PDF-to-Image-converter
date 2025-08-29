from flask import Flask, request, send_file, render_template_string, jsonify
import os
import tempfile
import zipfile
from pdf2image import convert_from_path
from werkzeug.utils import secure_filename
import shutil

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>PDF to Image Converter</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .upload-area { border: 2px dashed #ccc; padding: 40px; text-align: center; margin: 20px 0; }
        .upload-area.dragover { border-color: #007bff; background-color: #f8f9fa; }
        button { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; }
        button:hover { background: #0056b3; }
        .progress { display: none; margin: 20px 0; }
        .result { margin: 20px 0; }
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
                <select name="format">
                    <option value="PNG">PNG</option>
                    <option value="JPEG">JPEG</option>
                </select>
            </label>
            <label>DPI: 
                <input type="number" name="dpi" value="200" min="72" max="300">
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
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'converted_images.zip';
                    a.click();
                    result.innerHTML = '<p style="color: green;">Conversion successful! Download started.</p>';
                } else {
                    const error = await response.text();
                    result.innerHTML = `<p style="color: red;">Error: ${error}</p>`;
                }
            } catch (error) {
                result.innerHTML = `<p style="color: red;">Error: ${error.message}</p>`;
            }
            
            progress.style.display = 'none';
        });
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
            # Convert PDF to images
            pages = convert_from_path(pdf_path, dpi=dpi)
            
            # Create zip file with converted images
            zip_path = os.path.join(temp_dir, 'converted_images.zip')
            with zipfile.ZipFile(zip_path, 'w') as zip_file:
                for i, page in enumerate(pages, 1):
                    img_filename = f"page_{i:03d}.{format_type.lower()}"
                    img_path = os.path.join(temp_dir, img_filename)
                    page.save(img_path, format_type)
                    zip_file.write(img_path, img_filename)
            
            return send_file(zip_path, as_attachment=True, download_name='converted_images.zip')
            
        except Exception as e:
            return f'Conversion failed: {str(e)}', 500

# Vercel will handle the app running