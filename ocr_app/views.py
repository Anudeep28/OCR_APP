# ocr_app/views.py
from django.views import View
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from .services.rag_utils import extract_data_from_document
from .models import CustomUser, LoanDocument
from django.views.generic.edit import CreateView
from django.urls import reverse_lazy
from .forms import CustomUserCreationForm

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
        print(f"\nProcessing uploaded file: {document.name}")
        
        fs = FileSystemStorage()
        filename = fs.save(document.name, document)
        file_path = fs.path(filename)
        print(f"File saved to: {file_path}")
        
        try:
            # Extract data from document
            print("Calling extract_data_from_document...")
            result = extract_data_from_document(file_path)
            print(f"Extraction result: {result}")
            
            if not result['success']:
                messages.error(request, f"Error processing document: {result.get('error', 'Unknown error')}")
                return render(request, self.template_name)
            
            # Create LoanDocument instance
            print("Creating LoanDocument instance...")
            
            # Handle date fields
            loan_sanction_date = result['structured_data'].get('loan_sanction_date')
            if loan_sanction_date == 'None' or loan_sanction_date is None:
                loan_sanction_date = None
                
            date_of_birth = result['structured_data'].get('date_of_birth')
            if date_of_birth == 'None' or date_of_birth is None:
                date_of_birth = None
            
            # Handle numeric fields
            loan_amount = result['structured_data'].get('loan_amount')
            if loan_amount == 'None' or loan_amount is None:
                loan_amount = None
                
            loan_balance = result['structured_data'].get('loan_balance')
            if loan_balance == 'None' or loan_balance is None:
                loan_balance = None
            
            loan_doc = LoanDocument(
                user=request.user,
                borrower_name=result['structured_data'].get('borrower_name') or '',
                date_of_birth=date_of_birth,
                sex=result['structured_data'].get('sex') or '',
                father_name=result['structured_data'].get('father_name') or '',
                spouse_name=result['structured_data'].get('spouse_name') or '',
                aadhar_number=result['structured_data'].get('aadhar_number') or '',
                pan_number=result['structured_data'].get('pan_number') or '',
                passport_number=result['structured_data'].get('passport_number') or '',
                driving_license=result['structured_data'].get('driving_license') or '',
                loan_amount=loan_amount,
                loan_sanction_date=loan_sanction_date,
                loan_balance=loan_balance,
                witness_details=result['structured_data'].get('witness_details') or [],
                emi_history=result['structured_data'].get('emi_history') or [],
                credibility_summary=result['structured_data'].get('credibility_summary') or ''
            )
            loan_doc.save()
            print("LoanDocument saved successfully")
            
            messages.success(request, 'Document processed successfully!')
            context = {
                'extracted_data': result['structured_data'],
                'loan_doc': loan_doc
            }
            print(f"Rendering template with context: {context}")
            return render(request, self.template_name, context)
            
        except Exception as e:
            print(f"Error in post method: {str(e)}")
            messages.error(request, f'Error processing document: {str(e)}')
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