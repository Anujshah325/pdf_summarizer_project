"""
URL configuration for pdf_summarizer_web_app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# pdf_summarizer_web_app/pdf_summarizer_web_app/urls.py

from django.contrib import admin
from django.urls import path, include # Make sure 'include' is imported here

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('summarizer_app.urls')), # This line includes your app's URLs
]