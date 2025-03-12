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
import fitz  # PyMuPDF
import cv2
import numpy as np

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

def convert_pdf_to_images(pdf_path, target_dpi=300):
    """Convert PDF to images with quality optimizations"""
    try:
        print("Converting pdf to images using the optimization way")
        pdf_document = fitz.open(pdf_path)
        temp_dir = tempfile.mkdtemp()
        images = []
        
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            
            # Calculate zoom factor for target DPI
            zoom = target_dpi / 72
            matrix = fitz.Matrix(zoom, zoom)
            
            pix = page.get_pixmap(
                matrix=matrix,
                colorspace=fitz.csGRAY,  # Grayscale conversion
                alpha=False
            )
            
            image_path = os.path.join(temp_dir, f"page_{page_num + 1}.png")
            pix.save(image_path)
            
            # Apply post-processing
            enhanced_image = enhance_image_quality(image_path)
            cv2.imwrite(image_path, enhanced_image)
            
            # Convert to PIL Image for compatibility with existing code
            pil_image = Image.open(image_path)
            images.append(pil_image)
            
        return images
    except Exception as e:
        print(f"Error converting PDF: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return []

def enhance_image_quality(image_path):
    """Optimized image preprocessing pipeline"""
    try:
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        
        # CLAHE for contrast enhancement
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        img = clahe.apply(img)
        
        # Adaptive thresholding
        img = cv2.adaptiveThreshold(
            img, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )
        
        # Noise reduction
        img = cv2.fastNlMeansDenoising(img, h=10, 
                                    templateWindowSize=7, 
                                    searchWindowSize=21)
        return img
    except Exception as e:
        print(f"Error enhancing image: {str(e)}")
        return cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)

def enhance_pil_image(image):
    """Enhance a PIL image for better OCR results"""
    try:
        print("Starting image enhancement")
        # Convert to numpy array for OpenCV processing
        img_np = np.array(image)
        
        # Convert to grayscale if it's a color image
        if len(img_np.shape) == 3 and img_np.shape[2] == 3:
            gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_np
            
        # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        # Apply adaptive thresholding to separate text from background
        # For tables, we need to be more conservative with thresholding to preserve grid lines
        binary = cv2.adaptiveThreshold(
            enhanced, 
            255, 
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 
            15,  # Smaller block size for finer details
            5    # Lower C value to preserve more details
        )
        
        # Apply a light denoising to remove noise while preserving table structure
        denoised = cv2.fastNlMeansDenoising(binary, None, 10, 7, 21)
        
        # Convert back to PIL image
        enhanced_image = Image.fromarray(denoised)
        print("Image enhancement completed successfully")
        return enhanced_image
    
    except Exception as e:
        print(f"Error in enhance_pil_image: {str(e)}")
        # Return original image if enhancement fails
        return image

