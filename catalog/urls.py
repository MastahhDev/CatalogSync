from django.urls import path
from . import views

app_name = 'catalogo'

urlpatterns = [
    path('', views.catalogo_general, name='general'),
    path('ps4/', views.catalogo_ps4, name='ps4'),
    path('ps5/', views.catalogo_ps5, name='ps5'),
    path('destacados/', views.destacados, name='destacados'),
    path('juego/<slug:slug>/', views.detalle_juego, name='detalle'),
    path("subir-stock-ps4/", views.subir_stock_ps4, name="subir_stock_ps4"),
]