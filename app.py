import base64
import os
import io
import time
import datetime # For footer year
import pandas as pd
import math # Potentially needed by pandas implicitly
import random # Import random for adding jitter to backoff
import mimetypes
import zipfile # For creating ZIP archives
import PIL.Image
from io import BytesIO
import uuid
import nltk
from nltk.tokenize import sent_tokenize

from prompts import PROMPT_CATEGORIES

# Try to import the new Google API style
try:
    from google import genai as google_genai
    from google.genai import types as genai_types
    HAS_NEW_GENAI = True
except ImportError:
    HAS_NEW_GENAI = False

from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session, send_from_directory
from dotenv import load_dotenv
import google.generativeai as genai
from google.generativeai import types # For file API status checks
from werkzeug.utils import secure_filename
from config import Config

# Ensure NLTK data is properly downloaded for sentence tokenization
try:
    # Force download the punkt tokenizer data
    print("Downloading NLTK punkt tokenizer data...")
    nltk.download('punkt', quiet=False)
    
    # Verify the download worked by trying to load it
    try:
        nltk.data.find('tokenizers/punkt')
        print("Successfully loaded punkt tokenizer data")
    except LookupError:
        print("Initial download succeeded but verification failed. Trying alternate method...")
        # Try additional download methods if needed
        import ssl
        try:
            _create_unverified_https_context = ssl._create_unverified_context
        except AttributeError:
            pass
        else:
            ssl._create_default_https_context = _create_unverified_https_context
        
        nltk.download('punkt')
        print("Alternate download method completed")
except Exception as e:
    print(f"Error downloading NLTK data: {e}")
    print("NLTK punkt tokenizer might not be available. Story sentence splitting may not work correctly.")

# --- Configuration ---
load_dotenv()  # Load environment variables from .env file

# ** Security: Get API key from environment variable **
API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables. Please set it in the .env file.")

genai.configure(api_key=API_KEY)

# --- Model Selection ---
# Use a model capable of handling various inputs (text, image, video). 1.5 Pro is recommended.
# Ensure your API key has access to the chosen model.
# model_name = "gemini-1.5-flash-latest" # Faster, less capable for complex tasks
model_name1 = "gemini-2.0-flash" # Recommended for full features including video
model_name = "gemini-2.5-pro-exp-03-25" # Good for text, basic image, not video

print(f"Using Gemini Model: {model_name}")

# Allowed file extensions
ALLOWED_EXTENSIONS_IMG = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_EXTENSIONS_PDF = {'pdf'}
ALLOWED_EXTENSIONS_VID = {'mp4', 'mov', 'avi', 'mpeg', 'mpg', 'webm', 'wmv'} # Added wmv
ALLOWED_EXTENSIONS_XLS = {'xlsx', 'xls'} # Excel files

# File Upload Configuration
UPLOAD_FOLDER = 'uploads' # For temporary storage of user uploads
PROCESSED_FOLDER = os.path.join(UPLOAD_FOLDER, 'processed') # For storing generated files before download

# Create upload folders if they don't exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
if not os.path.exists(PROCESSED_FOLDER):
    os.makedirs(PROCESSED_FOLDER)

    


# --- Flask App Setup ---
app = Flask(__name__)
app.config.from_object(Config)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER
# Increased limit for potentially large videos or excel files
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024  # Limit uploads e.g., 1 GB (adjust as needed)
app.secret_key = os.urandom(24) # Needed for flashing messages
app.config['OUTPUT_FOLDER'] = 'outputs'

# Initialize app with config after setting all required folders
Config.init_app(app)

# Create folders if they don't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# --- Helper Functions ---

