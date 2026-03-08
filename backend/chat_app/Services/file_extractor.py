import os
import cv2
from PIL import Image
import pytesseract
import PyPDF2
from pdf2image import convert_from_path
import numpy as np

def preprocess_image_cv(path):
    """
    Preprocess image for OCR using OpenCV.
    """
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f"Could not read image: {path}")
    
    # Resize for consistent processing if very large
    h, w = img.shape[:2]
    max_dim = 1600
    if max(h, w) > max_dim:
        scale = max_dim / max(h, w)
        img = cv2.resize(img, (int(w*scale), int(h*scale)), interpolation=cv2.INTER_AREA)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Denoise
    den = cv2.fastNlMeansDenoising(gray, None, h=10)
    # Adaptive threshold to binarize
    th = cv2.adaptiveThreshold(den, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                               cv2.THRESH_BINARY, 31, 15)
    return th

def ocr_from_preprocessed_image(image_path):
    """
    Apply preprocessing and extract text using pytesseract.
    """
    tcmd = os.environ.get('TESSERACT_CMD')
    if tcmd:
        pytesseract.pytesseract.tesseract_cmd = tcmd
    
    try:
        # Preprocess the image
        preprocessed = preprocess_image_cv(image_path)
        pil_image = Image.fromarray(preprocessed)
        
        # Extract text
        text = pytesseract.image_to_string(pil_image, lang='eng')
        return text
    except Exception as e:
        print(f"Error in OCR: {e}")
        return ""

def extract_text_from_pdf(pdf_path):
    """
    Extract text from PDF. If extractable, get text directly. Otherwise OCR scanned pages.
    """
    text_parts = []
    
    try:
        # Try direct text extraction first
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            num_pages = min(len(reader.pages), 5)  # Max 5 pages
            
            # Check if PDF has extractable text
            extracted_text = ""
            for page_num in range(num_pages):
                page_text = reader.pages[page_num].extract_text()
                if page_text:
                    extracted_text += page_text + "\n"
            
            # If we got meaningful text, return it
            if extracted_text.strip():
                return extracted_text
        
        # Otherwise, it's a scanned PDF - convert to images and OCR
        print("PDF appears to be scanned. Converting pages to images for OCR...")
        # Poppler path might be needed on Windows if not in PATH
        # For now assuming it's in PATH or user handles it
        images = convert_from_path(pdf_path, first_page=1, last_page=5)
        
        for i, img in enumerate(images):
            # Save temporarily
            temp_img_path = f"{pdf_path}_temp_page_{i}.png"
            img.save(temp_img_path)
            
            # OCR the page
            page_text = ocr_from_preprocessed_image(temp_img_path)
            text_parts.append(page_text)
            
            # Clean up temp file
            if os.path.exists(temp_img_path):
                os.remove(temp_img_path)
        
        return "\n\n".join(text_parts)
        
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return ""
