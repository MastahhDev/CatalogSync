from django.contrib import admin
from django.urls import path, include
from featured import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('catalogo/', include('catalog.urls')),  # Nueva ruta
    path('questions/', views.questions, name='questions'),
    path('about/', views.about, name='about'),
    path('carrito/', include('carrito.urls')),
    path("catalog/", include("catalog.urls")),
]