def allowed_file(filename, allowed_extensions):
    """Checks if the uploaded file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def upload_file_to_gemini(filepath, mime_type=None):
    """
    Uploads a file to the Gemini API Files service and waits for it to become ACTIVE.
    Handles PROCESSING, FAILED states, and includes a timeout.
    Returns the file object if successful, None otherwise.
    """
    print(f"Uploading file to Gemini: {filepath}")
    try:
        file = genai.upload_file(path=filepath, mime_type=mime_type)
        print(f"Uploaded file '{file.display_name}' as: {file.name} ({file.uri}). Initial State: {file.state.name}")

        processing_start_time = time.time()
        processing_timeout_seconds = 600 # 10 minutes timeout for Gemini processing

        while file.state.name == "PROCESSING":
            print(f"Processing file... (URI: {file.name}) Elapsed: {time.time() - processing_start_time:.0f}s")
            time.sleep(10) # Check status every 10 seconds
            file = genai.get_file(file.name) # Get updated status

            if time.time() - processing_start_time > processing_timeout_seconds:
                 print(f"File processing timed out after {processing_timeout_seconds} seconds. URI: {file.name}")
                 try:
                     genai.delete_file(file.name)
                     print(f"Attempted to delete timed-out Gemini file: {file.name}")
                 except Exception as del_e:
                     print(f"Could not delete timed-out Gemini file {file.name}: {del_e}")
                 return None # Indicate timeout failure

        if file.state.name == "FAILED":
            print(f"Gemini file processing failed. URI: {file.name}, State Details: {file.state}")
            try:
                genai.delete_file(file.name)
                print(f"Deleted failed Gemini file resource: {file.name}")
            except Exception as del_e:
                print(f"Could not delete failed Gemini file {file.name}: {del_e}")
            return None # Indicate failure

        if file.state.name != "ACTIVE":
             print(f"File is not active after processing. State: {file.state.name}. URI: {file.name}")
             # Optional: Delete if not active? Depends on policy.
             # delete_gemini_file(file) # Consider uncommenting if non-ACTIVE states should be cleaned up
             return None # Indicate non-active state failure

        print(f"File is ACTIVE and ready: {file.uri}")
        return file

    except Exception as e:
        print(f"Error during file upload/processing for {filepath} with Gemini: {e}")
        # If a file object exists from upload attempt but failed during status checks, try deleting
        if 'file' in locals() and hasattr(file, 'name'):
             try:
                 genai.delete_file(file.name)
                 print(f"Attempted delete on Gemini file due to exception during processing: {file.name}")
             except Exception as del_e:
                  print(f"Could not delete Gemini file {file.name} after exception: {del_e}")
        return None # Indicate failure


def delete_gemini_file(file_obj):
    """Safely deletes a file from the Gemini API Files service."""
    if file_obj and hasattr(file_obj, 'name'):
        try:
            print(f"Attempting to delete Gemini file: {file_obj.name}")
            genai.delete_file(file_obj.name)
            print(f"Successfully deleted Gemini file: {file_obj.name}")
        except Exception as e:
            # Log error but don't crash the app
            print(f"Error deleting Gemini file {file_obj.name}: {e}")
    else:
        print("No valid Gemini file object provided for deletion.")


# --- Context processor to add year to footer ---
@app.context_processor
def inject_now():
    """Injects current UTC time into templates."""
    return {'now': datetime.datetime.utcnow()}


# --- Flask Routes ---

@app.route('/')
def index():
    """Renders the main grid page."""
    return render_template('index.html')

# --- 1. Text Generation (Modified) ---
@app.route('/feature/text', methods=['GET', 'POST'])
def feature_text():
    """Handles text prompt input and displays result on the same page. Includes Prompt Library."""
    if request.method == 'POST':
        prompt = request.form.get('prompt_text')
        if not prompt:
            flash('Please enter a text prompt.', 'error')
            # Pass prompts data even on error postback
            return render_template('feature_text.html', prompts_data=PROMPT_CATEGORIES)

        try:
            print(f"Generating text for prompt: {prompt[:100]}...")
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            result_text = response.text
            print("Text generation successful.")
            # Pass prompts data along with results
            return render_template('feature_text.html',
                                   prompt=prompt,
                                   result=result_text,
                                   prompts_data=PROMPT_CATEGORIES)

        except Exception as e:
            error_message = f"An error occurred during text generation: {e}"
            print(error_message)
            if "API key not valid" in str(e): error_message = "API key is invalid."
            elif "quota" in str(e).lower(): error_message = "API quota exceeded."
            flash(error_message, 'error')
            # Pass prompts data and preserve submitted prompt on error
            return render_template('feature_text.html',
                                   prompt=prompt,
                                   prompts_data=PROMPT_CATEGORIES)

    # GET request: show the empty form and pass prompt data
    return render_template('feature_text.html', prompts_data=PROMPT_CATEGORIES)


# --- 2. PDF Interaction ---
@app.route('/feature/pdf', methods=['GET', 'POST'])
def feature_pdf():
    """Handles PDF upload and prompt, shows result on the same page."""
    if request.method == 'POST':
        prompt = request.form.get('prompt_pdf')
        file = request.files.get('file_pdf')
        original_filename = None
        local_filepath = None # Renamed for clarity
        gemini_file = None

        # Validation
        if not prompt: flash('Please enter a prompt for the PDF.', 'error'); return render_template('feature_pdf.html', prompts_data=PROMPT_CATEGORIES)
        if not file or file.filename == '': flash('No PDF file selected.', 'error'); return render_template('feature_pdf.html', prompt=prompt, prompts_data=PROMPT_CATEGORIES)
        if not allowed_file(file.filename, ALLOWED_EXTENSIONS_PDF): flash('Invalid file type. Please upload a PDF.', 'error'); return render_template('feature_pdf.html', prompt=prompt, prompts_data=PROMPT_CATEGORIES)

        try:
            original_filename = secure_filename(file.filename)
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"{timestamp}-{original_filename}"
            local_filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            file.save(local_filepath)
            print(f"PDF saved locally: {local_filepath}")

            # Upload local file to Gemini Files API
            gemini_file = upload_file_to_gemini(local_filepath, mime_type='application/pdf')
            if not gemini_file:
                flash('Failed to upload or process PDF file with Gemini. Check logs.', 'error')
                raise ValueError("Gemini file upload/processing failed.") # Go to finally for cleanup

            print(f"Generating content for PDF '{original_filename}' with prompt: {prompt[:50]}...")
            model = genai.GenerativeModel(model_name)
            response = model.generate_content([prompt, gemini_file]) # Pass file obj

            result_text = response.text
            print("PDF content generation successful.")

            return render_template('feature_pdf.html', prompt=prompt, result=result_text, filename=original_filename, prompts_data=PROMPT_CATEGORIES)

        except Exception as e:
            error_message = f"An error occurred processing the PDF: {e}"
            print(error_message)
            flash(error_message, 'error')
            # Render form again, preserving prompt
            return render_template('feature_pdf.html', prompt=prompt, prompts_data=PROMPT_CATEGORIES)

        finally:
            # Clean up local file regardless of success/failure
            if local_filepath and os.path.exists(local_filepath):
                try:
                    os.remove(local_filepath)
                    print(f"Removed temporary local file: {local_filepath}")
                except Exception as e:
                    print(f"Warning: Could not remove temporary file {local_filepath}: {e}")

            # Clean up Gemini file if it exists and we had an error
            if gemini_file and 'error_message' in locals():
                delete_gemini_file(gemini_file)

    # GET request: show the empty form and pass prompt data
    return render_template('feature_pdf.html', prompts_data=PROMPT_CATEGORIES)


# --- 3. Image Interaction ---
@app.route('/feature/image', methods=['GET', 'POST'])
def feature_image():
    """Handles Image upload and prompt, shows result on the same page."""
    if request.method == 'POST':
        prompt = request.form.get('prompt_image')
        file = request.files.get('file_image')
        original_filename = None
        local_filepath = None
        gemini_file = None

        # Validation
        if not prompt: flash('Please enter a prompt for the image.', 'error'); return render_template('feature_image.html', prompts_data=PROMPT_CATEGORIES)
        if not file or file.filename == '': flash('No image file selected.', 'error'); return render_template('feature_image.html', prompt=prompt, prompts_data=PROMPT_CATEGORIES)
        if not allowed_file(file.filename, ALLOWED_EXTENSIONS_IMG): flash(f'Invalid file type. Allowed: {", ".join(ALLOWED_EXTENSIONS_IMG)}', 'error'); return render_template('feature_image.html', prompt=prompt, prompts_data=PROMPT_CATEGORIES)

        try:
            original_filename = secure_filename(file.filename)
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"{timestamp}-{original_filename}"
            local_filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(local_filepath)
            print(f"Image saved locally: {local_filepath}")

            gemini_file = upload_file_to_gemini(local_filepath) # Let Gemini detect mime type
            if not gemini_file:
                flash('Failed to upload or process image file with Gemini. Check logs.', 'error')
                raise ValueError("Gemini file upload/processing failed.")

            print(f"Generating content for Image '{original_filename}' with prompt: {prompt[:50]}...")
            model = genai.GenerativeModel(model_name) # 1.5 models handle vision
            response = model.generate_content([prompt, gemini_file])

            result_text = response.text
            print("Image content generation successful.")

            return render_template('feature_image.html', prompt=prompt, result=result_text, filename=original_filename, prompts_data=PROMPT_CATEGORIES)

        except Exception as e:
            error_message = f"An error occurred processing the image: {e}"
            if "does not support image input" in str(e).lower() or "multimodal capabilities" in str(e).lower():
                error_message = f"Model '{model_name}' may not support image input. Try 'gemini-1.5-pro-latest' or 'gemini-1.5-flash-latest'."
            print(error_message)
            flash(error_message, 'error')
            return render_template('feature_image.html', prompt=request.form.get('prompt_image'), prompts_data=PROMPT_CATEGORIES)

        finally:
            # Cleanup local temp file AND Gemini file resource
            if local_filepath and os.path.exists(local_filepath):
                try: os.remove(local_filepath); print(f"Removed local file: {local_filepath}")
                except Exception as e_rem: print(f"Error removing local file {local_filepath}: {e_rem}")
            if gemini_file:
                delete_gemini_file(gemini_file)

    # GET request
    return render_template('feature_image.html', prompts_data=PROMPT_CATEGORIES)


# --- 4. Video Interaction ---
@app.route('/feature/video', methods=['GET', 'POST'])
def feature_video():
    """Handles Video upload and prompt, shows result on the same page."""
    if request.method == 'POST':
        prompt = request.form.get('prompt_video')
        file = request.files.get('file_video')
        original_filename = None
        local_filepath = None
        gemini_file = None

        # Validation
        if not prompt: flash('Please enter a prompt for the video.', 'error'); return render_template('feature_video.html', prompts_data=PROMPT_CATEGORIES)
        if not file or file.filename == '': flash('No video file selected.', 'error'); return render_template('feature_video.html', prompt=prompt, prompts_data=PROMPT_CATEGORIES)
        if not allowed_file(file.filename, ALLOWED_EXTENSIONS_VID): flash(f'Invalid file type. Allowed: {", ".join(ALLOWED_EXTENSIONS_VID)}', 'error'); return render_template('feature_video.html', prompt=prompt, prompts_data=PROMPT_CATEGORIES)

        try:
            original_filename = secure_filename(file.filename)
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"{timestamp}-{original_filename}"
            local_filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(local_filepath)
            file_size_mb = os.path.getsize(local_filepath) / (1024*1024)
            print(f"Video saved locally: {local_filepath}, Size: {file_size_mb:.2f} MB")

            print("Starting video upload/processing with Gemini (can take minutes)...")
            gemini_file = upload_file_to_gemini(local_filepath) # Let Gemini detect mime type
            if not gemini_file:
                flash('Failed to upload or process video file with Gemini. Check logs. This can take time.', 'error')
                raise ValueError("Gemini file upload/processing failed.")

            print(f"Video processed. Generating content for '{original_filename}' with prompt: {prompt[:50]}...")
            model = genai.GenerativeModel(model_name) # Ensure model supports video (e.g., 1.5 Pro)
            response = model.generate_content([prompt, gemini_file])

            result_text = response.text
            print("Video content generation successful.")

            return render_template('feature_video.html', prompt=prompt, result=result_text, filename=original_filename, prompts_data=PROMPT_CATEGORIES)

        except Exception as e:
            error_message = f"An error occurred processing the video: {e}"
            if "doesn't have video capabilities" in str(e).lower() or "multimodal capabilities" in str(e).lower():
                error_message = f"Model may not support video input. Try 'gemini-1.5-pro-latest'."
            elif "Deadline Exceeded" in str(e) or "504" in str(e):
                 error_message = f"Request timed out processing video. Try a shorter clip or check Gemini status."
            print(error_message)
            flash(error_message, 'error')
            return render_template('feature_video.html', prompt=request.form.get('prompt_video'), prompts_data=PROMPT_CATEGORIES)

        finally:
            # Cleanup local temp file AND Gemini file resource
            if local_filepath and os.path.exists(local_filepath):
                try: os.remove(local_filepath); print(f"Removed local file: {local_filepath}")
                except Exception as e_rem: print(f"Error removing local file {local_filepath}: {e_rem}")
            if gemini_file:
                delete_gemini_file(gemini_file)

    # GET request
    return render_template('feature_video.html', prompts_data=PROMPT_CATEGORIES)


# --- 5. Excel AI Prompter (Summary) ---
@app.route('/feature/excel', methods=['GET', 'POST'])
def feature_excel():
    """Handles Excel upload, extracts text, sends to Gemini for summary/insights."""
    if request.method == 'POST':
        prompt = request.form.get('prompt_excel')
        file = request.files.get('file_excel')
        original_filename = None
        local_filepath = None

        # Validation
        if not prompt: flash('Please enter a prompt for the Excel file.', 'error'); return render_template('feature_excel.html', prompts_data=PROMPT_CATEGORIES)
        if not file or file.filename == '': flash('No Excel file selected.', 'error'); return render_template('feature_excel.html', prompt=prompt, prompts_data=PROMPT_CATEGORIES)
        if not allowed_file(file.filename, ALLOWED_EXTENSIONS_XLS): flash(f'Invalid file type. Allowed: {", ".join(ALLOWED_EXTENSIONS_XLS)}', 'error'); return render_template('feature_excel.html', prompt=prompt, prompts_data=PROMPT_CATEGORIES)

        try:
            original_filename = secure_filename(file.filename)
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"{timestamp}-{original_filename}"
            local_filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(local_filepath)
            print(f"Excel file saved locally: {local_filepath}")

            # Read Excel Content using Pandas
            excel_data_string = ""
            max_chars_to_read = 150000 # Increased limit slightly
            try:
                xls = pd.ExcelFile(local_filepath)
                temp_string = io.StringIO()
                temp_string.write(f"Summary of Excel file '{original_filename}':\n")
                total_chars = len(temp_string.getvalue())

                for sheet_name in xls.sheet_names:
                    if total_chars >= max_chars_to_read: temp_string.write("\n[Data truncated]"); break
                    df = pd.read_excel(xls, sheet_name=sheet_name)
                    sheet_csv = df.to_csv(index=False, lineterminator='\n')
                    sheet_header = f"\n--- Sheet: {sheet_name} ---\n"
                    chars_to_add = len(sheet_header) + len(sheet_csv)

                    if total_chars + chars_to_add <= max_chars_to_read:
                        temp_string.write(sheet_header)
                        temp_string.write(sheet_csv)
                        total_chars += chars_to_add
                    else:
                         remaining_chars = max_chars_to_read - total_chars
                         if remaining_chars > len(sheet_header) + 50: # Need space for header + some data
                            temp_string.write(sheet_header)
                            temp_string.write(sheet_csv[:remaining_chars - len(sheet_header) - 1])
                         temp_string.write("\n[Data truncated]")
                         break

                excel_data_string = temp_string.getvalue()
                temp_string.close()
                print(f"Extracted data from Excel (approx {len(excel_data_string)} chars).")
            except Exception as read_e:
                print(f"Error reading Excel file {local_filepath}: {read_e}")
                flash(f"Could not read the Excel file. Error: {read_e}", 'error')
                raise # Trigger cleanup

            # Generate Content using Gemini with extracted text
            combined_prompt = f"User Prompt: {prompt}\n\nData from the uploaded Excel file:\n```csv\n{excel_data_string}\n```"
            print(f"Generating content based on Excel data and prompt: {prompt[:50]}...")
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(combined_prompt)
            result_text = response.text
            print("Excel-based content generation successful.")

            return render_template('feature_excel.html', prompt=prompt, result=result_text, filename=original_filename, prompts_data=PROMPT_CATEGORIES)

        except Exception as e:
            error_message = f"An error occurred processing the Excel file request: {e}"
            print(error_message)
            flash(error_message, 'error')
            return render_template('feature_excel.html', prompt=request.form.get('prompt_excel'), prompts_data=PROMPT_CATEGORIES)

        finally:
            # Cleanup: Only remove the local temp file
            if local_filepath and os.path.exists(local_filepath):
                try: os.remove(local_filepath); print(f"Removed local Excel file: {local_filepath}")
                except Exception as e_rem: print(f"Error removing local file {local_filepath}: {e_rem}")

    # GET request
    return render_template('feature_excel.html', prompts_data=PROMPT_CATEGORIES)


# --- 6. Modified AGAIN: Excel Row-by-Row AI Processor with Retry Logic ---
@app.route('/feature/excel_row', methods=['GET', 'POST'])
def feature_excel_row():
    """
    Handles Excel upload, processes specified column row by row with a prompt,
    retries on 429 errors, saves results to a new Excel file, provides download link.
    """
    if request.method == 'POST':
        prompt_template = request.form.get('prompt_excel_row')
        input_column_name = request.form.get('input_column_name')
        file = request.files.get('file_excel_row')
        original_filename = None
        input_filepath = None
        output_filename = None
        output_filepath = None

        # Validation (keep existing)
        if not prompt_template: flash('Please enter a prompt template.', 'error'); return render_template('feature_excel_row.html', prompts_data=PROMPT_CATEGORIES)
        # ... (rest of validation) ...
        if not file or file.filename == '': flash('No Excel file selected.', 'error'); return render_template('feature_excel_row.html', prompt_template=prompt_template, input_column_name=input_column_name, prompts_data=PROMPT_CATEGORIES)
        if not allowed_file(file.filename, ALLOWED_EXTENSIONS_XLS): flash(f'Invalid file type. Allowed: {", ".join(ALLOWED_EXTENSIONS_XLS)}', 'error'); return render_template('feature_excel_row.html', prompt_template=prompt_template, input_column_name=input_column_name, prompts_data=PROMPT_CATEGORIES)

        try:
            original_filename = secure_filename(file.filename)
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            temp_input_filename = f"{timestamp}-temp-{original_filename}"
            input_filepath = os.path.join(app.config['UPLOAD_FOLDER'], temp_input_filename)
            file.save(input_filepath)
            print(f"[INFO] Temporary input Excel file saved: {input_filepath}")

            # Read Excel
            try:
                df = pd.read_excel(input_filepath, sheet_name=0) # Process first sheet
                if input_column_name not in df.columns:
                    flash(f"Error: Column '{input_column_name}' not found. Available: {', '.join(df.columns)}", 'error')
                    raise ValueError(f"Input column '{input_column_name}' not found.")
                print(f"[INFO] Successfully read Excel. Columns: {df.columns.tolist()}. Rows: {len(df)}")
            except Exception as read_e:
                flash(f"Could not read Excel file (Sheet 1) or column not found. Error: {read_e}", 'error')
                raise # Trigger cleanup

            # Process Rows with Retry Logic
            results_ai_output = []
            results_original_input = []
            model = genai.GenerativeModel(model_name1)
            total_rows = len(df)
            print(f"\n[INFO] Starting row-by-row processing for {total_rows} rows...")
            print("-" * 30)

            # Retry configuration
            MAX_RETRIES = 7
            INITIAL_RETRY_DELAY_SECONDS = 5 # Start delay at 5 seconds
            MAX_RETRY_DELAY_SECONDS = 60    # Cap delay at 60 seconds

            for index, row in df.iterrows():
                row_input_text = row[input_column_name]
                if pd.isna(row_input_text) or not isinstance(row_input_text, str):
                    row_input_text = str(row_input_text) if not pd.isna(row_input_text) else ""

                # --- Log Start of Row Processing ---
                print(f"[ROW {index + 1}/{total_rows}] Processing Input: '{str(row_input_text)[:70]}...'")
                results_original_input.append(row_input_text)

                if not row_input_text.strip():
                    print(f"[ROW {index + 1}/{total_rows}] Skipping API call (empty input).")
                    results_ai_output.append("[skipped_empty_input]")
                    print("-" * 30) # Separator for next row
                    continue # Move to next row immediately

                # --- API Call with Retry Loop ---
                retries = 0
                current_delay = INITIAL_RETRY_DELAY_SECONDS
                while True: # Loop for retries on the current row
                    try:
                        if retries > 0:
                            print(f"[ROW {index + 1}/{total_rows}] Retry {retries}/{MAX_RETRIES}...")

                        combined_row_prompt = f"User Prompt: {prompt_template}\n\nInput Text from Excel Row: {row_input_text}"
                        response = model.generate_content(combined_row_prompt)
                        ai_result = response.text
                        results_ai_output.append(ai_result)
                        print(f"[ROW {index + 1}/{total_rows}] API Success. Output: '{ai_result[:70]}...'")
                        break # Success, exit retry loop for this row

                    except Exception as api_e:
                        error_str = str(api_e).lower()
                        # --- Check for Quota Error (429) ---
                        if "429" in error_str or "quota" in error_str or "resource has been exhausted" in error_str:
                            retries += 1
                            if retries > MAX_RETRIES:
                                print(f"[ROW {index + 1}/{total_rows}] ERROR: Max retries ({MAX_RETRIES}) exceeded for quota error.")
                                error_msg = f"[API_ERROR: Max retries exceeded - {str(api_e)[:100]}]"
                                results_ai_output.append(error_msg)
                                break # Exit retry loop, record error
                            else:
                                # Apply exponential backoff with jitter
                                wait_time = current_delay + random.uniform(0, 1) # Add jitter
                                print(f"[ROW {index + 1}/{total_rows}] WARNING: Quota error (429) detected. Retrying in {wait_time:.1f} seconds (Attempt {retries}/{MAX_RETRIES})...")
                                time.sleep(wait_time)
                                # Increase delay for next time, cap it
                                current_delay = min(current_delay * 2, MAX_RETRY_DELAY_SECONDS)
                                # Continue to the next iteration of the retry loop
                        else:
                            # --- Handle Other API Errors ---
                            print(f"[ROW {index + 1}/{total_rows}] ERROR: Non-retryable API error: {api_e}")
                            error_msg = f"[API_ERROR: {str(api_e)[:100]}]"
                            results_ai_output.append(error_msg)
                            break # Exit retry loop for non-quota errors
                # --- End API Call Retry Loop ---
                print("-" * 30) # Separator for next row

            print(f"\n[INFO] Finished processing all {total_rows} rows.")

            # Create Output DataFrame
            print("[INFO] Creating output DataFrame...")
            output_df = pd.DataFrame({
                'AI Output': results_ai_output,
                f'Original Text ({input_column_name})': results_original_input
            })
            # Optional: Add to original df instead
            # df['AI_Output'] = results_ai_output; output_df = df

            # Save Output Excel Locally
            output_filename = f"{timestamp}-{os.path.splitext(original_filename)[0]}_processed.xlsx"
            output_filepath = os.path.join(PROCESSED_FOLDER, output_filename)
            output_df.to_excel(output_filepath, index=False, engine='openpyxl')
            print(f"[INFO] Processed file saved locally: {output_filepath}")

            # Signal Completion and Provide Download Link
            success_message = f"Processing complete for {total_rows} rows. Click the link below to download."
            print(f"[INFO] Rendering template with success message and download link for {output_filename}")
            return render_template('feature_excel_row.html',
                                   prompt_template=prompt_template,
                                   input_column_name=input_column_name,
                                   processed_filename=output_filename,
                                   success_message=success_message,
                                   prompts_data=PROMPT_CATEGORIES)

        except Exception as e:
            # General error handling
            error_message = f"An error occurred during row-by-row processing: {e}"
            print(f"[ERROR] Overall processing failed: {error_message}") # Log the error
            flash(error_message, 'error')
            return render_template('feature_excel_row.html',
                                   prompt_template=request.form.get('prompt_excel_row'),
                                   input_column_name=request.form.get('input_column_name'),
                                   prompts_data=PROMPT_CATEGORIES)

        finally:
            # Cleanup: ONLY remove the temporary INPUT file
            if input_filepath and os.path.exists(input_filepath):
                try:
                    os.remove(input_filepath)
                    print(f"[INFO] Removed temporary INPUT file: {input_filepath}")
                except Exception as e_rem:
                    print(f"[ERROR] Failed to remove temp input file {input_filepath}: {e_rem}")
            # The processed file in PROCESSED_FOLDER remains for download

    # GET request
    return render_template('feature_excel_row.html', prompts_data=PROMPT_CATEGORIES)


# --- 7. Image Generation ---
@app.route('/feature/image_generation', methods=['GET', 'POST'])
def feature_image_generation():
    """Handles text prompt input and generates AI images using Gemini API."""
    if request.method == 'POST':
        prompt = request.form.get('prompt_text')
        num_images = int(request.form.get('num_images', 1))
        
        # Validate inputs
        if not prompt:
            flash('Please enter a text prompt.', 'error')
            return render_template('feature_image_generation.html', prompts_data=PROMPT_CATEGORIES)
        
        if num_images < 1 or num_images > 12:
            flash('Number of images must be between 1 and 12.', 'error')
            return render_template('feature_image_generation.html', prompt=prompt, prompts_data=PROMPT_CATEGORIES)
        
        try:
            # Create generated directory if it doesn't exist
            generated_folder = os.path.join('static', 'generated')
            if not os.path.exists(generated_folder):
                os.makedirs(generated_folder)
            
            image_files = []
            
            # Get API key from environment variable
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                flash('GEMINI_API_KEY not found in environment variables.', 'error')
                return render_template('feature_image_generation.html', prompt=prompt, prompts_data=PROMPT_CATEGORIES)
            
            # Check if we have access to the new API style with Client
            if HAS_NEW_GENAI:
                # Initialize the client
                client = google_genai.Client(api_key=api_key)
                model_name_image = "gemini-2.0-flash-exp-image-generation"
                
                # Generate images
                for i in range(num_images):
                    timestamp = time.strftime("%Y%m%d-%H%M%S")
                    file_name = f"generated_{timestamp}_{i+1}"
                    
                    try:
                        print(f"Generating image {i+1} of {num_images}...")
                        
                        # Create content structure
                        contents = [
                            genai_types.Content(
                                role="user",
                                parts=[
                                    genai_types.Part.from_text(text=prompt),
                                ],
                            ),
                        ]
                        
                        # Configure generation parameters
                        generate_content_config = genai_types.GenerateContentConfig(
                            response_modalities=[
                                "image",
                                "text",
                            ],
                            response_mime_type="text/plain",
                        )
                        
                        # Generate image using the streaming API
                        response_stream = client.models.generate_content_stream(
                            model=model_name_image,
                            contents=contents,
                            config=generate_content_config,
                        )
                        
                        # Process the full response stream to ensure everything is read
                        try:
                            for chunk in response_stream:
                                if (
                                    chunk.candidates is None
                                    or chunk.candidates[0].content is None
                                    or chunk.candidates[0].content.parts is None
                                ):
                                    continue
                                    
                                # Check if the response contains image data
                                if chunk.candidates[0].content.parts[0].inline_data:
                                    # Extract image data
                                    inline_data = chunk.candidates[0].content.parts[0].inline_data
                                    data_buffer = inline_data.data
                                    file_extension = mimetypes.guess_extension(inline_data.mime_type)
                                    
                                    if not file_extension:
                                        file_extension = ".jpg"  # Default to jpg
                                    
                                    # Save the image
                                    image_path = os.path.join(generated_folder, f"{file_name}{file_extension}")
                                    with open(image_path, "wb") as f:
                                        f.write(data_buffer)
                                    
                                    # Add to list of generated images
                                    image_files.append(os.path.basename(image_path))
                                    print(f"Image saved to {image_path}")
                                else:
                                    # If we get text instead of image
                                    if hasattr(chunk, 'text') and chunk.text:
                                        print(f"Text response: {chunk.text}")
                        except Exception as stream_error:
                            print(f"Error processing response stream: {stream_error}")
                            # Make sure to fully consume the stream even on error
                            try:
                                # Exhaust the stream to avoid "Response not read" errors
                                for _ in response_stream:
                                    pass
                            except Exception as exhaust_error:
                                print(f"Error exhausting stream: {exhaust_error}")
                            raise stream_error  # Re-raise the original error
                        
                    except Exception as e:
                        print(f"Error generating image {i+1}: {e}")
                        flash(f'Error generating image {i+1}: {str(e)}', 'error')
                
                # If we successfully generated at least one image
                if image_files:
                    session['generated_images'] = image_files
                    return render_template('feature_image_generation.html', 
                                         prompt=prompt,
                                         image_files=image_files,
                                         prompts_data=PROMPT_CATEGORIES)
                else:
                    flash('No images were generated. Please try a different prompt.', 'error')
                    return render_template('feature_image_generation.html', 
                                         prompt=prompt,
                                         prompts_data=PROMPT_CATEGORIES)
            else:
                # If the required Client class is not available, fall back to text generation
                flash('The required modules for image generation are not available. Falling back to text descriptions.', 'error')
                
                # Fall back to text description generation
                model_name2 = "gemini-2.5-pro-exp-03-25"  # Standard model for text
                model = genai.GenerativeModel(model_name2)
                
                # Generate text descriptions instead
                result_text = None
                for i in range(1):  # Just generate one description
                    image_prompt = f"Create a detailed artistic description of this image: {prompt}. Include details about style, colors, composition, and mood."
                    response = model.generate_content(image_prompt)
                    result_text = response.text
                
                return render_template('feature_image_generation.html', 
                                      prompt=prompt,
                                      result=result_text,
                                      prompts_data=PROMPT_CATEGORIES)
                
        except Exception as e:
            error_message = f"An error occurred during image generation: {e}"
            print(error_message)
            flash(error_message, 'error')
            return render_template('feature_image_generation.html', 
                                  prompt=prompt,
                                  prompts_data=PROMPT_CATEGORIES)
    
    # GET request: show the empty form with prompts data
    return render_template('feature_image_generation.html', prompts_data=PROMPT_CATEGORIES)

@app.route('/download_image/<filename>')
def download_image(filename):
    """Downloads a single generated image."""
    image_path = os.path.join('static', 'generated', filename)
    if not os.path.exists(image_path):
        flash('Image file not found.', 'error')
        return redirect(url_for('feature_image_generation'))
    
    return send_file(image_path, as_attachment=True)

@app.route('/download_all_images')
def download_all_images():
    """Downloads all generated images as a ZIP file."""
    # Get image files from session
    image_files = session.get('generated_images', [])
    
    if not image_files:
        flash('No images to download.', 'error')
        return redirect(url_for('feature_image_generation'))
    
    # Create a ZIP file
    zip_filename = f"generated_images_{time.strftime('%Y%m%d-%H%M%S')}.zip"
    zip_path = os.path.join(app.config['PROCESSED_FOLDER'], zip_filename)
    
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for img in image_files:
            img_path = os.path.join('static', 'generated', img)
            if os.path.exists(img_path):
                zipf.write(img_path, os.path.basename(img_path))
    
    return send_file(zip_path, as_attachment=True, download_name=zip_filename)

# --- End of Image Generation Routes ---

# --- 8. Image Editor ---
@app.route('/feature/image_editor', methods=['GET', 'POST'])
def feature_image_editor():
    if request.method == 'POST':
        # Get form inputs
        prompt = request.form.get('prompt_text', '')
        files = request.files.getlist('file_images')
        
        # Validate inputs
        if not prompt:
            flash('Please provide editing instructions', 'error')
            return render_template('feature_image_editor.html', prompts_data=PROMPT_CATEGORIES)
        
        if not files or files[0].filename == '':
            flash('Please upload at least one image', 'error')
            return render_template('feature_image_editor.html', prompts_data=PROMPT_CATEGORIES)
        
        # Limit to maximum 100 files
        if len(files) > 100:
            flash('Maximum 100 images allowed, processing the first 100', 'warning')
            files = files[:100]
        
        # Validate file types
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
        for file in files:
            if not allowed_file(file.filename, allowed_extensions):
                flash(f'File {file.filename} has an invalid extension. Allowed extensions: {", ".join(allowed_extensions)}', 'error')
                return render_template('feature_image_editor.html', prompts_data=PROMPT_CATEGORIES)
        
        # Create output directory if it doesn't exist
        output_dir = os.path.join(app.static_folder, 'edited')
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Save images temporarily
        timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        saved_files = []
        for i, file in enumerate(files):
            # Generate a unique filename
            filename = secure_filename(file.filename)
            base, ext = os.path.splitext(filename)
            unique_filename = f"{base}_{timestamp}_{i}{ext}"
            filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
            
            # Save the file
            file.save(filepath)
            saved_files.append(filepath)
        
        # Process images with Gemini AI
        edited_images = []
        errors = []
        
        try:
            # Check if we have access to the new API style
            if HAS_NEW_GENAI:
                # Initialize the client
                client = google_genai.Client(api_key=API_KEY)
                # Use the image generation model explicitly
                model_name_edit = "gemini-2.0-flash-exp-image-generation"
                
                for i, file_path in enumerate(saved_files):
                    try:
                        print(f"Processing image {i+1}/{len(saved_files)}: {os.path.basename(file_path)}")
                        
                        # Open the image with PIL
                        image = PIL.Image.open(file_path)
                        
                        # Format prompt as tuple to match example code
                        text_input = (f"Edit this image: {prompt}",)
                        
                        # Set explicit response modalities to ensure we get back image data
                        generation_config = genai_types.GenerateContentConfig(
                            response_modalities=['TEXT', 'IMAGE']
                        )
                        
                        # Use streaming API for more reliable response handling
                        try:
                            response_stream = client.models.generate_content_stream(
                                model=model_name_edit,
                                contents=[text_input, image],
                                config=generation_config
                            )
                            
                            # Process the response stream
                            output_image_data = None
                            output_text = ""
                            
                            for chunk in response_stream:
                                if hasattr(chunk, 'text') and chunk.text:
                                    output_text += chunk.text
                                
                                # Process candidates if available
                                if (hasattr(chunk, 'candidates') and chunk.candidates and 
                                    chunk.candidates[0].content and chunk.candidates[0].content.parts):
                                    for part in chunk.candidates[0].content.parts:
                                        if hasattr(part, 'text') and part.text is not None:
                                            output_text += part.text
                                        elif hasattr(part, 'inline_data') and part.inline_data is not None:
                                            output_image_data = part.inline_data.data
                                            print(f"Found image data in response")
                            
                            # Print text response summary if available
                            if output_text:
                                print(f"Text response: {output_text[:100]}...")
                                
                        except Exception as stream_error:
                            print(f"Error processing response stream: {stream_error}")
                            # Make sure to fully consume the stream even on error
                            try:
                                # Exhaust the stream to avoid "Response not read" errors
                                if 'response_stream' in locals():
                                    for _ in response_stream:
                                        pass
                            except Exception as exhaust_error:
                                print(f"Error exhausting stream: {exhaust_error}")
                            raise Exception(f"Stream error: {stream_error}")
                        
                        if output_image_data:
                            # Create output filename
                            base, ext = os.path.splitext(os.path.basename(file_path))
                            output_filename = f"edited_{base}{ext}"
                            output_path = os.path.join(output_dir, output_filename)
                            
                            # Save the edited image
                            with open(output_path, "wb") as f:
                                f.write(output_image_data)
                            
                            edited_images.append(output_filename)
                            print(f"Saved edited image to {output_path}")
                        else:
                            error_msg = f"No image data in response for image {i+1}. Model may not support image editing. Try a different prompt or image."
                            print(error_msg)
                            errors.append(error_msg)
                    
                    except Exception as e:
                        error_msg = f"Error processing image {i+1}: {str(e)}"
                        print(error_msg)
                        errors.append(error_msg)
            else:
                flash("The required Google AI client library for new Gemini API is not available. Please install the latest version.", 'error')
                return render_template('feature_image_editor.html', prompts_data=PROMPT_CATEGORIES)
                
        except Exception as e:
            flash(f"Error processing images: {str(e)}", 'error')
            return render_template('feature_image_editor.html', prompts_data=PROMPT_CATEGORIES)
        finally:
            # Clean up temporary files
            for file_path in saved_files:
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        print(f"Removed temporary file: {file_path}")
                except Exception as e:
                    print(f"Error removing temporary file {file_path}: {e}")
        
        # If no successful edits, show error
        if not edited_images and errors:
            flash("Failed to generate any edited images. The model may not currently support image editing or the prompt may need to be more specific.", 'error')
            for error in errors:
                flash(error, 'warning')
        elif errors:
            # Show warnings for partial successes
            for error in errors:
                flash(error, 'warning')
        
        # Return results
        return render_template('feature_image_editor.html', 
                             edited_images=edited_images,
                             prompts_data=PROMPT_CATEGORIES)
    
    # GET request - just show the form
    return render_template('feature_image_editor.html', prompts_data=PROMPT_CATEGORIES)

@app.route('/download_edited_image/<filename>')
def download_edited_image(filename):
    return send_from_directory(os.path.join(app.static_folder, 'edited'),
                               filename, as_attachment=True)

@app.route('/download_all_edited_images')
def download_all_edited_images():
    # Create a temporary ZIP file
    memory_file = BytesIO()
    with zipfile.ZipFile(memory_file, 'w') as zf:
        edited_dir = os.path.join(app.static_folder, 'edited')
        for filename in os.listdir(edited_dir):
            file_path = os.path.join(edited_dir, filename)
            if os.path.isfile(file_path):
                zf.write(file_path, arcname=filename)
    
    # Reset file pointer and create response
    memory_file.seek(0)
    
    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    return send_file(
        memory_file,
        mimetype='application/zip',
        as_attachment=True,
        download_name=f'edited_images_{timestamp}.zip'
    )

def get_mime_type(file_path):
    """Determine the MIME type of a file"""
    extension = os.path.splitext(file_path)[1].lower()
    if extension in ['.jpg', '.jpeg']:
        return 'image/jpeg'
    elif extension == '.png':
        return 'image/png'
    elif extension == '.gif':
        return 'image/gif'
    elif extension == '.webp':
        return 'image/webp'
    else:
        return 'application/octet-stream'  # Default

@app.route('/download_processed/<filename>')
def download_processed_file(filename):
    """Serves the processed Excel file for download and then deletes it."""
    safe_filename = secure_filename(filename)
    if safe_filename != filename:
         flash("Invalid filename.", "error")
         return redirect(url_for('index'))

    file_path = os.path.join(PROCESSED_FOLDER, safe_filename)
    print(f"[DOWNLOAD] Request for: {file_path}")

    if not os.path.exists(file_path):
        print("[DOWNLOAD] ERROR: Processed file not found.")
        flash("Error: Processed file not found or expired.", "error")
        return redirect(url_for('feature_excel_row'))

    try:
        response = send_file(
            file_path,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename,
        )
        print(f"[DOWNLOAD] Sending file {filename}...")
        return response
    except Exception as e:
         print(f"[DOWNLOAD] ERROR sending file {filename}: {e}")
         flash(f"Error preparing file download: {e}", "error")
         return redirect(url_for('feature_excel_row'))
    finally:
        # Cleanup the file after send_file prepares the response
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"[DOWNLOAD] Deleted processed file after sending: {file_path}")
            except Exception as delete_e:
                print(f"[DOWNLOAD] ERROR deleting processed file {file_path} after sending: {delete_e}")


# --- 8. Save Text to File Utility ---

@app.route('/save_text', methods=['POST'])
def save_text():
    """Saves the provided text content to a downloadable .txt file."""
    text_to_save = request.form.get('text_content')
    original_prompt = request.form.get('original_prompt', 'response')

    if not text_to_save:
        flash('No text content found to save.', 'error')
        referer = request.headers.get("Referer")
        return redirect(referer or url_for('index'))

    try:
        safe_prompt = "".join(c if c.isalnum() or c in (' ', '_', '-') else '_' for c in original_prompt[:50]).rstrip().replace(' ', '_')
        filename = f"gemini_{safe_prompt}.txt"

        mem_io = io.BytesIO()
        mem_io.write(text_to_save.encode('utf-8'))
        mem_io.seek(0)

        print(f"[SAVE TEXT] Preparing file '{filename}' for download.")
        return send_file(
            mem_io,
            mimetype='text/plain',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        error_message = f"Error creating file for download: {e}"
        print(f"[SAVE TEXT] ERROR: {error_message}")
        flash(error_message, 'error')
        referer = request.headers.get("Referer")
        return redirect(referer or url_for('index'))


# --- Audio feature route ---
@app.route('/feature/audio', methods=['GET', 'POST'])
def feature_audio():
    """Handles audio file upload, prompt, and displays result on the same page."""
    if request.method == 'POST':
        prompt = request.form.get('prompt_audio')
        file = request.files.get('file_audio')
        original_filename = None
        local_filepath = None
        gemini_file = None

        # Validation
        if not prompt: 
            flash('Please enter a prompt for the audio.', 'error')
            return render_template('feature_audio.html', prompts_data=PROMPT_CATEGORIES)
        
        if not file or file.filename == '': 
            flash('No audio file selected.', 'error')
            return render_template('feature_audio.html', prompt=prompt, prompts_data=PROMPT_CATEGORIES)
        
        # Define allowed audio extensions
        ALLOWED_EXTENSIONS_AUDIO = {'mp3', 'wav', 'ogg', 'm4a', 'flac'}
        
        if not allowed_file(file.filename, ALLOWED_EXTENSIONS_AUDIO): 
            flash('Invalid file type. Please upload a supported audio format (MP3, WAV, OGG, M4A, FLAC).', 'error')
            return render_template('feature_audio.html', prompt=prompt, prompts_data=PROMPT_CATEGORIES)

        try:
            original_filename = secure_filename(file.filename)
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"{timestamp}-{original_filename}"
            local_filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            file.save(local_filepath)
            print(f"Audio saved locally: {local_filepath}")

            # Get MIME type for the audio file
            mime_type, _ = mimetypes.guess_type(local_filepath)
            if not mime_type:
                mime_type = 'audio/mpeg'  # Default to common audio MIME type if not detected
                
            # Upload local file to Gemini Files API
            gemini_file = upload_file_to_gemini(local_filepath, mime_type=mime_type)
            if not gemini_file:
                flash('Failed to upload or process audio file with Gemini. Check logs.', 'error')
                raise ValueError("Gemini file upload/processing failed.")  # Go to finally for cleanup

            print(f"Generating content for audio '{original_filename}' with prompt: {prompt[:50]}...")
            model = genai.GenerativeModel(model_name)
            response = model.generate_content([prompt, gemini_file])  # Pass file obj

            result_text = response.text
            print("Audio content generation successful.")

            return render_template('feature_audio.html', 
                                  prompt=prompt, 
                                  result=result_text, 
                                  filename=original_filename,
                                  prompts_data=PROMPT_CATEGORIES)

        except Exception as e:
            error_message = f"An error occurred processing the audio: {e}"
            print(error_message)
            flash(error_message, 'error')
            # Render form again, preserving prompt
            return render_template('feature_audio.html', 
                                  prompt=prompt, 
                                  prompts_data=PROMPT_CATEGORIES)

        finally:
            # Clean up local file regardless of success/failure
            if local_filepath and os.path.exists(local_filepath):
                try:
                    os.remove(local_filepath)
                    print(f"Removed temporary local file: {local_filepath}")
                except Exception as e:
                    print(f"Warning: Could not remove temporary file {local_filepath}: {e}")

            # Clean up Gemini file if it exists and we had an error
            if gemini_file and 'error_message' in locals():
                delete_gemini_file(gemini_file)

    # GET request: show the empty form
    return render_template('feature_audio.html', prompts_data=PROMPT_CATEGORIES)



@app.route('/download/<filename>')
def download_story_prompts(filename):
    """Downloads the generated Excel file with story prompts."""
    try:
        return send_from_directory(
            app.config['OUTPUT_FOLDER'],
            filename,
            as_attachment=True,
            download_name="Story_Prompts.xlsx"
        )
    except Exception as e:
        print(f"Error downloading story prompts file: {e}")
        flash("Could not download the Excel file.", "error")
        return redirect(url_for('feature_sentence_splitter'))

def generate_with_gemini(prompt_text):
    """Generate content using Google's Gemini API with retry logic for rate limits"""
    max_retries = 5
    base_retry_delay = 2  # Start with 2 seconds
    
    for attempt in range(max_retries):
        try:
            # Use the standard API with streaming
            model = genai.GenerativeModel("gemini-2.0-flash")
            
            # Configure to use plain text
            generation_config = {
                "temperature": 0.2,  # Lower temperature for more focused response
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 200,  # Limit response length
            }
            
            # Use streaming for better efficiency
            response_text = ""
            for chunk in model.generate_content(
                prompt_text,
                generation_config=generation_config,
                stream=True
            ):
                response_text += chunk.text
                
            # Clean the response - remove extra whitespace
            response_text = response_text.strip()
            
            return response_text
                
        except Exception as e:
            error_str = str(e)
            app.logger.warning(f"Attempt {attempt+1}/{max_retries} failed: {error_str}")
            
            # Check if it's a rate limit error (429)
            if "429" in error_str or "quota" in error_str.lower() or "exceeded" in error_str.lower():
                # Extract retry delay from error message if available
                import re
                retry_seconds = base_retry_delay * (2 ** attempt)  # Exponential backoff
                
                # Try to extract the recommended retry delay from the error message
                retry_match = re.search(r"retry_delay\s*{\s*seconds:\s*(\d+)", error_str)
                if retry_match:
                    retry_seconds = int(retry_match.group(1))
                    app.logger.info(f"Using recommended retry delay: {retry_seconds} seconds")
                
                # Add some jitter to avoid all clients retrying at exactly the same time
                import random
                jitter = random.uniform(0, 1)
                retry_seconds = retry_seconds + jitter
                
                app.logger.info(f"Rate limit exceeded. Retrying in {retry_seconds:.1f} seconds (attempt {attempt+1}/{max_retries})")
                
                # Sleep before retry
                import time
                time.sleep(retry_seconds)
                
                # Continue to the next retry attempt
                continue
            
            # If we get here, it wasn't a rate limit error or we're out of retries
            app.logger.error(f"Error generating content with Gemini: {e}")
            return "Unable to generate prompt. Please try again later."
    
    # If we've exhausted all retries
    return "API rate limit exceeded. Please try again later."

