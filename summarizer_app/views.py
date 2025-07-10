import os
import sys
import tempfile
import json
from django.shortcuts import render, redirect
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

# --- Import your core summarizer modules ---
try:
    from text_extractor import TextExtractor
    from language_detector import LanguageDetector
    from summarizer import DocumentSummarizer
    print("Core summarizer modules imported successfully.")
except ImportError as e:
    print(f"Error importing core summarizer modules: {e}")
    # Fallback/error handling if modules aren't found
    TextExtractor = None
    LanguageDetector = None
    DocumentSummarizer = None

# --- Initialize summarizer components globally (or lazily) ---
text_extractor = None
lang_detector = None
doc_summarizer = None

def initialize_summarizer_components():
    global text_extractor, lang_detector, doc_summarizer
    if text_extractor is None:
        try:
            import pytesseract
            pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
            
            text_extractor = TextExtractor(poppler_path=settings.POPPLER_PATH)
            lang_detector = LanguageDetector()
            doc_summarizer = DocumentSummarizer() # This initializes the DocumentSummarizer class
            print("Summarizer components initialized successfully.")
        except Exception as e:
            print(f"Failed to initialize summarizer components: {e}")
            text_extractor = None
            lang_detector = None
            doc_summarizer = None

initialize_summarizer_components()


def upload_pdf(request):
    print("DEBUG: upload_pdf function called.")
    if request.method == 'POST':
        print("DEBUG: Request method is POST.")
        if 'pdf_file' not in request.FILES:
            print("DEBUG: No file uploaded in request.FILES.")
            return render(request, 'summarizer_app/summary.html', {'error_message': 'No file uploaded.'})
        
        uploaded_file = request.FILES['pdf_file']
        print(f"DEBUG: Uploaded file: {uploaded_file.name}, size: {uploaded_file.size} bytes.")
        
        if not uploaded_file.name.lower().endswith('.pdf'):
            print("DEBUG: Invalid file type detected.")
            return render(request, 'summarizer_app/summary.html', {'error_message': 'Invalid file type. Please upload a PDF.'})

        temp_dir = tempfile.gettempdir()
        temp_pdf_path = os.path.join(temp_dir, uploaded_file.name)
        print(f"DEBUG: Temporary PDF path: {temp_pdf_path}")
        
        try:
            with open(temp_pdf_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)
            print("DEBUG: PDF file saved temporarily.")

            summary_text = "Could not generate summary." # Default value
            extracted_text = ""
            error_message = None

            if text_extractor and lang_detector and doc_summarizer:
                print(f"DEBUG: Summarizer components are initialized. Processing PDF: {temp_pdf_path}")
                
                print("DEBUG: Calling text_extractor.extract_text_from_pdf...")
                extracted_text = text_extractor.extract_text_from_pdf(temp_pdf_path)
                print(f"DEBUG: Text extraction completed. Length of extracted text: {len(extracted_text)}.")
                
                if not extracted_text.strip():
                    error_message = "Could not extract any meaningful text from the PDF. It might be empty or unreadable."
                    print(f"DEBUG: {error_message}")
                else:
                    print("DEBUG: Calling lang_detector.detect_language...")
                    detected_lang = lang_detector.detect_language(extracted_text)
                    print(f"DEBUG: Detected Language: {detected_lang}")

                    print("DEBUG: Calling doc_summarizer.generate_summary...")
                    summary_text = doc_summarizer.generate_summary(extracted_text)
                    print(f"DEBUG: Summarization completed. Summary length: {len(summary_text)}.")
            else:
                error_message = "Summarizer core components failed to initialize. Check server logs."
                print(f"DEBUG: {error_message}")

        except Exception as e:
            error_message = f"An error occurred during summarization: {e}"
            print(f"DEBUG: Error during summarization: {e}")
        finally:
            if os.path.exists(temp_pdf_path):
                os.remove(temp_pdf_path)
                print(f"DEBUG: Cleaned up temporary file: {temp_pdf_path}")

        request.session['last_summary'] = summary_text
        request.session['last_filename'] = uploaded_file.name
        print(f"DEBUG: Stored summary in session. 'last_summary' length: {len(request.session.get('last_summary', ''))}")
        print(f"DEBUG: Stored filename in session: {request.session.get('last_filename', 'N/A')}")
        
        if error_message:
            request.session['last_error'] = error_message
            print("DEBUG: Redirecting to display_summary with error.")
            return redirect('display_summary')
        else:
            if not summary_text.strip():
                request.session['last_error'] = "Summary could not be generated. The document might be too short or contain no relevant information."
                print("DEBUG: Redirecting to display_summary with empty summary warning.")
                return redirect('display_summary')
            print("DEBUG: Redirecting to display_summary with successful summary.")
            return redirect('display_summary')

    print("DEBUG: Request method is GET, rendering upload.html.")
    return render(request, 'summarizer_app/upload.html')


def display_summary(request):
    print("DEBUG: display_summary function called.")
    # Changed .pop() to .get() for both summary and filename so they persist for download
    summary = request.session.get('last_summary', 'No summary available.') 
    filename = request.session.get('last_filename', 'N/A') # Changed from .pop() to .get()
    error_message = request.session.pop('last_error', None)

    print(f"DEBUG: Retrieved summary from session. Length: {len(summary)}.")
    print(f"DEBUG: Retrieved filename from session: {filename}.")
    print(f"DEBUG: Retrieved error_message from session: {error_message}.")

    if request.GET.get('download'):
        print("DEBUG: Download requested.")
        if summary and summary != 'No summary available.' and summary.strip():
            print(f"DEBUG: Summary content found for download. Length: {len(summary)}.")
            response = HttpResponse(summary, content_type='text/plain')
            response['Content-Disposition'] = f'attachment; filename="{filename}_summary.txt"'
            return response
        else:
            print("DEBUG: No summary content found for download (after strip check).")
            return render(request, 'summarizer_app/summary.html', {
                'error_message': 'No summary content to download.'
            })

    print("DEBUG: Rendering summary.html.")
    return render(request, 'summarizer_app/summary.html', {
        'summary': summary,
        'filename': filename,
        'error_message': error_message
    })

