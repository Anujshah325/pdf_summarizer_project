from langdetect import detect, LangDetectException

def detect_language(text: str) -> str:
    """
    Detects the language of the given text efficiently.

    Args:
        text (str): The input text whose language needs to be detected.

    Returns:
        str: The detected language code (e.g., 'en' for English, 'fr' for French).
             Returns 'unknown' if detection fails (e.g., text is too short, or non-linguistic).
    """
    # Langdetect might struggle or raise an exception for very short strings
    # or strings without sufficient linguistic features.
    # A heuristic minimum length check improves efficiency by avoiding unnecessary
    # processing for trivial inputs and prevents common LangDetectException scenarios.
    if not text or len(text.strip()) < 10:
        return "unknown"
    
    try:
        language_code = detect(text)
        return language_code
    except LangDetectException:
        # Catch specific exceptions from langdetect indicating insufficient language data.
        return "unknown"
    except Exception as e:
        # Catch any other unexpected errors during the detection process.
        print(f"An unexpected error occurred during language detection: {e}")
        return "unknown"