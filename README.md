# GEMITAI - Google Gemini AI Interface

GEMITAI is a comprehensive web application that provides an intuitive interface for interacting with Google's Gemini AI models. It offers multiple features for processing various types of content including text, images, PDFs, videos, Excel files, and more.

## Features

- **Text Generation**: Generate text responses from prompts with a built-in prompt library
- **PDF Analysis**: Upload PDFs and ask questions about their content
- **Image Analysis**: Upload images and get AI-powered insights
- **Video Analysis**: Process videos and extract information
- **Excel Processing**: Analyze Excel files and process data row by row
- **Image Generation**: Create images from text prompts
- **Image Editing**: Edit images using AI
- **Audio Processing**: Transcribe and analyze audio files
- **Sentence Splitter**: Process sentences from stories to generate prompts for each sentence

## Installation

### Prerequisites

- Python 3.10.7 (recommended)
- Google Gemini API key

### Setup

1. Clone the repository:
   ```
   git clone <repository-url>
   cd GEMITAI
   ```

2. Create a virtual environment and activate it:
   ```
   python -m venv .venv
   # On Windows
   .venv\Scripts\activate
   # On macOS/Linux
   source .venv/bin/activate
   ```

3. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the root directory with your Gemini API key:
   ```
   GEMINI_API_KEY=your-api-key-here
   ```

## Usage

1. Start the Flask application:
   ```
   python app.py
   ```

2. Open your web browser and navigate to:
   ```
   http://localhost:5000
   ```

3. Select a feature from the main page and follow the instructions for each specific feature.

## Project Structure

- `app.py`: Main Flask application with routes and core functionality
- `config.py`: Configuration settings for the application
- `main.py`: Functions for processing Excel files and generating prompts
- `prompts.py`: Library of prompt templates organized by categories
- `story.py`: Implementation for the story prompt generator feature
- `web_app.py`: Additional web application functionality
- `static/`: CSS, JavaScript, and image assets
- `templates/`: HTML templates for the web interface
- `uploads/`: Directory for storing uploaded files
- `outputs/`: Directory for storing processed output files

## Dependencies

- Flask 2.3.3: Web framework
- Pandas 2.0.3: Data manipulation and analysis
- OpenPyXL 3.1.2: Excel file handling
- Google Generative AI 0.3.1: Interface to Google's Gemini AI models
- Werkzeug 2.3.7: WSGI web application library
- NLTK: Natural Language Toolkit for text processing
- python-dotenv: Environment variable management

## Notes

- The application requires a valid Google Gemini API key to function properly
- Large files (videos, PDFs) may take time to process depending on your internet connection and the Gemini API's processing speed
- The application has a file size limit of 1GB for uploads

## Troubleshooting

- If you encounter package compatibility issues, ensure you're using Python 3.10.7
- For numpy/pandas compatibility issues, try downgrading numpy to version 1.26.4 or earlier
- Make sure your Gemini API key is valid and has sufficient quota

## License

[Specify license information here]