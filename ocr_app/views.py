# ocr_app/views.py
from django.views import View
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from .services.rag_utils import extract_data_from_document
from .models import CustomUser, LoanDocument, PropertyDocument, TableDocument, ExtractionPrompt, CustomExtraction
from django.views.generic.edit import CreateView
from django.urls import reverse_lazy
from .forms import CustomUserCreationForm
import logging
from datetime import datetime
import json
import csv
from django.http import HttpResponse, JsonResponse
from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin

logger = logging.getLogger(__name__)

class HomeView(View):
    def get(self, request):
        return render(request, 'ocr_app/index.html')

# Access control decorator from MEMORY
def app_access_required(view_func):
    from functools import wraps
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Please log in to access this feature")
            return redirect('login')
        if not request.user.is_app_user:
            messages.error(request, "You don't have access to document processing features")
            return redirect('ocr_app:home')
        return view_func(request, *args, **kwargs)
    return wrapper


class DocumentProcessView(View):
    template_name = 'ocr_app/document_upload.html'
    
    @method_decorator(app_access_required)
    def get(self, request):
        return render(request, self.template_name)
    
    @method_decorator(app_access_required)
    def post(self, request):
        if 'document' not in request.FILES:
            messages.error(request, 'Please select a document to upload')
            return render(request, self.template_name)
        
        document = request.FILES['document']
        document_type = request.POST.get('document_type')
        
        if not document_type:
            messages.error(request, 'Please select a document type')
            return render(request, self.template_name)
        
        print(f"\nProcessing uploaded file: {document.name}")
        
        fs = FileSystemStorage()
        filename = fs.save(document.name, document)
        file_path = fs.path(filename)
        print(f"File saved to: {file_path}")
        
        # Check if custom prompt is being used
        use_custom_prompt = request.POST.get('use_custom_prompt') == 'on'
        custom_prompt = request.POST.get('custom_prompt', '') if use_custom_prompt else None
        save_prompt = request.POST.get('save_prompt') == 'on'
        prompt_name = request.POST.get('prompt_name', '')
        
        # Save the custom prompt if requested
        if use_custom_prompt and save_prompt and prompt_name and custom_prompt:
            try:
                # Check if a prompt with this name already exists
                existing_prompt = ExtractionPrompt.objects.filter(
                    user=request.user,
                    name=prompt_name,
                    document_type=document_type
                ).first()
                
                if existing_prompt:
                    # Update existing prompt
                    existing_prompt.prompt_text = custom_prompt
                    existing_prompt.save()
                    messages.success(request, f'Updated existing prompt: {prompt_name}')
                else:
                    # Create new prompt
                    ExtractionPrompt.objects.create(
                        user=request.user,
                        document_type=document_type,
                        name=prompt_name,
                        prompt_text=custom_prompt
                    )
                    messages.success(request, f'Saved custom prompt: {prompt_name}')
            except Exception as e:
                messages.error(request, f'Error saving prompt: {str(e)}')
        
        try:
            # Extract data from document with optional custom prompt
            print("Calling extract_data_from_document...")
            result = extract_data_from_document(file_path, document_type, custom_prompt)
            print(f"Extraction result: {result}")
            
            if not result['success']:
                messages.error(request, f"Error processing document: {result.get('error', 'Unknown error')}")
                return render(request, self.template_name)
            
            # Get the structured data
            extracted_data = result.get('structured_data', {})
            
            # Process the extracted data to ensure proper structure for all fields
            processed_data = {}
            
            # For table documents, keep the original structure
            if document_type == 'table':
                processed_data = extracted_data
            else:
                # Process each field to ensure it has the right structure
                for key, value in extracted_data.items():
                    # If value is already a dict with 'original', 'language', 'translated' structure, keep it as is
                    if isinstance(value, dict) and 'original' in value and 'language' in value and 'translated' in value:
                        processed_data[key] = value
                    # If value is a string, convert it to the structured format
                    elif isinstance(value, str):
                        # Only process non-empty strings
                        if value.strip():
                            processed_data[key] = {
                                'original': value,
                                'language': 'auto',  # Will be determined during translation
                                'translated': value  # Default to original, will be translated if needed
                            }
                        else:
                            processed_data[key] = {
                                'original': '',
                                'language': 'none',
                                'translated': ''
                            }
                    # For other types (like lists or empty values), keep as is
                    else:
                        processed_data[key] = value
            
            # Save extraction with processed data
            custom_extraction = CustomExtraction.objects.create(
                user=request.user,
                document_type=document_type,
                extracted_data=processed_data,
                custom_prompt=custom_prompt if use_custom_prompt else "Default extraction"
            )
            
            # Create a list of fields and their languages for the template
            languages_detected = []
            if document_type != 'table':
                for key, value in processed_data.items():
                    if isinstance(value, dict) and 'language' in value and value.get('language') not in ['en', 'none', '']:
                        field_name = key.replace('_', ' ').title()
                        languages_detected.append((field_name, value.get('language')))
            
            messages.success(request, f'{document_type.title()} document processed successfully!')
            
            # Use different template for table documents
            if document_type == 'table':
                template_name = 'ocr_app/table_display.html'
            else:
                template_name = self.template_name
            
            # Render the template with the data
            return render(request, template_name, {
                'extraction': custom_extraction,
                'document_type': document_type,
                'processed_data': True,
                'extraction_data': processed_data,
                'languages_detected': languages_detected
            })
        
        except Exception as e:
            print(f"Error processing document: {str(e)}")
            messages.error(request, f"Error processing document: {str(e)}")
            return render(request, self.template_name)
            
        finally:
            if 'file_path' in locals():
                fs.delete(filename)


