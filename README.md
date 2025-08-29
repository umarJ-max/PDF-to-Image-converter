# 📄 PDF to Image Converter

> **Professional PDF to Image Conversion Tool** - Convert PDF documents to high-quality PNG/JPEG images with ease.

[![Vercel](https://img.shields.io/badge/Deployed%20on-Vercel-black?style=for-the-badge&logo=vercel)](https://vercel.com)
[![Python](https://img.shields.io/badge/Python-3.8+-blue?style=for-the-badge&logo=python)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.0+-green?style=for-the-badge&logo=flask)](https://flask.palletsprojects.com)

## ✨ Features

- 🖼️ **High-Quality Conversion** - Convert PDF pages to PNG/JPEG with customizable DPI (72-300)
- 👀 **Live Preview** - See all pages before downloading
- 📱 **Mobile Responsive** - Works perfectly on desktop, tablet, and mobile
- ⚡ **Individual Downloads** - Download specific pages you need
- 📦 **Batch Download** - Get all pages in a single ZIP file
- 🔒 **Secure Processing** - Files processed temporarily and automatically deleted
- 🎨 **Modern UI** - Clean, professional interface with smooth animations

## 🚀 Live Demo

[**Try it now →**](your-vercel-url-here)

## 🛠️ Tech Stack

- **Backend**: Python, Flask
- **PDF Processing**: PyMuPDF (fitz)
- **Image Processing**: Pillow (PIL)
- **Frontend**: HTML5, CSS3, JavaScript
- **Deployment**: Vercel
- **Styling**: Modern CSS with gradients and animations

## 📋 How to Use

1. **Upload** - Select or drag & drop your PDF file
2. **Configure** - Choose output format (PNG/JPEG) and DPI quality
3. **Convert** - Click convert and wait for processing
4. **Preview** - View all converted pages
5. **Download** - Get individual pages or all as ZIP

## 🏃‍♂️ Quick Start

### Local Development

```bash
# Clone the repository
git clone <your-repo-url>
cd PDF-To-Image-Converter

# Install dependencies
pip install -r requirements.txt

# Run locally
python app.py
```

### Deploy to Vercel

1. Fork this repository
2. Connect to Vercel
3. Deploy automatically

## 📁 Project Structure

```
PDF-To-Image-Converter/
├── app.py              # Main Flask application
├── api/
│   └── index.py        # Vercel entry point
├── requirements.txt    # Python dependencies
├── vercel.json        # Vercel configuration
├── .vercelignore      # Files to ignore during deployment
└── README.md          # This file
```

## ⚙️ Configuration

- **Max File Size**: 16MB
- **Supported Formats**: PDF input, PNG/JPEG output
- **DPI Range**: 72-300 DPI
- **Session Storage**: Temporary (auto-cleanup)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

## 👨‍💻 Author

**Umar J**
- Professional PDF Solutions Developer
- Focused on creating efficient, user-friendly web applications

---

⭐ **Star this repo if you found it helpful!**