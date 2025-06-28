import PyPDF2
import os
import pytesseract
from pdf2image import convert_from_path
from PIL import Image # Pillow is imported via PIL

# --- IMPORTANT CONFIGURATION ---
# 1. If Tesseract is NOT in your system's PATH, uncomment and set the correct path:
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# 2. If Poppler's 'bin' directory is NOT in your system's PATH, uncomment and set the correct path:
# poppler_path = r'C:\Program Files\poppler-24.02.0\Library\bin' # Adjust version and path as per your extraction
# (Note: pdf2image's convert_from_path takes 'poppler_path' argument, which we'll use below)


def extract_text_from_native_pdf(pdf_path: str) -> str:
    """
    Extracts text from a native (text-based) PDF document efficiently.
    Handles encrypted or corrupted PDFs gracefully.
    """
    if not os.path.exists(pdf_path):
        return ""

    try:
        extracted_pages_text = []
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)

            if reader.is_encrypted:
                # Attempt to decrypt with an empty password first, common for no password
                # For real-world, you might prompt for a password or indicate a need for one.
                try:
                    reader.decrypt('') 
                    print(f"Warning: PDF '{os.path.basename(pdf_path)}' was encrypted but successfully decrypted with no password.")
                except PyPDF2.errors.FileNotDecryptedError:
                    print(f"Error: PDF '{os.path.basename(pdf_path)}' is encrypted and requires a password. Cannot extract text.")
                    return "ENCRYPTED_PDF" # Special sentinel value for encrypted PDFs

            for page_num in range(len(reader.pages)):
                page = reader.pages[page_num]
                text = page.extract_text()
                if text:
                    extracted_pages_text.append(text)
        
        return "\n".join(extracted_pages_text)

    except PyPDF2.errors.PdfReadError:
        print(f"Error: PDF '{os.path.basename(pdf_path)}' appears to be corrupted or malformed. Cannot extract text.")
        return "CORRUPTED_PDF" # Special sentinel value for corrupted PDFs
    except Exception as e:
        print(f"An unexpected error occurred during native PDF processing of {pdf_path}: {e}")
        return ""


def extract_text_from_scanned_pdf(pdf_path: str, poppler_path: str = None) -> str:
    """
    Extracts text from a scanned (image-based) PDF document using OCR.

    Args:
        pdf_path (str): The path to the scanned PDF file.
        poppler_path (str, optional): Path to Poppler's 'bin' directory if not in system PATH.

    Returns:
        str: The OCR-extracted text from the PDF.
             Returns an empty string if the file cannot be processed or OCR fails.
    """
    if not os.path.exists(pdf_path):
        return ""

    full_text = []
    try:
        # Convert PDF pages to images.
        # Pass poppler_path if it's not in the system's PATH.
        images = convert_from_path(pdf_path, dpi=300, poppler_path=poppler_path)

        for i, image in enumerate(images):
            # Perform OCR on each image
            text = pytesseract.image_to_string(image)
            if text:
                full_text.append(text)
            else:
                print(f"Warning: No text found on page {i+1} using OCR for {os.path.basename(pdf_path)}.")
                
    except pytesseract.TesseractNotFoundError:
        print("Error: Tesseract is not installed or not in your system PATH.")
        print("Please install Tesseract and ensure it's accessible or configure pytesseract.pytesseract.tesseract_cmd.")
        return ""
    except Exception as e:
        print(f"An error occurred during OCR processing of {os.path.basename(pdf_path)}: {e}")
        return ""

    return "\n".join(full_text)


def extract_text_from_pdf(pdf_path: str, poppler_path: str = None) -> str:
    """
    Attempts to extract text from a PDF, trying native extraction first,
    then falling back to OCR if native extraction yields no or insufficient text.
    Handles specific error codes from native extraction.

    Args:
        pdf_path (str): The path to the PDF file (can be native or scanned).
        poppler_path (str, optional): Path to Poppler's 'bin' directory if not in system PATH.

    Returns:
        str: The extracted text from the PDF. Returns an empty string if extraction fails
             or specific error types (encrypted/corrupted) are encountered.
    """
    if not os.path.exists(pdf_path):
        print(f"Error: PDF file not found at {pdf_path}")
        return ""

    print(f"Attempting native text extraction for {os.path.basename(pdf_path)}...")
    native_text = extract_text_from_native_pdf(pdf_path)

    # Check for specific error messages from native extraction
    if native_text == "ENCRYPTED_PDF":
        return "" # Don't try OCR if it's explicitly encrypted
    if native_text == "CORRUPTED_PDF":
        return "" # Don't try OCR if it's explicitly corrupted

    # A heuristic: if native text is too short, or empty, assume it's scanned or poorly structured
    # You might refine this threshold later. For now, if empty, try OCR.
    if not native_text or len(native_text.strip()) < 50: # Adjust threshold as needed for your data
        print(f"Native extraction for {os.path.basename(pdf_path)} failed or was insufficient. Attempting OCR...")
        scanned_text = extract_text_from_scanned_pdf(pdf_path, poppler_path=poppler_path)
        if scanned_text:
            print(f"Successfully extracted text from {os.path.basename(pdf_path)} using OCR.")
            return scanned_text
        else:
            print(f"OCR also failed for {os.path.basename(pdf_path)}. Could not extract text.")
            return ""
    else:
        print(f"Successfully extracted text from {os.path.basename(pdf_path)} using native method.")
        return native_text