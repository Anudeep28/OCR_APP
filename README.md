# OCR Web Application

A modern web application that performs OCR on images and PDFs using Tesseract and processes the text using a locally hosted LLM through Ollama.

## Prerequisites

1. Python 3.8 or higher
2. Tesseract OCR installed on your system
3. Ollama installed and running locally
4. Poppler (for PDF processing)

## Setup Instructions

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Install Tesseract OCR:
   - Windows: Download and install from https://github.com/UB-Mannheim/tesseract/wiki
   - Add Tesseract to your system PATH

3. Install Poppler:
   - Windows: Download from http://blog.alivate.com.au/poppler-windows/
   - Add to system PATH

4. Make sure Ollama is running locally with your preferred model

5. Run migrations:
   ```bash
   python manage.py migrate
   ```

6. Start the development server:
   ```bash
   python manage.py runserver
   ```

Visit http://localhost:8000 to use the application.
