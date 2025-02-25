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
    
    # Personal Information
    borrower_name = models.CharField(max_length=100)
    date_of_birth = models.DateField(null=True, blank=True)
    sex = models.CharField(max_length=20, blank=True)
    father_name = models.CharField(max_length=100, blank=True)
    spouse_name = models.CharField(max_length=100, blank=True)
    
    # Identity Information
    aadhar_number = models.CharField(max_length=12, blank=True)
    pan_number = models.CharField(max_length=10, blank=True)
    passport_number = models.CharField(max_length=20, blank=True)
    driving_license = models.CharField(max_length=20, blank=True)
    
    # Loan Information
    loan_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    loan_sanction_date = models.DateField(null=True, blank=True)
    loan_balance = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    
    # Additional Information
    witness_details = models.JSONField(default=dict, blank=True)
    emi_history = models.JSONField(default=dict, blank=True)
    credibility_summary = models.TextField(blank=True)
    
    def __str__(self):
        return f"Loan Document - {self.borrower_name}"