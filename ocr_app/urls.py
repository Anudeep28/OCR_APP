from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('upload/', views.upload_file, name='upload_file'),
    path('download/markdown/<int:doc_id>/', views.download_markdown, name='download_markdown'),
    path('download/excel/<int:doc_id>/', views.download_excel, name='download_excel'),
]
