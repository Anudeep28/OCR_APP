from django.shortcuts import render
import os
import json
import requests
from django.http import JsonResponse, HttpResponse, FileResponse
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from .models import OCRDocument
import pytesseract
from PIL import Image
from pdf2image import convert_from_path
import markdown
from together import Together
import base64
import pandas as pd
from io import BytesIO
from bs4 import BeautifulSoup
import markdown2

# Configure Tesseract path
tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
if not os.path.exists(tesseract_path):
    raise FileNotFoundError(f"Tesseract not found at {tesseract_path}. Please install Tesseract-OCR.")
pytesseract.pytesseract.tesseract_cmd = tesseract_path

def index(request):
    return render(request, 'ocr_app/index.html')

def process_image(image_path):
    try:
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img)
        return text
    except Exception as e:
        return str(e)

def process_pdf(pdf_path):
    try:
        pages = convert_from_path(pdf_path)
        text = ""
        for page in pages:
            text += pytesseract.image_to_string(page) + "\n\n"
        return text
    except Exception as e:
        return str(e)

def process_with_llm(file_path):
    try:
        # Initialize Together with API key from settings
        client = Together(api_key=settings.TOGETHER_API_KEY)
        
        # Read and encode the image file
        with open(file_path, 'rb') as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
        
        # Create the chat completion with image
        response = client.chat.completions.create(
            model="meta-llama/Llama-Vision-Free",
            messages=[{
                "role": "system",
                "content": """Convert the provided image into Markdown format. Ensure that all content from the page is included, such as headers, footers, subtexts, images (with all text if possible), tables, and any other elements.
  Requirements:

  - Output Only Markdown: Return solely the Markdown content without any additional explanations or comments.
  - No Delimiters: Do not use code fences or delimiters like \`\`\`markdown.
  - Complete Content: Do not omit any part of the page, including headers, footers, and subtext.
  """,
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }],
            max_tokens=512,
            temperature=0.7,
            top_p=0.7,
            top_k=50,
            repetition_penalty=1,
            stop=["<|eot_id|>","<|eom_id|>"]
        )
        
        # Get the response content
        markdown_text = response.choices[0].message.content
        return markdown_text
    except Exception as e:
        return str(e)

def upload_file(request):
    if request.method == 'POST' and request.FILES.get('file'):
        file = request.FILES['file']
        
        # Validate file extension
        ext = os.path.splitext(file.name)[1].lower()
        if ext not in ['.pdf', '.png', '.jpg', '.jpeg']:
            return JsonResponse({'error': 'Invalid file format'})
            
        # Save the file
        fs = FileSystemStorage()
        filename = fs.save(f"documents/{file.name}", file)
        file_path = fs.path(filename)
        
        # Process the file
        if ext == '.pdf':
            extracted_text = process_pdf(file_path)
        else:
            extracted_text = process_image(file_path)
            
        # Process with LLM
        markdown_output = process_with_llm(file_path)
        
        # Save to database
        doc = OCRDocument.objects.create(
            file=filename,
            processed_text=extracted_text,
            markdown_output=markdown_output
        )
        
        return JsonResponse({
            'success': True,
            'text': extracted_text,
            'markdown': markdown_output,
            'html': markdown.markdown(markdown_output),
            'doc_id': doc.id
        })
        
    return JsonResponse({'error': 'No file uploaded'})

def download_markdown(request, doc_id):
    try:
        doc = OCRDocument.objects.get(id=doc_id)
        response = HttpResponse(doc.markdown_output, content_type='text/markdown')
        response['Content-Disposition'] = f'attachment; filename="output_{doc_id}.md"'
        return response
    except OCRDocument.DoesNotExist:
        return JsonResponse({'error': 'Document not found'}, status=404)

def download_excel(request, doc_id):
    try:
        doc = OCRDocument.objects.get(id=doc_id)
        # Convert markdown to HTML
        html_content = markdown2.markdown(doc.markdown_output)
        
        # Extract relevant data from HTML (this is a simplified approach)
        # You may need to use BeautifulSoup or similar to parse the HTML properly
        df_data = []
        # Example: Extracting paragraphs as rows
        soup = BeautifulSoup(html_content, 'html.parser')
        for p in soup.find_all('p'):
            df_data.append([p.get_text()])  # Assuming each paragraph is a row
        
        # Create DataFrame from extracted data
        df = pd.DataFrame(df_data, columns=['Content'])
        
        # Create Excel file
        excel_file = BytesIO()
        # print(df.head())
        df.to_excel(excel_file, index=False, engine='openpyxl')
        excel_file.seek(0)
        
        response = HttpResponse(excel_file.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="output_{doc_id}.xlsx"'
        return response
    except OCRDocument.DoesNotExist:
        return JsonResponse({'error': 'Document not found'}, status=404)
