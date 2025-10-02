from django.contrib import admin
from django.urls import path
from featured import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('featured/', views.featured, name='featured'),
    path('ps4/', views.ps4, name='ps4'),
    path('ps5/', views.ps5, name='ps5'),
    path('questions/', views.questions, name='questions'),
    path('about/', views.about, name='about'),
]
