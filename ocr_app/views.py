# ocr_app/views.py
from django.views import View
from django.shortcuts import render, redirect, get_object_or_404
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
import json
import csv
from django.http import HttpResponse, JsonResponse
from django.contrib.auth import logout

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
                    property_area_original=property_data.get('property_area', {}).get('original', ''),
                    property_area_language=property_data.get('property_area', {}).get('language', 'en'),
                    property_area_translated=property_data.get('property_area', {}).get('translated', ''),
                    
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


# Custom logout view
def logout_view(request):
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('ocr_app:home')


@app_access_required
def download_json(request, document_type, document_id):
    """Download document data as JSON file"""
    try:
        if document_type == 'loan':
            document = get_object_or_404(LoanDocument, id=document_id, user=request.user)
            
            # Create a dictionary with all the loan document data
            data = {
                'personal_information': {
                    'borrower_name': {
                        'original': document.borrower_name_original,
                        'language': document.borrower_name_language,
                        'translated': document.borrower_name_translated
                    },
                    'date_of_birth': str(document.date_of_birth) if document.date_of_birth else '',
                    'father_name': {
                        'original': document.father_name_original,
                        'language': document.father_name_language,
                        'translated': document.father_name_translated
                    },
                    'spouse_name': {
                        'original': document.spouse_name_original,
                        'language': document.spouse_name_language,
                        'translated': document.spouse_name_translated
                    },
                    'sex': {
                        'original': document.sex_original,
                        'language': document.sex_language,
                        'translated': document.sex_translated
                    }
                },
                'identity_information': {
                    'aadhar_number': document.aadhar_number,
                    'pan_number': document.pan_number,
                    'passport_number': document.passport_number,
                    'driving_license': document.driving_license
                },
                'loan_information': {
                    'loan_amount': document.loan_amount,
                    'loan_purpose': {
                        'original': document.loan_purpose_original,
                        'language': document.loan_purpose_language,
                        'translated': document.loan_purpose_translated
                    },
                    'loan_term_months': document.loan_term_months,
                    'monthly_income': document.monthly_income,
                    'credit_score': document.credit_score,
                    'loan_sanction_date': str(document.loan_sanction_date) if document.loan_sanction_date else '',
                    'loan_balance': document.loan_balance
                },
                'additional_information': {
                    'witness_details': document.witness_details,
                    'emi_history': document.emi_history,
                    'credibility_summary': {
                        'original': document.credibility_summary_original,
                        'language': document.credibility_summary_language,
                        'translated': document.credibility_summary_translated
                    }
                }
            }
            filename = f"loan_document_{document_id}.json"
            
        elif document_type == 'property':
            document = get_object_or_404(PropertyDocument, id=document_id, user=request.user)
            
            # Create a dictionary with all the property document data
            data = {
                'property_information': {
                    'property_owner': {
                        'original': document.property_owner_original,
                        'language': document.property_owner_language,
                        'translated': document.property_owner_translated
                    },
                    'property_area': {
                        'original': document.property_area_original,
                        'language': document.property_area_language,
                        'translated': document.property_area_translated
                    },
                    'property_location': {
                        'original': document.property_location_original,
                        'language': document.property_location_language,
                        'translated': document.property_location_translated
                    },
                    'property_coordinates': document.property_coordinates,
                    'property_value': document.property_value,
                    'loan_limit': document.loan_limit
                },
                'risk_assessment': {
                    'risk_summary': {
                        'original': document.risk_summary_original,
                        'language': document.risk_summary_language,
                        'translated': document.risk_summary_translated
                    }
                }
            }
            filename = f"property_document_{document_id}.json"
        else:
            return HttpResponse("Invalid document type", status=400)
        
        # Create the JSON response
        response = HttpResponse(json.dumps(data, indent=4), content_type='application/json')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
        
    except Exception as e:
        logger.error(f"Error downloading JSON: {str(e)}")
        messages.error(request, f"Error downloading document: {str(e)}")
        return redirect('ocr_app:document-upload')


