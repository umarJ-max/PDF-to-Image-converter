#!/usr/bin/env python3
import os
import sys
from pdf2image import convert_from_path
import argparse

def convert_pdf_to_images(pdf_path, output_format='PNG', output_dir=None, dpi=200):
    """Convert PDF to images with specified format"""
    
    if not os.path.exists(pdf_path):
        print(f"Error: PDF file '{pdf_path}' not found.")
        return False
    
    # Set output directory
    if output_dir is None:
        output_dir = os.path.dirname(pdf_path)
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Get PDF filename without extension
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    
    try:
        # Convert PDF to images
        print(f"Converting {pdf_path} to {output_format} format...")
        pages = convert_from_path(pdf_path, dpi=dpi)
        
        for i, page in enumerate(pages, 1):
            output_filename = f"{pdf_name}_page_{i:03d}.{output_format.lower()}"
            output_path = os.path.join(output_dir, output_filename)
            page.save(output_path, output_format)
            print(f"Saved: {output_filename}")
        
        print(f"Successfully converted {len(pages)} pages to {output_format}")
        return True
        
    except Exception as e:
        print(f"Error converting PDF: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Convert PDF to images')
    parser.add_argument('pdf_path', help='Path to the PDF file')
    parser.add_argument('-f', '--format', default='PNG', 
                       choices=['PNG', 'JPEG', 'JPG', 'TIFF', 'BMP'],
                       help='Output image format (default: PNG)')
    parser.add_argument('-o', '--output', help='Output directory')
    parser.add_argument('-d', '--dpi', type=int, default=200, 
                       help='DPI for output images (default: 200)')
    
    args = parser.parse_args()
    
    # Convert JPG to JPEG for PIL compatibility
    format_name = 'JPEG' if args.format == 'JPG' else args.format
    
    success = convert_pdf_to_images(
        args.pdf_path, 
        format_name, 
        args.output, 
        args.dpi
    )
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()