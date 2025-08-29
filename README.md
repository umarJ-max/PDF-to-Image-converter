# PDF to Image Converter

A complete PDF to image conversion tool with both web interface and command-line support. Converts PDF files to PNG, JPEG, TIFF, or BMP formats.

## Features
- Web interface for easy drag-and-drop conversion
- Command-line interface for batch processing
- Multiple output formats (PNG, JPEG, TIFF, BMP)
- Customizable DPI settings
- Batch download as ZIP file (web interface)

## Quick Start

### Windows Users:
1. Run `install.bat` to install dependencies
2. For web interface: `python run.py web`
3. For command line: `python run.py cli your_file.pdf`

### Manual Installation:
1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Install poppler (required for pdf2image):
   - **Windows**: Download from https://github.com/oschwartz10612/poppler-windows/releases/
   - **macOS**: `brew install poppler`
   - **Linux**: `sudo apt-get install poppler-utils`

## Usage

### Web Interface
```bash
python run.py web
# or directly: python app.py
```
Then open http://localhost:5000 in your browser.

### Command Line Interface

#### Basic usage (PNG format):
```bash
python run.py cli document.pdf
# or directly: python pdf_converter.py document.pdf
```

#### Specify output format:
```bash
python run.py cli document.pdf -f JPEG
python run.py cli document.pdf -f TIFF
```

#### Specify output directory:
```bash
python run.py cli document.pdf -o output_folder
```

#### Custom DPI:
```bash
python run.py cli document.pdf -d 300
```

## Supported Formats
- PNG (default)
- JPEG/JPG
- TIFF
- BMP

## Examples
```bash
# Convert to PNG (default)
python pdf_converter.py sample.pdf

# Convert to JPEG with custom output directory
python pdf_converter.py sample.pdf -f JPEG -o images/

# High quality conversion
python pdf_converter.py sample.pdf -f PNG -d 300
```