def detect_and_translate(text, model):
    """Detect language and translate text to English using Gemini"""
    try:
        if not text or text.strip() == "":
            return {"original": "", "language": "", "translated": ""}

        # First, detect the language
        prompt = f"""Analyze the following text and determine text language (ex. when you see Rajendra Goswami it is not Hindi, it is written in English). If it's in an Indian language, specify which one. Return ONLY the language code (e.g., 'hi' for Hindi, 'ta' for Tamil, etc.) or 'en' for English. Text to analyze:

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

def extract_property_data_from_image(image, model, custom_prompt=None):
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

        # Use custom prompt if provided, otherwise use default
        if custom_prompt:
            prompt = custom_prompt
            print("Using custom prompt for property extraction")
        else:
            prompt = """Please extract the following information from this document image, keeping any text in its original language. Return the data in valid JSON format with these fields:
            {
                "property_owner": "",
                "property_area": "",
                "property_size": "",
                "property_location": "",
                "property_coordinates": "",
                "property_value": "",
                "loan_limit": "",
                "risk_summary": "",
                "bank_name": "",
                "application_date": ""
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
            9. Use DOUBLE QUOTES for both property names and string values, not single quotes
            """
            print("Using default prompt for property extraction")

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
        try:
            # First attempt - direct parsing
            extracted_data = json.loads(response_text)
        except json.JSONDecodeError as e:
            print(f"Initial JSON parsing failed: {str(e)}")
            
            # Second attempt - try to find JSON-like content within the response
            try:
                # Look for content between curly braces
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                
                if start_idx >= 0 and end_idx > start_idx:
                    json_content = response_text[start_idx:end_idx]
                    print(f"Extracted JSON-like content: {json_content[:100]}...")
                    
                    # Fix Python-style dictionaries (with single quotes)
                    if "'" in json_content:
                        # Replace Python-style single quotes with double quotes for JSON compatibility
                        import re
                        
                        # First, escape any existing double quotes that are inside string values
                        # This pattern looks for double quotes that are between single quotes
                        fixed_content = re.sub(r"'([^']*?)\"([^']*?)'", r'"\1\\"\2"', json_content)
                        
                        # Then, handle the property names (keys)
                        # This regex looks for patterns like 'key': or 'key' :
                        fixed_content = re.sub(r"'([^']+)'(\s*):(\s*)", r'"\1"\2:\3', fixed_content)
                        
                        # Then handle the string values
                        # This regex looks for patterns like : 'value' or : 'value',
                        fixed_content = re.sub(r":(\s*)'([^']*)'(,|\s*}|$)", r':\1"\2"\3', fixed_content)
                        
                        print(f"Fixed JSON content: {fixed_content[:100]}...")
                        extracted_data = json.loads(fixed_content)
                    else:
                        extracted_data = json.loads(json_content)
                else:
                    # Third attempt - try to fix common JSON formatting issues
                    fixed_text = response_text
                    # Replace single quotes with double quotes for JSON compatibility
                    fixed_text = fixed_text.replace("'", '"')
                    # Ensure property names have double quotes
                    import re
                    fixed_text = re.sub(r'(\s*)(\w+)(\s*):(\s*)', r'\1"\2"\3:\4', fixed_text)
                    print(f"Fixed JSON text: {fixed_text[:100]}...")
                    extracted_data = json.loads(fixed_text)
            except Exception as inner_e:
                print(f"All JSON parsing attempts failed: {str(inner_e)}")
                print("Falling back to a structured empty response")
                
                # Create a default structure based on custom prompt or use generic fields
                extracted_data = {}
                
                # If we detected JSON-like content but couldn't parse it, try to extract key-value pairs manually
                if start_idx >= 0 and end_idx > start_idx:
                    json_content = response_text[start_idx:end_idx]
                    print("Attempting manual extraction of key-value pairs from JSON-like content")
                    
                    # Simple regex to extract key-value pairs from the JSON-like content
                    import re
                    # Look for patterns like 'key': 'value' or "key": "value" or 'key': 123
                    pairs = re.findall(r"['\"]([^'\"]+)['\"][\s]*:[\s]*['\"]?([^'\",}]*)['\"]*", json_content)
                    
                    for key, value in pairs:
                        print(f"Manually extracted: {key} = {value}")
                        extracted_data[key] = value.strip()
                    
                    if extracted_data:
                        print(f"Successfully extracted {len(extracted_data)} key-value pairs manually")
                
                # If manual extraction didn't work or no JSON-like content was found,
                # try to extract field names from the custom prompt
                if not extracted_data and custom_prompt:
                    # Look for field names in the custom prompt
                    import re
                    # Find words after "extract" or between commas, or after colons
                    potential_fields = re.findall(r'extract\s+(\w+)|[,:\s]\s*(\w+)\s*[,:]', custom_prompt.lower())
                    # Flatten and clean up the list
                    fields = []
                    for field_tuple in potential_fields:
                        for field in field_tuple:
                            if field and len(field) > 2 and field not in ['the', 'and', 'from', 'with', 'this', 'that']:
                                fields.append(field)
                    
                    # Add extracted fields to the default structure
                    for field in set(fields):
                        extracted_data[field] = ""
                
                # If no fields were extracted or custom_prompt is None, use default fields
                if not extracted_data and not custom_prompt:
                    extracted_data = {
                        "property_owner": "",
                        "property_area": "",
                        "property_size": "",
                        "property_location": "",
                        "property_coordinates": "",
                        "property_value": "",
                        "loan_limit": "",
                        "risk_summary": "",
                        "bank_name": "",
                        "application_date": ""
                    }
        
        print("JSON parsed successfully")
        print(f"Extracted data keys: {list(extracted_data.keys())}")

        # Process translations for text fields
        translated_data = {}
        
        # If using a custom prompt, only process fields that were extracted
        if custom_prompt:
            for field in extracted_data.keys():
                value = extracted_data.get(field, '')
                if isinstance(value, str):
                    translated_data[field] = detect_and_translate(value, model)
                else:
                    translated_data[field] = {
                        'original': value if value is not None else '',
                        'language': 'none',
                        'translated': value if value is not None else ''
                    }
        else:
            # For default prompts, ensure all required fields are present
            for field in extracted_data.keys():
                value = extracted_data.get(field, '')
                if field in ["witness_details", "emi_history"]:
                    # Handle arrays
                    translated_array = []
                    for item in value:
                        if isinstance(item, str) and item.strip():  # Only translate non-empty strings
                            translated_array.append(detect_and_translate(item, model))
                        else:
                            translated_array.append(item)
                    translated_data[field] = translated_array
                elif isinstance(value, str):
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

def extract_loan_data_from_image(image, model, custom_prompt=None):
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

        # Use custom prompt if provided, otherwise use default
        if custom_prompt:
            prompt = custom_prompt
            print("Using custom prompt for loan extraction")
        else:
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
                "credibility_summary": "",
                "bank_name": ""
            }
            
            Important:
            1. Return ONLY the JSON object, no additional text
            2. Use YYYY-MM-DD format for dates
            3. Remove any currency symbols and special characters from numbers
            4. If a field is not found in the image, leave it empty
            5. For loan amount, include the currency symbol (e.g., "₹")
            6. For witness_details and emi_history, use arrays even if empty
            7. Keep all text in its original language - do not translate
            8. Use DOUBLE QUOTES for both property names and string values, not single quotes"""
            print("Using default prompt for loan extraction")

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
        try:
            # First attempt - direct parsing
            extracted_data = json.loads(response_text)
        except json.JSONDecodeError as e:
            print(f"Initial JSON parsing failed: {str(e)}")
            
            # Second attempt - try to find JSON-like content within the response
            try:
                # Look for content between curly braces
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                
                if start_idx >= 0 and end_idx > start_idx:
                    json_content = response_text[start_idx:end_idx]
                    print(f"Extracted JSON-like content: {json_content[:100]}...")
                    
                    # Fix Python-style dictionaries (with single quotes)
                    if "'" in json_content:
                        # Replace Python-style single quotes with double quotes for JSON compatibility
                        import re
                        
                        # First, escape any existing double quotes that are inside string values
                        # This pattern looks for double quotes that are between single quotes
                        fixed_content = re.sub(r"'([^']*?)\"([^']*?)'", r'"\1\\"\2"', json_content)
                        
                        # Then, handle the property names (keys)
                        # This regex looks for patterns like 'key': or 'key' :
                        fixed_content = re.sub(r"'([^']+)'(\s*):(\s*)", r'"\1"\2:\3', fixed_content)
                        
                        # Then handle the string values
                        # This regex looks for patterns like : 'value' or : 'value',
                        fixed_content = re.sub(r":(\s*)'([^']*)'(,|\s*}|$)", r':\1"\2"\3', fixed_content)
                        
                        print(f"Fixed JSON content: {fixed_content[:100]}...")
                        extracted_data = json.loads(fixed_content)
                    else:
                        extracted_data = json.loads(json_content)
                else:
                    # Third attempt - try to fix common JSON formatting issues
                    fixed_text = response_text
                    # Replace single quotes with double quotes for JSON compatibility
                    fixed_text = fixed_text.replace("'", '"')
                    # Ensure property names have double quotes
                    import re
                    fixed_text = re.sub(r'(\s*)(\w+)(\s*):(\s*)', r'\1"\2"\3:\4', fixed_text)
                    print(f"Fixed JSON text: {fixed_text[:100]}...")
                    extracted_data = json.loads(fixed_text)
            except Exception as inner_e:
                print(f"All JSON parsing attempts failed: {str(inner_e)}")
                print("Falling back to a structured empty response")
                
                # Create a default structure based on custom prompt or use generic fields
                extracted_data = {}
                
                # If we detected JSON-like content but couldn't parse it, try to extract key-value pairs manually
                if start_idx >= 0 and end_idx > start_idx:
                    json_content = response_text[start_idx:end_idx]
                    print("Attempting manual extraction of key-value pairs from JSON-like content")
                    
                    # Simple regex to extract key-value pairs from the JSON-like content
                    import re
                    # Look for patterns like 'key': 'value' or "key": "value" or 'key': 123
                    pairs = re.findall(r"['\"]([^'\"]+)['\"][\s]*:[\s]*['\"]?([^'\",}]*)['\"]*", json_content)
                    
                    for key, value in pairs:
                        print(f"Manually extracted: {key} = {value}")
                        extracted_data[key] = value.strip()
                    
                    if extracted_data:
                        print(f"Successfully extracted {len(extracted_data)} key-value pairs manually")
                
                # If manual extraction didn't work or no JSON-like content was found,
                # try to extract field names from the custom prompt
                if not extracted_data and custom_prompt:
                    # Look for field names in the custom prompt
                    import re
                    # Find words after "extract" or between commas, or after colons
                    potential_fields = re.findall(r'extract\s+(\w+)|[,:\s]\s*(\w+)\s*[,:]', custom_prompt.lower())
                    # Flatten and clean up the list
                    fields = []
                    for field_tuple in potential_fields:
                        for field in field_tuple:
                            if field and len(field) > 2 and field not in ['the', 'and', 'from', 'with', 'this', 'that']:
                                fields.append(field)
                    
                    # Add extracted fields to the default structure
                    for field in set(fields):
                        extracted_data[field] = ""
                
                # If no fields were extracted or custom_prompt is None, use default fields
                if not extracted_data and not custom_prompt:
                    extracted_data = {
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
                        "credibility_summary": "",
                        "bank_name": ""
                    }
        
        print("JSON parsed successfully")
        print(f"Extracted data keys: {list(extracted_data.keys())}")

        # Process translations for text fields
        translated_data = {}
        
        # If using a custom prompt, only process fields that were extracted
        if custom_prompt:
            for field in extracted_data.keys():
                value = extracted_data.get(field, '')
                if isinstance(value, str):
                    translated_data[field] = detect_and_translate(value, model)
                else:
                    translated_data[field] = {
                        'original': value if value is not None else '',
                        'language': 'none',
                        'translated': value if value is not None else ''
                    }
        else:
            # For default prompts, ensure all required fields are present
            for field in extracted_data.keys():
                value = extracted_data.get(field, '')
                if field in ["witness_details", "emi_history"]:
                    # Handle arrays
                    translated_array = []
                    for item in value:
                        if isinstance(item, str) and item.strip():  # Only translate non-empty strings
                            translated_array.append(detect_and_translate(item, model))
                        else:
                            translated_array.append(item)
                    translated_data[field] = translated_array
                elif isinstance(value, str):
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
        print(f"\n!!! ERROR in extract_loan_data_from_image: {str(e)}")
        print(f"Error type: {type(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return None

def extract_table_data_from_image(image, model, custom_prompt=None):
    """Extract table data from a single image using Gemini vision model"""
    try:
        print("\n=== Starting Table Data Extraction ===")
        print(f"Image type: {type(image)}")
        if isinstance(image, str):
            print("Image is already a base64 string")
            image_data = image
        else:
            # For tables, use the original image without enhancement
            print("Using original image for table recognition")
            image_data = image_to_base64(image)

        # Use custom prompt if provided, otherwise use default
        if custom_prompt:
            prompt = custom_prompt
            print("Using custom prompt for table extraction")
        else:
            prompt = """Please extract the data from this table image. Identify all columns and rows, and return the data in a structured JSON format with the following structure:
            {
                "columns": ["Column1", "Column2", "Column3", ...],
                "rows": [
                    {"Column1": "value1", "Column2": "value2", "Column3": "value3", ...},
                    {"Column1": "value1", "Column2": "value2", "Column3": "value3", ...},
                    ...
                ]
            }
            
            Important:
            1. Return ONLY the JSON object, no additional text
            2. Preserve the exact column names as they appear in the table
            3. Make sure all rows have values for all columns (use empty string if no value)
            4. Ensure the data is properly structured with each row as an object with column names as keys
            5. Use DOUBLE QUOTES for both property names and string values, not single quotes
            6. If there are merged cells, duplicate the value in all applicable rows/columns
            7. Keep all text in its original language - do not translate
            8. If a cell contains numeric data, preserve it as a string with the original formatting
            """
            print("Using default prompt for table extraction")

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
        try:
            # First attempt - direct parsing
            extracted_data = json.loads(response_text)
        except json.JSONDecodeError as e:
            print(f"Initial JSON parsing failed: {str(e)}")
            
            # Second attempt - try to find JSON-like content within the response
            try:
                # Look for content between curly braces
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                
                if start_idx >= 0 and end_idx > start_idx:
                    json_content = response_text[start_idx:end_idx]
                    print(f"Extracted JSON-like content: {json_content[:100]}...")
                    
                    # Fix Python-style dictionaries (with single quotes)
                    if "'" in json_content:
                        # Replace Python-style single quotes with double quotes for JSON compatibility
                        import re
                        
                        # First, escape any existing double quotes that are inside string values
                        # This pattern looks for double quotes that are between single quotes
                        fixed_content = re.sub(r"'([^']*?)\"([^']*?)'", r'"\1\\"\2"', json_content)
                        
                        # Then, handle the property names (keys)
                        # This regex looks for patterns like 'key': or 'key' :
                        fixed_content = re.sub(r"'([^']+)'(\s*):(\s*)", r'"\1"\2:\3', fixed_content)
                        
                        # Then handle the string values
                        # This regex looks for patterns like : 'value' or : 'value',
                        fixed_content = re.sub(r":(\s*)'([^']*)'(,|\s*}|$)", r':\1"\2"\3', fixed_content)
                        
                        print(f"Fixed JSON content: {fixed_content[:100]}...")
                        extracted_data = json.loads(fixed_content)
                    else:
                        extracted_data = json.loads(json_content)
                else:
                    # Third attempt - try to fix common JSON formatting issues
                    fixed_text = response_text
                    # Replace single quotes with double quotes for JSON compatibility
                    fixed_text = fixed_text.replace("'", '"')
                    # Ensure property names have double quotes
                    import re
                    fixed_text = re.sub(r'(\s*)(\w+)(\s*):(\s*)', r'\1"\2"\3:\4', fixed_text)
                    print(f"Fixed JSON text: {fixed_text[:100]}...")
                    extracted_data = json.loads(fixed_text)
            except Exception as inner_e:
                print(f"All JSON parsing attempts failed: {str(inner_e)}")
                print("Falling back to a structured empty response")
                
                # Create a default structure for table data
                extracted_data = {
                    "columns": [],
                    "rows": []
                }
        
        print("JSON parsed successfully")
        print(f"Extracted data keys: {list(extracted_data.keys())}")

        # Ensure the extracted data has the expected structure
        if "columns" not in extracted_data:
            extracted_data["columns"] = []
        if "rows" not in extracted_data:
            extracted_data["rows"] = []

        # Validate and clean up the data
        columns = extracted_data["columns"]
        rows = extracted_data["rows"]
        
        # Ensure all rows have all columns
        for row in rows:
            for col in columns:
                if col not in row:
                    row[col] = ""

        print(f"Extracted {len(columns)} columns and {len(rows)} rows")
        return extracted_data

    except Exception as e:
        print(f"\n!!! ERROR in extract_table_data_from_image: {str(e)}")
        print(f"Error type: {type(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return None

def extract_data_from_document(file_path, document_type='loan', custom_prompt=None):
    """Process document and extract structured data using Gemini vision model"""
    try:
        print(f"\n=== Starting Document Processing ===")
        print(f"Processing file: {file_path}")
        print(f"Document type: {document_type}")
        print(f"File exists: {os.path.exists(file_path)}")
        print(f"File size: {os.path.getsize(file_path)} bytes")
        print(f"Custom prompt provided: {bool(custom_prompt)}")

        # Configure Gemini
        print("\nConfiguring Gemini API...")
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        model = genai.GenerativeModel('gemini-2.0-flash')
        print("Gemini model initialized")
        
        all_extracted_data = []
        
        # Select the appropriate extraction function based on document type
        if document_type == 'loan':
            extract_function = extract_loan_data_from_image
        elif document_type == 'property':
            extract_function = extract_property_data_from_image
        elif document_type == 'table':
            extract_function = extract_table_data_from_image
        else:
            # Default to loan document extraction
            extract_function = extract_loan_data_from_image
        
        # Handle PDF files
        if file_path.lower().endswith('.pdf'):
            print("\nProcessing PDF file...")
            poppler_path = r"C:\Program Files\poppler-24.08.0\Library\bin"
            print(f"Using Poppler path: {poppler_path}")
            print(f"Poppler path exists: {os.path.exists(poppler_path)}")
            
            try:
                images = convert_pdf_to_images(file_path)
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
                extracted = extract_function(image, model, custom_prompt)
                if extracted:
                    print(f"Successfully extracted data from page {i}")
                    all_extracted_data.append(extracted)
                else:
                    print(f"Failed to extract data from page {i}")
        
        else:
            print("\nProcessing image file...")
            with Image.open(file_path) as image:
                print(f"Image opened successfully. Size: {image.size}, Mode: {image.mode}")
                extracted = extract_function(image, model, custom_prompt)
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
        
        # For table documents, we need special handling to merge tables across pages
        if document_type == 'table':
            if len(all_extracted_data) > 1:
                # For tables, we'll merge by appending rows and ensuring columns are consistent
                all_columns = set()
                for data in all_extracted_data:
                    all_columns.update(data.get("columns", []))
                
                # Convert to list and maintain order
                all_columns_list = list(all_columns)
                
                # Create a new merged structure
                merged_rows = []
                for data in all_extracted_data:
                    rows = data.get("rows", [])
                    # Ensure all rows have all columns
                    for row in rows:
                        for col in all_columns_list:
                            if col not in row:
                                row[col] = ""
                        merged_rows.append(row)
                
                merged_data = {
                    "columns": all_columns_list,
                    "rows": merged_rows
                }
            return {
                'success': True,
                'structured_data': merged_data
            }
        
        # For custom prompts, we want to preserve the original field names
        if custom_prompt:
            for data in all_extracted_data[1:]:
                # Update empty fields from subsequent pages
                for key, value in data.items():
                    try:
                        # Only process keys that already exist in merged_data
                        if key in merged_data:
                            # Handle dictionary values (like translated fields)
                            if isinstance(value, dict) and isinstance(merged_data.get(key), dict):
                                # If the original field is empty but this one has content, use this one
                                if (not merged_data[key].get("original") or merged_data[key].get("original") == "") and value.get("original"):
                                    merged_data[key] = value
                                    print(f"Updated field {key} from subsequent page")
                            # Handle list values
                            elif isinstance(value, list) and isinstance(merged_data.get(key), list):
                                # Extend lists with unique values
                                for item in value:
                                    if item not in merged_data[key]:
                                        merged_data[key].append(item)
                            # Handle simple values (like dates and numbers)
                            elif (not merged_data.get(key) or merged_data.get(key) == "") and value:
                                merged_data[key] = value
                                print(f"Updated field {key} from subsequent page")
                    except Exception as e:
                        print(f"Error merging field {key}: {str(e)}")
                        continue
        else:
            # Standard field merging for non-custom prompts
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