@csrf_exempt # Temporarily disable CSRF for API endpoints for simpler testing. Re-enable for production!
def expand_summary(request):
    print("DEBUG: expand_summary function called.")
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            current_summary = data.get('summary', '')
            print(f"DEBUG: Expand summary request received. Summary length: {len(current_summary)}")

            if not current_summary.strip():
                print("DEBUG: No summary provided for expansion.")
                return JsonResponse({'error': 'No summary provided to expand.'}, status=400)

            prompt = f"Expand the following summary into a more detailed paragraph, keeping the core meaning:\n\n{current_summary}\n\nExpanded Summary:"
            
            chatHistory = []
            chatHistory.append({ "role": "user", "parts": [{ "text": prompt }] })
            payload = { "contents": chatHistory }
            apiKey = "AIzaSyA6rfbBJkFu31UD4Gn50l2p3G6wKattxIY" # Your provided API Key
            apiUrl = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={apiKey}"

            import requests
            print("DEBUG: Making Gemini API call for expansion...")
            response = requests.post(apiUrl, headers={'Content-Type': 'application/json'}, data=json.dumps(payload))
            response.raise_for_status()
            print("DEBUG: Gemini API call for expansion successful.")
            
            result = response.json()
            
            if result.get('candidates') and len(result['candidates']) > 0 and \
               result['candidates'][0].get('content') and result['candidates'][0]['content'].get('parts') and \
               len(result['candidates'][0]['content']['parts']) > 0:
                expanded_text = result['candidates'][0]['content']['parts'][0]['text']
                print("DEBUG: Expanded text received from Gemini.")
                return JsonResponse({'expanded_summary': expanded_text})
            else:
                print("DEBUG: Gemini API returned invalid response for expansion.")
                return JsonResponse({'error': 'Gemini API did not return a valid response for expansion.'}, status=500)

        except json.JSONDecodeError:
            print("DEBUG: JSONDecodeError in expand_summary.")
            return JsonResponse({'error': 'Invalid JSON in request body.'}, status=400)
        except requests.exceptions.RequestException as e:
            print(f"DEBUG: API request failed in expand_summary: {e}")
            return JsonResponse({'error': f'API request failed: {e}'}, status=500)
        except Exception as e:
            print(f"DEBUG: An unexpected error occurred in expand_summary: {e}")
            return JsonResponse({'error': f'An unexpected error occurred: {e}'}, status=500)
    print("DEBUG: Invalid request method for expand_summary.")
    return JsonResponse({'error': 'Invalid request method.'}, status=405)


@csrf_exempt # Temporarily disable CSRF for API endpoints for simpler testing. Re-enable for production!
def generate_keywords(request):
    print("DEBUG: generate_keywords function called.")
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            current_summary = data.get('summary', '')
            print(f"DEBUG: Generate keywords request received. Summary length: {len(current_summary)}")

            if not current_summary.strip():
                print("DEBUG: No summary provided for keywords generation.")
                return JsonResponse({'error': 'No summary provided to generate keywords from.'}, status=400)

            prompt = f"Extract key keywords or phrases from the following text, separated by commas:\n\n{current_summary}\n\nKeywords:"
            
            chatHistory = []
            chatHistory.append({ "role": "user", "parts": [{ "text": prompt }] })
            payload = { "contents": chatHistory }
            apiKey = "AIzaSyA6rfbBJkFu31UD4Gn50l2p3G6wKattxIY" # Your provided API Key
            apiUrl = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={apiKey}"

            import requests
            print("DEBUG: Making Gemini API call for keywords...")
            response = requests.post(apiUrl, headers={'Content-Type': 'application/json'}, data=json.dumps(payload))
            response.raise_for_status()
            print("DEBUG: Gemini API call for keywords successful.")
            
            result = response.json()
            
            if result.get('candidates') and len(result['candidates']) > 0 and \
               result['candidates'][0].get('content') and result['candidates'][0]['content'].get('parts') and \
               len(result['candidates'][0]['content']['parts']) > 0:
                keywords_text = result['candidates'][0]['content']['parts'][0]['text']
                print("DEBUG: Keywords received from Gemini.")
                return JsonResponse({'keywords': keywords_text})
            else:
                print("DEBUG: Gemini API did not return a valid response for keywords.")
                return JsonResponse({'error': 'Gemini API did not return a valid response for keywords.'}, status=500)

        except json.JSONDecodeError:
            print("DEBUG: JSONDecodeError in generate_keywords.")
            return JsonResponse({'error': 'Invalid JSON in request body.'}, status=400)
        except requests.exceptions.RequestException as e:
            print(f"DEBUG: API request failed in generate_keywords: {e}")
            return JsonResponse({'error': f'API request failed: {e}'}, status=500)
        except Exception as e:
            print(f"DEBUG: An unexpected error occurred in generate_keywords: {e}")
            return JsonResponse({'error': f'An unexpected error occurred: {e}'}, status=500)
    print("DEBUG: Invalid request method for generate_keywords.")
    return JsonResponse({'error': 'Invalid request method.'}, status=405)
