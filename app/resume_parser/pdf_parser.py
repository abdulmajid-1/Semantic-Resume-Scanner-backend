"""
PDF Parser module.
Extracts raw text from PDF files using PyMuPDF (fitz) and falls back to pdfplumber.
"""

import fitz  # PyMuPDF
import pdfplumber
import logging

logger = logging.getLogger(__name__)


def extract_text_from_pdf(file_path: str) -> str:
    """
    Extracts text from a PDF file using PyMuPDF. If that fails or returns empty,
    falls back to pdfplumber.
    """
    text = ""
    try:
        # Try PyMuPDF first (fast and robust)
        doc = fitz.open(file_path)
        for page in doc:
            text += page.get_text()
        doc.close()
    except Exception as e:
        logger.warning(f"PyMuPDF failed to extract text from {file_path}: {e}. Retrying with pdfplumber.")

    if not text.strip():
        try:
            # Fallback to pdfplumber
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            logger.error(f"pdfplumber also failed to extract text from {file_path}: {e}")

    return text