@app.route('/feature/sentence_splitter', methods=['GET', 'POST'])
def feature_sentence_splitter():
    """Splits text into individual sentences and saves them to an Excel file."""
    if request.method == 'POST':
        input_text = request.form.get('input_text')
        if not input_text:
            flash('Please enter some text to split.', 'error')
            return render_template('feature_sentence_splitter.html')

        try:
            print(f"Processing text input: {input_text[:100]}...")
            
            # Split the text into sentences
            import re
            # This regex handles basic sentence splitting
            sentences = re.split(r'(?<=[.!?])\s+', input_text.strip())
            sentences = [s for s in sentences if s.strip()]  # Remove empty sentences
            
            # Create a dataframe with one column for the sentences
            sentences_df = pd.DataFrame({
                'Sentence': sentences
            })
            
            # Save to Excel file
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            excel_filename = f"sentences_{timestamp}.xlsx"
            excel_path = os.path.join(app.config['PROCESSED_FOLDER'], excel_filename)
            
            # Create the Excel file
            sentences_df.to_excel(excel_path, index=False)
            print(f"Created Excel file with {len(sentences)} sentences: {excel_path}")
            
            return render_template('feature_sentence_splitter.html', 
                                  excel_file=excel_filename,
                                  sentence_count=len(sentences))

        except Exception as e:
            error_message = f"An error occurred while processing your text: {e}"
            print(error_message)
            flash(error_message, 'error')
            return render_template('feature_sentence_splitter.html', 
                                  input_text=input_text)

    # GET request - just show the form
    return render_template('feature_sentence_splitter.html')


