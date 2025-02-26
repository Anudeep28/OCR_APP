# ocr_app/views.py
from django.views import View
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from .services.rag_utils import extract_data_from_document
from .models import CustomUser, LoanDocument, PropertyDocument
from django.views.generic.edit import CreateView
from django.urls import reverse_lazy
from .forms import CustomUserCreationForm
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def home(request):
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
        
        try:
            # Extract data from document
            print("Calling extract_data_from_document...")
            result = extract_data_from_document(file_path, document_type)
            print(f"Extraction result: {result}")
            
            if not result['success']:
                messages.error(request, f"Error processing document: {result.get('error', 'Unknown error')}")
                return render(request, self.template_name)
            
            if document_type == 'loan':
                # Handle loan document with translations
                loan_data = result.get('structured_data', {})
                
                # Helper function to safely get values
                def safe_get(data_dict, key):
                    if not data_dict:
                        return {'original': '', 'language': 'en', 'translated': ''}
                    value = data_dict.get(key, {})
                    if not isinstance(value, dict):
                        return {'original': '', 'language': 'en', 'translated': ''}
                    return {
                        'original': value.get('original', '') or '',
                        'language': value.get('language', 'en') or 'en',
                        'translated': value.get('translated', '') or ''
                    }
                
                # Get data with safe defaults
                borrower_name = safe_get(loan_data, 'borrower_name')
                father_name = safe_get(loan_data, 'father_name')
                spouse_name = safe_get(loan_data, 'spouse_name')
                sex = safe_get(loan_data, 'sex')
                loan_purpose = safe_get(loan_data, 'loan_purpose')
                credibility_summary = safe_get(loan_data, 'credibility_summary')
                
                # Handle date fields
                try:
                    date_of_birth = loan_data.get('date_of_birth', {}).get('original')
                    if date_of_birth:
                        date_of_birth = datetime.strptime(date_of_birth, '%Y-%m-%d').date()
                    else:
                        date_of_birth = None
                except (ValueError, TypeError):
                    date_of_birth = None
                
                try:
                    loan_sanction_date = loan_data.get('loan_sanction_date', {}).get('original')
                    if loan_sanction_date:
                        loan_sanction_date = datetime.strptime(loan_sanction_date, '%Y-%m-%d').date()
                    else:
                        loan_sanction_date = None
                except (ValueError, TypeError):
                    loan_sanction_date = None
                
                loan_doc = LoanDocument(
                    user=request.user,
                    # Personal Information
                    borrower_name_original=borrower_name['original'],
                    borrower_name_language=borrower_name['language'],
                    borrower_name_translated=borrower_name['translated'],
                    
                    date_of_birth=date_of_birth,
                    
                    father_name_original=father_name['original'],
                    father_name_language=father_name['language'],
                    father_name_translated=father_name['translated'],
                    
                    spouse_name_original=spouse_name['original'],
                    spouse_name_language=spouse_name['language'],
                    spouse_name_translated=spouse_name['translated'],
                    
                    sex_original=sex['original'],
                    sex_language=sex['language'],
                    sex_translated=sex['translated'],
                    
                    # Identity Information
                    aadhar_number=loan_data.get('aadhar_number', {}).get('original', ''),
                    pan_number=loan_data.get('pan_number', {}).get('original', ''),
                    passport_number=loan_data.get('passport_number', {}).get('original', ''),
                    driving_license=loan_data.get('driving_license', {}).get('original', ''),
                    
                    # Loan Details
                    loan_amount=loan_data.get('loan_amount', {}).get('original', ''),
                    loan_purpose_original=loan_purpose['original'],
                    loan_purpose_language=loan_purpose['language'],
                    loan_purpose_translated=loan_purpose['translated'],
                    loan_term_months=loan_data.get('loan_term_months', ''),
                    monthly_income=loan_data.get('monthly_income', ''),
                    credit_score=loan_data.get('credit_score', ''),
                    
                    loan_sanction_date=loan_sanction_date,
                    loan_balance=loan_data.get('loan_balance', {}).get('original', ''),
                    
                    # Lists
                    witness_details=loan_data.get('witness_details', []),
                    emi_history=loan_data.get('emi_history', []),
                    
                    # Summary
                    credibility_summary_original=credibility_summary['original'],
                    credibility_summary_language=credibility_summary['language'],
                    credibility_summary_translated=credibility_summary['translated']
                )
                
                try:
                    loan_doc.save()
                    messages.success(request, 'Loan document processed successfully!')
                    
                    # Create a list of fields and their languages for the template
                    languages_detected = [
                        ("Borrower Name", loan_doc.borrower_name_language),
                        ("Father's Name", loan_doc.father_name_language),
                        ("Spouse's Name", loan_doc.spouse_name_language),
                        ("Sex", loan_doc.sex_language),
                        ("Loan Purpose", loan_doc.loan_purpose_language),
                        ("Credibility Summary", loan_doc.credibility_summary_language)
                    ]
                    
                    return render(request, self.template_name, {
                        'loan_doc': loan_doc,
                        'document_type': document_type,
                        'processed_data': True,
                        'languages_detected': languages_detected
                    })
                    
                except Exception as e:
                    messages.error(request, f'Error saving document: {str(e)}')
                    logger.error(f'Error saving loan document: {str(e)}')
                    return render(request, self.template_name)
                
            else:  # property document
                # Handle property document with translations
                # Get the data with proper default values
                property_data = result.get('structured_data', {})
                
                property_owner = property_data.get('property_owner', {})
                property_location = property_data.get('property_location', {})
                risk_summary = property_data.get('risk_summary', {})
                
                property_doc = PropertyDocument(
                    user=request.user,
                    # Property owner details
                    property_owner_original=property_owner.get('original', ''),
                    property_owner_language=property_owner.get('language', 'en'),
                    property_owner_translated=property_owner.get('translated', ''),
                    
                    # Property area
                    property_area=property_data.get('property_area', {}).get('original', ''),
                    
                    # Property location
                    property_location_original=property_location.get('original', ''),
                    property_location_language=property_location.get('language', 'en'),
                    property_location_translated=property_location.get('translated', ''),
                    
                    # Other property details
                    property_coordinates=property_data.get('property_coordinates', {}).get('original', ''),
                    property_value=property_data.get('property_value', {}).get('original', ''),
                    loan_limit=property_data.get('loan_limit', {}).get('original', ''),
                    
                    # Risk summary
                    risk_summary_original=risk_summary.get('original', ''),
                    risk_summary_language=risk_summary.get('language', 'en'),
                    risk_summary_translated=risk_summary.get('translated', '')
                )
                
                try:
                    property_doc.save()
                    messages.success(request, 'Property document processed successfully!')
                    
                    # Pass the processed data to the template
                    context = {
                        'processed_data': True,
                        'document_type': 'property',
                        'property_doc': property_doc
                    }
                    return render(request, self.template_name, context)
                    
                except Exception as e:
                    messages.error(request, f'Error saving document: {str(e)}')
                    logger.error(f'Error saving property document: {str(e)}')
                    return render(request, self.template_name)

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