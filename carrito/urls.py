from django.urls import path
from . import views

app_name = 'carrito'

urlpatterns = [
    path('agregar/<int:juego_id>/', views.agregar_al_carrito, name='agregar'),
    path('ver/', views.ver_carrito, name='ver'),
    path('actualizar/<str:item_key>/', views.actualizar_cantidad, name='actualizar'),
    path('eliminar/<str:item_key>/', views.eliminar_del_carrito, name='eliminar'),
    path('vaciar/', views.vaciar_carrito, name='vaciar'),
    path('finalizar/', views.finalizar_compra, name='finalizar'),
]