import google.generativeai as genai
from django.conf import settings
from pdf2image import convert_from_path
from PIL import Image
import tempfile
import logging
import json
import os
import base64
from io import BytesIO

logger = logging.getLogger(__name__)

# Add Poppler to system PATH
poppler_path = r"C:\Program Files\poppler-24.08.0\Library\bin"
if poppler_path not in os.environ["PATH"]:
    os.environ["PATH"] += os.pathsep + poppler_path

def image_to_base64(image):
    """Convert PIL Image to base64 string"""
    print(f"Converting image to base64. Image size: {image.size}")
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
    print(f"Base64 string length: {len(img_str)}")
    return img_str

def detect_and_translate(text, model):
    """Detect language and translate text to English using Gemini"""
    try:
        if not text or text.strip() == "":
            return {"original": "", "language": "", "translated": ""}

        # First, detect the language
        prompt = f"""Analyze the following text and determine its language. If it's in an Indian language, specify which one. Return ONLY the language code (e.g., 'hi' for Hindi, 'ta' for Tamil, etc.) or 'en' for English. Text to analyze:

{text}"""
        
        response = model.generate_content(prompt)
        language = response.text.strip().lower()
        
        result = {
            "original": text,
            "language": language,
            "translated": text  # Default to original if English
        }
        
        # Translate if not English and language was detected
        if language and language != 'en':
            translate_prompt = f"""Translate the following text from {language} to English. Provide ONLY the English translation, no additional text or explanations:

{text}"""
            translation = model.generate_content(translate_prompt)
            translated_text = translation.text.strip()
            if translated_text:  # Only update if we got a translation
                result["translated"] = translated_text
            print(f"Translation result for '{text}': {result}")  # Add debug logging
            
        return result
    except Exception as e:
        logger.error(f"Translation error: {str(e)}")
        return {"original": text, "language": "unknown", "translated": text}