@app_access_required
def download_csv(request, document_type, document_id):
    """Download document data as CSV file"""
    try:
        if document_type == 'loan':
            document = get_object_or_404(LoanDocument, id=document_id, user=request.user)
            filename = f"loan_document_{document_id}.csv"
            
            # Create CSV response
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            writer = csv.writer(response)
            # Write headers and rows for loan document
            writer.writerow(['Field', 'Original Value', 'Language', 'Translated Value'])
            
            # Personal Information
            writer.writerow(['Borrower Name', document.borrower_name_original, document.borrower_name_language, document.borrower_name_translated])
            writer.writerow(['Date of Birth', document.date_of_birth if document.date_of_birth else '', '', ''])
            writer.writerow(['Father Name', document.father_name_original, document.father_name_language, document.father_name_translated])
            writer.writerow(['Spouse Name', document.spouse_name_original, document.spouse_name_language, document.spouse_name_translated])
            writer.writerow(['Sex', document.sex_original, document.sex_language, document.sex_translated])
            
            # Identity Information
            writer.writerow(['Aadhar Number', document.aadhar_number, '', ''])
            writer.writerow(['PAN Number', document.pan_number, '', ''])
            writer.writerow(['Passport Number', document.passport_number, '', ''])
            writer.writerow(['Driving License', document.driving_license, '', ''])
            
            # Loan Information
            writer.writerow(['Loan Amount', document.loan_amount, '', ''])
            writer.writerow(['Loan Purpose', document.loan_purpose_original, document.loan_purpose_language, document.loan_purpose_translated])
            writer.writerow(['Loan Term (Months)', document.loan_term_months, '', ''])
            writer.writerow(['Monthly Income', document.monthly_income, '', ''])
            writer.writerow(['Credit Score', document.credit_score, '', ''])
            writer.writerow(['Loan Sanction Date', document.loan_sanction_date if document.loan_sanction_date else '', '', ''])
            writer.writerow(['Loan Balance', document.loan_balance, '', ''])
            
            # Additional Information
            writer.writerow(['Credibility Summary', document.credibility_summary_original, document.credibility_summary_language, document.credibility_summary_translated])
            
            # Handle witness details and EMI history separately if needed
            if document.witness_details:
                writer.writerow([])
                writer.writerow(['Witness Details'])
                for i, witness in enumerate(document.witness_details):
                    writer.writerow([f'Witness {i+1}', str(witness), '', ''])
            
            if document.emi_history:
                writer.writerow([])
                writer.writerow(['EMI History'])
                for i, emi in enumerate(document.emi_history):
                    writer.writerow([f'EMI {i+1}', str(emi), '', ''])
            
        elif document_type == 'property':
            document = get_object_or_404(PropertyDocument, id=document_id, user=request.user)
            filename = f"property_document_{document_id}.csv"
            
            # Create CSV response
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            writer = csv.writer(response)
            # Write headers and rows for property document
            writer.writerow(['Field', 'Original Value', 'Language', 'Translated Value'])
            
            # Property Information
            writer.writerow(['Property Owner', document.property_owner_original, document.property_owner_language, document.property_owner_translated])
            writer.writerow(['Property Area', document.property_area_original, document.property_area_language, document.property_area_translated])
            writer.writerow(['Property Location', document.property_location_original, document.property_location_language, document.property_location_translated])
            writer.writerow(['Property Coordinates', document.property_coordinates, '', ''])
            writer.writerow(['Property Value', document.property_value, '', ''])
            writer.writerow(['Loan Limit', document.loan_limit, '', ''])
            
            # Risk Assessment
            writer.writerow(['Risk Summary', document.risk_summary_original, document.risk_summary_language, document.risk_summary_translated])
            
        else:
            return HttpResponse("Invalid document type", status=400)
        
        return response
        
    except Exception as e:
        logger.error(f"Error downloading CSV: {str(e)}")
        messages.error(request, f"Error downloading document: {str(e)}")
        return redirect('ocr_app:document-upload')