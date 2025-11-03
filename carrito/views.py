from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from catalog.models import Juego
from .cart import Cart

@require_POST
def agregar_al_carrito(request, juego_id):
    """Agrega un juego al carrito y retorna el badge actualizado"""
    cart = Cart(request)
    juego = get_object_or_404(Juego, id=juego_id, disponible=True)
    
    cart.add(juego_id)
    
    # Renderiza el badge actualizado + notificación
    context = {
        'total_items': cart.get_total_items(),
        'juego_nombre': juego.nombre,
    }
    return render(request, 'carrito/badge_update.html', context)

def ver_carrito(request):
    """Muestra el contenido completo del carrito"""
    cart = Cart(request)
    
    context = {
        'cart': cart,
        'items': cart.get_items(),
        'total_price': cart.get_total_price(),
        'total_items': cart.get_total_items(),
    }
    return render(request, 'carrito/popup_content.html', context)

@require_POST
def actualizar_cantidad(request, juego_id):
    """Actualiza la cantidad de un juego"""
    cart = Cart(request)
    cantidad = int(request.POST.get('cantidad', 1))
    
    cart.update_quantity(juego_id, cantidad)
    
    # Renderiza el contenido actualizado del carrito
    context = {
        'cart': cart,
        'items': cart.get_items(),
        'total_price': cart.get_total_price(),
        'total_items': cart.get_total_items(),
    }
    return render(request, 'carrito/cart_items.html', context)

@require_POST
def eliminar_del_carrito(request, juego_id):
    """Elimina un juego del carrito"""
    cart = Cart(request)
    cart.remove(juego_id)
    
    # Si el carrito quedó vacío, retorna mensaje
    if len(cart) == 0:
        return render(request, 'carrito/cart_empty.html')
    
    # Sino, retorna el contenido actualizado
    context = {
        'cart': cart,
        'items': cart.get_items(),
        'total_price': cart.get_total_price(),
        'total_items': cart.get_total_items(),
    }
    return render(request, 'carrito/cart_items.html', context)

@require_POST
def vaciar_carrito(request):
    """Vacía todo el carrito"""
    cart = Cart(request)
    cart.clear()
    
    return render(request, 'carrito/cart_empty.html')