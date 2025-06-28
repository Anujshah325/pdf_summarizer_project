import os
import sys
import nltk
from nltk.tokenize import sent_tokenize # Make sure sent_tokenize is imported if used in DocumentTranslator

import pytesseract
from pdf2image import convert_from_path # This is needed for the extract_text_from_pdf module to use

# --- Configuration for Poppler and Tesseract ---
# IMPORTANT: Update these paths to match your actual installation locations!

# Path to Poppler's 'bin' folder (where pdftoppm.exe is located)
# Example: r"C:\Poppler\poppler-23.11.0\Library\bin"
# Your path: C:\Users\shaha\Downloads\Release-24.08.0-0\poppler-24.08.0\Library\bin
GLOBAL_POPPLER_PATH = r"C:\Users\shaha\Downloads\Release-24.08.0-0\poppler-24.08.0\Library\bin"

# Path to Tesseract's executable (tesseract.exe)
# This MUST be the installed executable, NOT the installer file!
# Example: r"C:\Program Files\Tesseract-OCR\tesseract.exe"
GLOBAL_TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe" # <--- IMPORTANT: VERIFY THIS IS YOUR ACTUAL TESSERACT.EXE PATH!

# Set pytesseract to use the specified Tesseract executable
pytesseract.pytesseract.tesseract_cmd = GLOBAL_TESSERACT_CMD
# --- End Configuration ---


# Import your custom modules
from text_extractor import extract_text_from_pdf
from language_detector import detect_language
from summarizer import DocumentSummarizer

from transformers import pipeline # Import pipeline for the translator

# Make sure nltk punkt is downloaded for sent_tokenize
try:
    nltk.data.find('tokenizers/punkt')
except nltk.downloader.DownloadError:
    nltk.download('punkt')

class DocumentTranslator:
    def __init__(self, model_name: str = "Helsinki-NLP/opus-mt-mul-en"):
        """
        Initializes the translation pipeline for translating multiple languages to English.
        """
        try:
            print(f"Loading translation model: {model_name}...")
            self.translator = pipeline("translation", model=model_name)
            print("Translation Model loaded successfully.")
        except Exception as e:
            print(f"Error loading translation model {model_name}: {e}")
            self.translator = None

    def translate_to_english(self, text: str, source_lang: str) -> str:
        """
        Translates text from a source language to English.
        """
        if not self.translator:
            return text # Return original text if translator failed to load

        # Chunking for translation if text is very long (models have input limits)
        MAX_TRANSLATION_CHUNK_CHARS = 1000 # Typical for translation models
        
        translated_parts = []
        sentences = sent_tokenize(text)
        
        current_chunk = []
        current_chunk_char_count = 0

        for sentence in sentences:
            if current_chunk_char_count + len(sentence) + 1 > MAX_TRANSLATION_CHUNK_CHARS and current_chunk:
                chunk_text = " ".join(current_chunk)
                try:
                    translated = self.translator(chunk_text, max_length=MAX_TRANSLATION_CHUNK_CHARS*2)
                    translated_parts.append(translated[0]['translation_text'])
                except Exception as e:
                    print(f"Warning: Failed to translate a chunk. Error: {e}")
                
                current_chunk = [sentence]
                current_chunk_char_count = len(sentence) + 1
            else:
                current_chunk.append(sentence)
                current_chunk_char_count += len(sentence) + 1

        if current_chunk:
            chunk_text = " ".join(current_chunk)
            try:
                translated = self.translator(chunk_text, max_length=MAX_TRANSLATION_CHUNK_CHARS*2)
                translated_parts.append(translated[0]['translation_text'])
            except Exception as e:
                print(f"Warning: Failed to translate final chunk. Error: {e}")
        
        return " ".join(translated_parts).strip()


