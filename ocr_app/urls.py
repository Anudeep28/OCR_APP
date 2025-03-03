# ocr_app/urls.py
from django.urls import path
from .views import DocumentProcessView, home, SignUpView, download_json, download_csv, logout_view, get_saved_prompts

app_name = 'ocr_app'
urlpatterns = [
    path('', home, name='home'),  # Add home page URL
    path('signup/', SignUpView.as_view(), name='signup'),
    path('document-upload/', DocumentProcessView.as_view(), name='document-upload'),
    path('download-json/<str:document_type>/<int:document_id>/', download_json, name='download-json'),
    path('download-csv/<str:document_type>/<int:document_id>/', download_csv, name='download-csv'),
    path('get-saved-prompts/', get_saved_prompts, name='get-saved-prompts'),
    path('logout/', logout_view, name='logout'),
]