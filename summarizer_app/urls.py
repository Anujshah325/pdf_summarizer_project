from django.urls import path
from . import views

urlpatterns = [
    path('', views.upload_pdf, name='upload_pdf'),
    path('summary/', views.display_summary, name='display_summary'),
    path('expand_summary/', views.expand_summary, name='expand_summary'), # New endpoint for expanding summary
    path('generate_keywords/', views.generate_keywords, name='generate_keywords'), # New endpoint for generating keywords
]