def main():
    """
    Main function to orchestrate PDF text extraction, language detection, translation (if needed), and summarization.
    """
    # --- Configuration ---
    # This local POPPLER_PATH variable is now using the global one defined at the top
    # No longer set to None, so it correctly passes the path to extract_text_from_pdf
    local_poppler_path_for_main = GLOBAL_POPPLER_PATH


    # Initialize the English summarizer
    print("Initializing document summarizer (English)...")
    summarizer = DocumentSummarizer()

    # Initialize the multilingual translator
    print("Initializing document translator (Multilingual to English)...")
    translator = DocumentTranslator()

    # Check if models loaded successfully
    if not summarizer.summarizer:
        print("Failed to initialize summarization model. Exiting.")
        sys.exit(1)
    if not translator.translator:
        print("Failed to initialize translation model. Non-English summarization may not work. Continuing with English only.")
        # We can decide to exit or continue with limited functionality if translator fails
        # For now, let's allow it to continue but warn.

    print("\n--- PDF Document Summarizer ---")
    print("Enter the path to the PDF file you want to summarize, or type 'exit' to quit.")

    while True:
        pdf_path = input("\nPDF Path: ").strip()

        if pdf_path.lower() == 'exit':
            print("Exiting summarizer.")
            break

        if not os.path.exists(pdf_path):
            print(f"Error: File not found at '{pdf_path}'. Please check the path and try again.")
            continue
        
        if not pdf_path.lower().endswith('.pdf'):
            print("Error: The provided file is not a PDF. Please provide a .pdf file.")
            continue

        print(f"Processing '{os.path.basename(pdf_path)}'...")

        # 1. Text Extraction
        # Pass the global Poppler path here
        extracted_text = extract_text_from_pdf(pdf_path, poppler_path=local_poppler_path_for_main)

        if extracted_text in ["ENCRYPTED_PDF", "CORRUPTED_PDF"]:
            print(f"Processing stopped for '{os.path.basename(pdf_path)}' due to PDF issue.")
            continue
        
        if not extracted_text:
            print(f"Could not extract any meaningful text from '{os.path.basename(pdf_path)}'. Cannot summarize.")
            continue
        
        print(f"Text extraction complete. Total characters: {len(extracted_text)}")

        # 2. Language Detection
        detected_lang = detect_language(extracted_text)
        print(f"Detected Language: {detected_lang}")

        text_to_summarize = extracted_text
        if detected_lang != 'en' and translator.translator:
            print(f"Detected non-English language '{detected_lang}'. Translating to English for summarization...")
            translated_text = translator.translate_to_english(extracted_text, detected_lang)
            if translated_text:
                text_to_summarize = translated_text
                print(f"Translation complete. Translated characters: {len(translated_text)}")
            else:
                print("Translation failed or produced empty text. Attempting summarization of original text.")
                # Fallback: try summarizing original if translation fails
        elif detected_lang != 'en' and not translator.translator:
            print(f"Detected non-English language '{detected_lang}', but translator is not available. Summarizing original text (may not be optimal).")

        # 3. Summarization (always in English now)
        summary = summarizer.generate_summary(
            text_to_summarize,
            min_length=50,
            max_length=200
        )

        print("\n--- Generated Summary ---")
        if summary:
            print(summary)

            # --- Save Summary to File ---
            save_choice = input("\nDo you want to save this summary to a file? (yes/no): ").strip().lower()
            if save_choice == 'yes':
                default_filename = os.path.splitext(os.path.basename(pdf_path))[0] + "_summary.txt"
                output_filename = input(f"Enter filename to save summary (e.g., '{default_filename}'): ").strip()
                if not output_filename:
                    output_filename = default_filename
                
                try:
                    with open(output_filename, 'w', encoding='utf-8') as f:
                        f.write(summary)
                    print(f"Summary saved successfully to '{output_filename}'")
                except IOError as e:
                    print(f"Error saving summary to file '{output_filename}': {e}")
            # --- End Save Feature ---

        else:
            print("Summary generation failed or produced no content.")
        print("-------------------------\n")


if __name__ == "__main__":
    main()