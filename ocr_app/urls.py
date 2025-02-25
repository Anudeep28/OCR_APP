# ocr_app/urls.py
from django.urls import path
from .views import DocumentProcessView, home, SignUpView

app_name = 'ocr_app'
urlpatterns = [
    path('', home, name='home'),  # Add home page URL
    path('signup/', SignUpView.as_view(), name='signup'),
    path('document-upload/', DocumentProcessView.as_view(), name='document-upload'),
]