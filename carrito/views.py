from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST
from catalog.models import Juego
from .cart import Cart
from urllib.parse import quote

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

@require_POST
def finalizar_compra(request):
    """Arma el mensaje de WhatsApp con los juegos del carrito y devuelve el enlace"""
    cart = Cart(request)
    items = cart.get_items()

    if not items:
        return JsonResponse({'error': 'El carrito está vacío.'}, status=400)

    # 1️⃣ Obtener nombres y total
    nombres = [item['juego'].nombre for item in items]
    total = cart.get_total_price()

    # 2️⃣ Obtener método de pago (si se envió desde un formulario)
    metodo_pago = request.POST.get('metodo_pago', 'sin especificar')

    # 3️⃣ Construir el mensaje
    mensaje = (
        f"Buenas! Vengo de la página web.\n"
        f"Quiero los siguientes juegos: {', '.join(nombres)}.\n"
        f"Abono el total de ${total:,.0f} por {metodo_pago}."
    )

    # 4️⃣ Codificar mensaje para WhatsApp
    mensaje_url = quote(mensaje)

    # 5️⃣ Número de destino
    numero = "5491151594477"  # ⚠️ tu número en formato internacional sin + ni 0
    url_whatsapp = f"https://wa.me/{numero}?text={mensaje_url}"

    # 6️⃣ Devolver respuesta JSON para abrir el link en JS
    return JsonResponse({'url': url_whatsapp})