@app.route('/download_sentence_excel/<filename>')
def download_sentence_excel(filename):
    """Download the generated Excel file with sentences."""
    try:
        return send_from_directory(
            app.config['PROCESSED_FOLDER'],
            filename,
            as_attachment=True,
            download_name="Sentences.xlsx"
        )
    except Exception as e:
        print(f"Error downloading sentences file: {e}")
        flash("Could not download the Excel file.", "error")
        return redirect(url_for('feature_sentence_splitter'))

# --- Story Prompt Generator Route ---
@app.route('/feature/story_prompts', methods=['GET', 'POST'])
def feature_story_prompts():
    """Handles the story prompt generation feature using the story.py module."""
    if request.method == 'POST':
        file = request.files.get('file_story')
        
        # Validate inputs
        if not file or file.filename == '':
            flash('Please upload an Excel file with your story sentences.', 'error')
            return render_template('feature_story_prompts.html', prompts_data=PROMPT_CATEGORIES)
        
        if not allowed_file(file.filename, ALLOWED_EXTENSIONS_XLS):
            flash(f'Invalid file type. Allowed: {", ".join(ALLOWED_EXTENSIONS_XLS)}', 'error')
            return render_template('feature_story_prompts.html', prompts_data=PROMPT_CATEGORIES)
        
        try:
            # Save the uploaded file
            original_filename = secure_filename(file.filename)
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"{timestamp}-{original_filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Process the file using the function from story.py
            from story import process_excel
            result = process_excel(filepath)
            
            # Extract output filename from result
            if result.startswith("Processing completed"):
                output_file = result.split("Results saved to ")[1]
                output_filename = os.path.basename(output_file)
                
                # Move the file to the OUTPUT_FOLDER for better organization
                if os.path.exists(output_file):
                    new_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
                    os.rename(output_file, new_path)
                    
                return render_template('feature_story_prompts.html', 
                                      success=True, 
                                      output_filename=output_filename,
                                      prompts_data=PROMPT_CATEGORIES)
            else:
                flash(result, 'error')
                return render_template('feature_story_prompts.html', prompts_data=PROMPT_CATEGORIES)
                
        except Exception as e:
            error_message = f"An error occurred processing your story: {e}"
            print(error_message)
            flash(error_message, 'error')
            return render_template('feature_story_prompts.html', prompts_data=PROMPT_CATEGORIES)
        
        finally:
            # Clean up the uploaded file
            if 'filepath' in locals() and os.path.exists(filepath):
                try:
                    os.remove(filepath)
                    print(f"Removed temporary file: {filepath}")
                except Exception as e:
                    print(f"Could not remove temporary file {filepath}: {e}")
    
    # GET request - just show the form
    return render_template('feature_story_prompts.html', prompts_data=PROMPT_CATEGORIES)

# --- Run the App ---
if __name__ == '__main__':
    print("-" * 50)
    print("Starting Flask server...")
    print(f"Gemini Model: {model_name}")
    print(f"Upload Folder: {UPLOAD_FOLDER}")
    print(f"Processed Folder: {PROCESSED_FOLDER}")
    print("Accessible on: http://<your-ip-address>:5001 (and http://127.0.0.1:5001)")
    print("-" * 50)
    app.run(debug=True, host='0.0.0.0', port=5001) # debug=True for development ONLY