class SignUpView(CreateView):
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('login')
    template_name = 'registration/signup.html'
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Account created successfully! Please log in.')
        return response


# Custom logout view
def logout_view(request):
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('ocr_app:home')


class DownloadJSONView(LoginRequiredMixin, View):
    def get(self, request, document_type, document_id):
        try:
            # Get the extraction object
            extraction = get_object_or_404(CustomExtraction, id=document_id, user=request.user)
            
            # Get the extracted data
            data = extraction.extracted_data
            
            # Create a JSON response
            response = HttpResponse(json.dumps(data, indent=4), content_type='application/json')
            response['Content-Disposition'] = f'attachment; filename="{document_type}_extraction_{document_id}.json"'
            
            return response
        except Exception as e:
            messages.error(request, f"Error downloading JSON: {str(e)}")
            return redirect('ocr_app:document-upload')


class DownloadCSVView(LoginRequiredMixin, View):
    def get(self, request, document_type, document_id):
        try:
            # Get the extraction object
            extraction = get_object_or_404(CustomExtraction, id=document_id, user=request.user)
            
            # Get the extracted data
            data = extraction.extracted_data
            
            # Create a CSV response
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{document_type}_extraction_{document_id}.csv"'
            
            writer = csv.writer(response)
            
            # Handle table data differently
            if document_type == 'table' and 'columns' in data and 'rows' in data:
                # Write header row
                writer.writerow(data['columns'])
                
                # Write data rows
                for row in data['rows']:
                    row_values = [row.get(col, '') for col in data['columns']]
                    writer.writerow(row_values)
            else:
                # For regular documents, write key-value pairs
                writer.writerow(['Field', 'Original Value', 'Language', 'Translated Value'])
                
                for key, value in data.items():
                    if isinstance(value, dict) and 'original' in value:
                        writer.writerow([
                            key, 
                            value.get('original', ''),
                            value.get('language', ''),
                            value.get('translated', '')
                        ])
                    else:
                        writer.writerow([key, value, '', ''])
            
            return response
        except Exception as e:
            messages.error(request, f"Error downloading CSV: {str(e)}")
            return redirect('ocr_app:document-upload')


# API endpoint to get saved prompts for a specific document type
def get_saved_prompts(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    document_type = request.GET.get('document_type')
    if not document_type:
        return JsonResponse({'error': 'Document type is required'}, status=400)
    
    try:
        prompts = ExtractionPrompt.objects.filter(
            user=request.user,
            document_type=document_type
        ).values('id', 'name', 'prompt_text')
        
        return JsonResponse({
            'success': True,
            'prompts': list(prompts)
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
