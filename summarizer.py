from transformers import pipeline
import nltk
from nltk.tokenize import sent_tokenize

# Ensure 'punkt' tokenizer data is downloaded for NLTK
try:
    nltk.data.find('tokenizers/punkt')
except nltk.downloader.DownloadError:
    nltk.download('punkt')


class DocumentSummarizer:
    def __init__(self, model_name: str = "sshleifer/distilbart-cnn-12-6"):
        """
        Initializes the summarization pipeline with a pre-trained English summarization model.

        Args:
            model_name (str): The name of the HuggingFace pre-trained summarization model to use.
                              "sshleifer/distilbart-cnn-12-6" is a good English choice.
        """
        try:
            print(f"Loading summarization model: {model_name}...")
            self.summarizer = pipeline("summarization", model=model_name)
            print("Summarization Model loaded successfully.")
        except Exception as e:
            print(f"Error loading summarization model {model_name}: {e}")
            self.summarizer = None # Indicate that the model failed to load

    def generate_summary(self, text: str, min_length: int = 50, max_length: int = 200) -> str:
        """
        Generates a concise summary of the given text using the loaded NLP model.
        Handles long texts by chunking them into smaller pieces and summarizing each chunk.

        Args:
            text (str): The input text to be summarized.
            min_length (int): The minimum length of the generated summary (in tokens).
            max_length (int): The maximum length of the generated summary (in tokens).

        Returns:
            str: The generated summary. Returns an empty string if summarization fails
                 or the model was not loaded.
        """
        if not self.summarizer:
            return "Summarization model not loaded. Cannot generate summary."
        
        if not text or len(text.strip()) < min_length:
            return "Input text is too short to summarize."

        # distilbart-cnn-12-6 has a max input length of 1024 tokens.
        # We'll use a conservative estimate for characters.
        MAX_CHUNK_CHARS = 3000 # Approx 1024 tokens * 3 chars/token
        
        full_summary_parts = []
        sentences = sent_tokenize(text)
        
        current_chunk = []
        current_chunk_char_count = 0

        for sentence in sentences:
            if current_chunk_char_count + len(sentence) + 1 > MAX_CHUNK_CHARS and current_chunk:
                chunk_text = " ".join(current_chunk)
                try:
                    summary = self.summarizer(
                        chunk_text,
                        min_length=min_length,
                        max_length=max_length,
                        do_sample=False
                    )
                    full_summary_parts.append(summary[0]['summary_text'])
                except Exception as e:
                    print(f"Warning: Failed to summarize a chunk. Error: {e}")
                
                current_chunk = [sentence]
                current_chunk_char_count = len(sentence) + 1
            else:
                current_chunk.append(sentence)
                current_chunk_char_count += len(sentence) + 1

        if current_chunk:
            chunk_text = " ".join(current_chunk)
            try:
                summary = self.summarizer(
                    chunk_text,
                    min_length=min_length,
                    max_length=max_length,
                    do_sample=False
                )
                full_summary_parts.append(summary[0]['summary_text'])
            except Exception as e:
                print(f"Warning: Failed to summarize final chunk. Error: {e}")
        
        final_summary = " ".join(full_summary_parts).strip()

        if not final_summary and text.strip():
            if len(text.strip()) < MAX_CHUNK_CHARS and len(text.strip()) >= min_length:
                 try:
                    summary = self.summarizer(
                        text,
                        min_length=min_length,
                        max_length=max_length,
                        do_sample=False
                    )
                    return summary[0]['summary_text']
                 except Exception as e:
                    print(f"Failed to summarize as a single chunk either: {e}")
                    return "Failed to generate summary."
            return "Failed to generate summary due to chunking issues or insufficient content after processing."

        return final_summary