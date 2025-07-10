
from django.urls import path
from . import views # Correctly imports views from the same app directory

urlpatterns = [
    path('', views.upload_pdf, name='upload_pdf'), # Root path for upload form
    path('summary/', views.display_summary, name='display_summary'), # Path for summary results
]