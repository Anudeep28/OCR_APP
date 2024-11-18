from django.db import models
from django.utils import timezone

# Create your models here.

class OCRDocument(models.Model):
    file = models.FileField(upload_to='documents/')
    uploaded_at = models.DateTimeField(default=timezone.now)
    processed_text = models.TextField(blank=True)
    markdown_output = models.TextField(blank=True)
    
    def __str__(self):
        return f"Document uploaded at {self.uploaded_at}"
