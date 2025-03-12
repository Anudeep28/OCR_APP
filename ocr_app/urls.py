# ocr_app/urls.py
from django.urls import path
from .views import (
    HomeView, DocumentProcessView, SignUpView, logout_view,
    DownloadJSONView, DownloadCSVView, get_saved_prompts
)

app_name = 'ocr_app'
urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('signup/', SignUpView.as_view(), name='signup'),
    path('document-process/', DocumentProcessView.as_view(), name='document-process'),
    path('download-json/<str:document_type>/<int:document_id>/', DownloadJSONView.as_view(), name='download-json'),
    path('download-csv/<str:document_type>/<int:document_id>/', DownloadCSVView.as_view(), name='download-csv'),
    path('get-saved-prompts/', get_saved_prompts, name='get-saved-prompts'),
    path('logout/', logout_view, name='logout'),
]