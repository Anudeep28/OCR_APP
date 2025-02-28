# ocr_app/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

class CustomUser(AbstractUser):
    is_app_user = models.BooleanField(
        default=False,
        verbose_name="App Access",
        help_text="Designates whether the user can access the document processing features"
    )

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

class OCRDocument(models.Model):
    file = models.FileField(upload_to='documents/')
    uploaded_at = models.DateTimeField(default=timezone.now)
    processed_text = models.TextField(blank=True)
    markdown_output = models.TextField(blank=True)

class LoanDocument(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    # Personal Information with language support
    borrower_name_original = models.CharField(max_length=255, blank=True, default='')
    borrower_name_language = models.CharField(max_length=10, blank=True, default='en')
    borrower_name_translated = models.CharField(max_length=255, blank=True, default='')
    
    date_of_birth = models.DateField(null=True, blank=True)
    
    father_name_original = models.CharField(max_length=255, blank=True, default='')
    father_name_language = models.CharField(max_length=10, blank=True, default='en')
    father_name_translated = models.CharField(max_length=255, blank=True, default='')
    
    spouse_name_original = models.CharField(max_length=255, blank=True, default='')
    spouse_name_language = models.CharField(max_length=10, blank=True, default='en')
    spouse_name_translated = models.CharField(max_length=255, blank=True, default='')
    
    sex_original = models.CharField(max_length=50, blank=True, default='')
    sex_language = models.CharField(max_length=10, blank=True, default='en')
    sex_translated = models.CharField(max_length=50, blank=True, default='')
    
    # Identity Information
    aadhar_number = models.CharField(max_length=12, blank=True, null=True, default='')
    pan_number = models.CharField(max_length=10, blank=True, null=True, verbose_name='PAN Number')
    passport_number = models.CharField(max_length=20, blank=True, null=True, default='')
    driving_license = models.CharField(max_length=20, blank=True, null=True, default='')
    
    # Loan Information
    loan_amount = models.CharField(max_length=50, blank=True, null=True, default='')
    loan_purpose_original = models.CharField(max_length=255, blank=True, default='')
    loan_purpose_language = models.CharField(max_length=10, blank=True, default='en')
    loan_purpose_translated = models.CharField(max_length=255, blank=True, default='')
    
    loan_term_months = models.CharField(max_length=50, blank=True, null=True, default='')
    monthly_income = models.CharField(max_length=50, blank=True, null=True, default='')
    credit_score = models.CharField(max_length=50, blank=True, null=True, default='')
    
    loan_sanction_date = models.DateField(null=True, blank=True)
    loan_balance = models.CharField(max_length=20, blank=True, null=True, default='')
    
    # Additional Information with language support
    witness_details = models.JSONField(default=list, blank=True)  
    emi_history = models.JSONField(default=list, blank=True)  
    credibility_summary_original = models.CharField(max_length=1000, blank=True, default='')
    credibility_summary_language = models.CharField(max_length=10, blank=True, default='en')
    credibility_summary_translated = models.CharField(max_length=1000, blank=True, default='')
    
    def __str__(self):
        return f"Loan Document - {self.borrower_name_original}"

class PropertyDocument(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    # Property Information with language support
    property_owner_original = models.CharField(max_length=200, blank=True)  
    property_owner_language = models.CharField(max_length=10, default='en')
    property_owner_translated = models.CharField(max_length=200, blank=True)
    
    property_area_original = models.CharField(max_length=100, blank=True)
    property_area_language = models.CharField(max_length=10, default='en')
    property_area_translated = models.CharField(max_length=100, blank=True)
    
    property_location_original = models.TextField(blank=True)  
    property_location_language = models.CharField(max_length=10, default='en')
    property_location_translated = models.TextField(blank=True)
    
    property_coordinates = models.CharField(max_length=100, blank=True)  
    property_value = models.CharField(max_length=100, blank=True)  
    loan_limit = models.CharField(max_length=100, blank=True)  
    
    risk_summary_original = models.TextField(blank=True)  
    risk_summary_language = models.CharField(max_length=10, default='en')
    risk_summary_translated = models.TextField(blank=True)
    
    def __str__(self):
        return f"Property Document - {self.property_owner_original}"