def extract_property_data_from_image(image, model):
    """Extract property data from a single image using Gemini vision model"""
    try:
        print("\n=== Starting Property Data Extraction ===")
        print(f"Image type: {type(image)}")
        if isinstance(image, str):
            print("Image is already a base64 string")
            image_data = image
        else:
            print("Converting image to base64")
            image_data = image_to_base64(image)

        prompt = """Please extract the following information from this document image, keeping any text in its original language. Return the data in valid JSON format with these fields:
        {
            "property_owner": "",
            "property_area": "",
            "property_location": "",
            "property_coordinates": "",
            "property_value": "",
            "loan_limit": "",
            "risk_summary": ""
        }
        
        Important:
        1. Return ONLY the JSON object, no additional text
        2. Remove any currency symbols and special characters from numbers
        3. If a field is not found in the image, leave it empty
        4. For property_area, include the unit (e.g., "1200 sq ft")
        5. For property_value, property_limit, include the currency symbol (e.g., "₹")  
        6. For property_coordinates, use the format "latitude° N/S, longitude° E/W"
        7. For risk_summary, provide a brief assessment of the property's risk factors
        8. Keep all text in its original language - do not translate
        """

        print("\n=== Sending Request to Gemini ===")
        print(f"Prompt length: {len(prompt)}")
        print("Generating content with Gemini...")
        
        # Create image parts for the model
        image_part = {'mime_type': 'image/jpeg', 'data': image_data}
        response = model.generate_content([prompt, image_part])
        
        print("\n=== Processing Gemini Response ===")
        print(f"Response type: {type(response)}")
        print(f"Raw response preview: {str(response.text)[:200]}...")

        # Extract JSON from the response
        response_text = response.text
        # Remove any markdown code block syntax if present
        response_text = response_text.replace('```json', '').replace('```', '').strip()
        print("\nCleaned response text preview:")
        print(response_text[:200])

        print("\n=== Parsing JSON ===")
        extracted_data = json.loads(response_text)
        print("JSON parsed successfully")
        print(f"Extracted data keys: {list(extracted_data.keys())}")

        # Process translations for text fields
        translated_data = {}
        for field in ['property_owner', 'property_area', 'property_location', 'property_coordinates', 
                     'property_value', 'loan_limit', 'risk_summary']:
            value = extracted_data.get(field, '')
            if value and isinstance(value, str):
                translated_data[field] = detect_and_translate(value, model)
            else:
                translated_data[field] = {
                    'original': value if value is not None else '',
                    'language': 'none',
                    'translated': value if value is not None else ''
                }

        print("\n=== Translation Complete ===")
        return translated_data

    except Exception as e:
        print(f"\n!!! ERROR in extract_property_data_from_image: {str(e)}")
        print(f"Error type: {type(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return None

def extract_loan_data_from_image(image, model):
    """Extract loan data from a single image using Gemini vision model"""
    try:
        print("\n=== Starting Loan Data Extraction ===")
        print(f"Image type: {type(image)}")
        if isinstance(image, str):
            print("Image is already a base64 string")
            image_data = image
        else:
            print("Converting image to base64")
            image_data = image_to_base64(image)

        prompt = """Please extract the following information from this document image, keeping any text in its original language. Return the data in valid JSON format with these fields:
        {
            "borrower_name": "",
            "date_of_birth": "",
            "sex": "",
            "father_name": "",
            "spouse_name": "",
            "aadhar_number": "",
            "pan_number": "",
            "passport_number": "",
            "driving_license": "",
            "loan_amount": "",
            "loan_sanction_date": "",
            "loan_balance": "",
            "witness_details": [],
            "emi_history": [],
            "credibility_summary": ""
        }
        
        Important:
        1. Return ONLY the JSON object, no additional text
        2. Use YYYY-MM-DD format for dates
        3. Remove any currency symbols and special characters from numbers
        4. If a field is not found in the image, leave it empty
        5. For loan amount, include the currency symbol (e.g., "₹")
        6. For witness_details and emi_history, use arrays even if empty
        7. Keep all text in its original language - do not translate"""

        print("\n=== Sending Request to Gemini ===")
        print(f"Prompt length: {len(prompt)}")
        print("Generating content with Gemini...")
        
        # Create image parts for the model
        image_part = {'mime_type': 'image/jpeg', 'data': image_data}
        response = model.generate_content([prompt, image_part])
        
        print("\n=== Processing Gemini Response ===")
        print(f"Response type: {type(response)}")
        print(f"Raw response preview: {str(response.text)[:200]}...")

        # Extract JSON from the response
        response_text = response.text
        # Remove any markdown code block syntax if present
        response_text = response_text.replace('```json', '').replace('```', '').strip()
        print("\nCleaned response text preview:")
        print(response_text[:200])

        print("\n=== Parsing JSON ===")
        extracted_data = json.loads(response_text)
        print("JSON parsed successfully")
        print(f"Extracted data keys: {list(extracted_data.keys())}")

        # Ensure all required fields are present and process translations
        required_fields = [
            "borrower_name", "date_of_birth", "sex", "father_name", "spouse_name",
            "aadhar_number", "pan_number", "passport_number", "driving_license",
            "loan_amount", "loan_sanction_date", "loan_balance", "witness_details",
            "emi_history", "credibility_summary"
        ]
        
        # Process translations for text fields
        translated_data = {}
        for field in required_fields:
            if field not in extracted_data:
                print(f"Adding missing field: {field}")
                extracted_data[field] = "" if field not in ["witness_details", "emi_history"] else []
                translated_data[field] = {"original": "", "language": "", "translated": ""}
            else:
                value = extracted_data[field]
                if field in ["witness_details", "emi_history"]:
                    # Handle arrays
                    translated_array = []
                    for item in value:
                        if isinstance(item, str) and item.strip():  # Only translate non-empty strings
                            translated_array.append(detect_and_translate(item, model))
                        else:
                            translated_array.append(item)
                    translated_data[field] = translated_array
                elif isinstance(value, str) and value.strip():  # Only translate non-empty strings
                    # Handle string fields
                    translated_data[field] = detect_and_translate(value, model)
                    print(f"Translated {field}: {translated_data[field]}")  # Add debug logging
                else:
                    # Handle non-string fields (like numbers) or empty strings
                    translated_data[field] = {"original": value, "language": "none", "translated": value}

        print("\n=== Translation Complete ===")
        return translated_data

    except Exception as e:
        print(f"\n!!! ERROR in extract_loan_data_from_image: {str(e)}")
        print(f"Error type: {type(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return None

def extract_data_from_document(file_path, document_type='loan'):
    """Process document and extract structured data using Gemini vision model"""
    try:
        print(f"\n=== Starting Document Processing ===")
        print(f"Processing file: {file_path}")
        print(f"Document type: {document_type}")
        print(f"File exists: {os.path.exists(file_path)}")
        print(f"File size: {os.path.getsize(file_path)} bytes")

        # Configure Gemini
        print("\nConfiguring Gemini API...")
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        model = genai.GenerativeModel('gemini-2.0-flash')
        print("Gemini model initialized")
        
        all_extracted_data = []
        extract_function = extract_loan_data_from_image if document_type == 'loan' else extract_property_data_from_image
        
        # Handle PDF files
        if file_path.lower().endswith('.pdf'):
            print("\nProcessing PDF file...")
            poppler_path = r"C:\Program Files\poppler-24.08.0\Library\bin"
            print(f"Using Poppler path: {poppler_path}")
            print(f"Poppler path exists: {os.path.exists(poppler_path)}")
            
            try:
                images = convert_from_path(file_path, poppler_path=poppler_path)
                print(f"Converted PDF to {len(images)} images")
            except Exception as e:
                print(f"Error converting PDF: {str(e)}")
                print("Checking Poppler installation:")
                print(f"1. Checking if pdftoppm exists: {os.path.exists(os.path.join(poppler_path, 'pdftoppm.exe'))}")
                print(f"2. Checking if pdfinfo exists: {os.path.exists(os.path.join(poppler_path, 'pdfinfo.exe'))}")
                raise Exception(f"PDF conversion failed. Please ensure Poppler is installed correctly at {poppler_path}")
            
            for i, image in enumerate(images, 1):
                print(f"\nProcessing page {i}/{len(images)}")
                print(f"Image size: {image.size}")
                extracted = extract_function(image, model)
                if extracted:
                    print(f"Successfully extracted data from page {i}")
                    all_extracted_data.append(extracted)
                else:
                    print(f"Failed to extract data from page {i}")
        
        else:
            print("\nProcessing image file...")
            with Image.open(file_path) as image:
                print(f"Image opened successfully. Size: {image.size}, Mode: {image.mode}")
                extracted = extract_function(image, model)
                if extracted:
                    print("Successfully extracted data from image")
                    all_extracted_data.append(extracted)
                else:
                    print("Failed to extract data from image")
        
        if not all_extracted_data:
            print("\n!!! No data could be extracted from the document")
            return {
                'success': False,
                'error': 'Failed to extract data from document'
            }
        
        print("\n=== Merging Data ===")
        # Merge data from all pages (for PDFs) or use single image data
        merged_data = all_extracted_data[0]  # Use first page as base
        for data in all_extracted_data[1:]:
            # Update empty fields from subsequent pages
            for key, value in data.items():
                try:
                    # Handle dictionary values (like translated fields)
                    if isinstance(value, dict) and isinstance(merged_data.get(key), dict):
                        if not merged_data[key].get("original") and value.get("original"):
                            merged_data[key] = value
                    # Handle list values (like witness_details and emi_history)
                    elif isinstance(value, list) and isinstance(merged_data.get(key), list):
                        merged_data[key].extend(value)
                    # Handle simple values (like dates and numbers)
                    elif not merged_data.get(key) and value:
                        merged_data[key] = value
                except Exception as e:
                    print(f"Error merging field {key}: {str(e)}")
                    continue
        
        print("\n=== Processing Complete ===")
        print(f"Final data keys: {list(merged_data.keys())}")
        return {
            'success': True,
            'structured_data': merged_data
        }
        
    except Exception as e:
        print(f"\n!!! ERROR in extract_data_from_document: {str(e)}")
        print(f"Error type: {type(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return {
            'success': False,
            'error': str(e)
        }