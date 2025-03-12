# OCR Web Application

A modern web application for Optical Character Recognition (OCR) and document processing with advanced features for handling multilingual documents, including Indian languages. The application uses Google's Gemini AI for enhanced text extraction, language detection, and translation capabilities.

## Features

- **Document Processing**: Upload and process PDF documents and images
- **Multilingual Support**: Detect and process text in multiple languages, including Indian languages
- **Document Type Processing**:
  - **Loan Documents**: Extract borrower information, loan details, and other relevant fields
  - **Property Documents**: Extract property details, location, valuation, and risk assessment
  - **Table Documents**: Extract structured tabular data with column and row preservation
- **Data Export**: Download extracted data in JSON and CSV formats
- **Custom Prompts**: Create and save custom extraction prompts for different document types
- **User Management**: Role-based access control for document processing features

## Technologies Used

- **Backend**: Django 4.2
- **OCR Engine**: Google Gemini AI for advanced text recognition and processing
- **Image Processing**: OpenCV and PIL for image enhancement and preprocessing
- **PDF Processing**: PyMuPDF and pdf2image for PDF handling
- **Machine Learning**: Integration with Gemini for AI-powered document analysis
- **Frontend**: Bootstrap 5 for responsive UI

## Prerequisites

1. Python 3.8 or higher
2. Google Gemini API key (for AI-powered OCR and text processing)
3. Poppler (for PDF processing)

## Setup Instructions

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd OCR_website
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   Create a `.env` file in the project root with the following:
   ```
   GOOGLE_API_KEY=your_gemini_api_key
   ```

5. Install Poppler (for PDF processing):
   - Windows: Download from http://blog.alivate.com.au/poppler-windows/
   - Add to system PATH

6. Run migrations:
   ```bash
   python manage.py migrate
   ```

7. Create a superuser:
   ```bash
   python manage.py createsuperuser
   ```

8. Start the development server:
   ```bash
   python manage.py runserver
   ```

9. Visit http://localhost:8000 to use the application
   - Admin panel: http://localhost:8000/admin/

## Usage

1. **Login**: Access the application using your credentials
2. **Document Upload**: Select the document type (Loan, Property, or Table) and upload your file
3. **Processing**: The system will process the document and extract relevant information
4. **Results**: View the extracted data in a structured format
5. **Export**: Download the results in JSON or CSV format

## Document Types

### Loan Documents
Extracts information such as borrower details, loan amount, interest rates, tenure, and other relevant loan information.

### Property Documents
Extracts property details including owner information, property size, location, valuation, and risk assessment.

### Table Documents
Extracts structured tabular data, preserving columns and rows for easy analysis and export.

## Custom Extraction
The application allows users to create and save custom extraction prompts for different document types, enabling tailored extraction for specific document formats.

## License

This project is licensed under the [MIT License](LICENSE).
