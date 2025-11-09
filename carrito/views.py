# carrito/views.py
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST
from catalog.models import Juego
from .cart import Cart
from urllib.parse import quote

@require_POST
def agregar_al_carrito(request, juego_id):
    """Agrega un juego al carrito con el tipo de precio especificado"""
    cart = Cart(request)
    juego = get_object_or_404(Juego, id=juego_id, disponible=True)
    
    # ⭐ NUEVO: Obtener tipo de precio desde el query parameter
    tipo_precio = request.GET.get('tipo', 'primario')
    
    # Validar que el tipo de precio sea válido
    if tipo_precio not in ['primario', 'secundario']:
        tipo_precio = 'primario'
    
    # Validar que el juego tenga el precio secundario si se solicita
    if tipo_precio == 'secundario':
        if not juego.tiene_secundario and not juego.es_solo_secundario:
            # Si no tiene secundario, usar primario
            tipo_precio = 'primario'
    
    # Agregar al carrito con el tipo de precio
    cart.add(juego_id, tipo_precio=tipo_precio)
    
    # Renderiza el badge actualizado + notificación
    context = {
        'total_items': cart.get_total_items(),
        'juego_nombre': juego.nombre,
        'tipo_precio': tipo_precio,
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
def actualizar_cantidad(request, item_key):
    """
    Actualiza la cantidad de un item específico del carrito.
    Ahora usa item_key en lugar de juego_id para soportar precios duales.
    """
    cart = Cart(request)
    cantidad = int(request.POST.get('cantidad', 1))
    
    cart.update_quantity(item_key, cantidad)
    
    # Renderiza el contenido actualizado del carrito
    context = {
        'cart': cart,
        'items': cart.get_items(),
        'total_price': cart.get_total_price(),
        'total_items': cart.get_total_items(),
    }
    return render(request, 'carrito/cart_items.html', context)

@require_POST
def eliminar_del_carrito(request, item_key):
    """
    Elimina un item del carrito.
    Ahora usa item_key en lugar de juego_id para soportar precios duales.
    """
    cart = Cart(request)
    cart.remove(item_key)
    
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

    # 1️⃣ Construir lista de juegos con detalles
    lineas_juegos = []
    for item in items:
        # ⭐ NUEVO: Incluir tipo de precio en el mensaje
        etiqueta = f"({item['etiqueta']})" if item['tipo_precio'] == 'secundario' or item.get('etiqueta') else ""
        cantidad_texto = f"x{item['cantidad']}" if item['cantidad'] > 1 else ""
        
        linea = f"• {item['juego'].nombre} {etiqueta} {cantidad_texto}".strip()
        lineas_juegos.append(linea)
    
    # 2️⃣ Obtener total
    total = cart.get_total_price()

    # 3️⃣ Obtener método de pago
    metodo_pago = request.POST.get('metodo_pago', 'sin especificar')

    # 4️⃣ Construir el mensaje
    mensaje = (
        f"¡Buenas! Vengo de la página web.\n\n"
        f"Quiero los siguientes juegos:\n"
        f"{chr(10).join(lineas_juegos)}\n\n"
        f"Total: ${total:,.0f}\n"
        f"Método de pago: {metodo_pago}"
    )

    # 5️⃣ Codificar mensaje para WhatsApp
    mensaje_url = quote(mensaje)

    # 6️⃣ Número de destino
    numero = "5491151594477"
    url_whatsapp = f"https://wa.me/{numero}?text={mensaje_url}"

    # 7️⃣ Devolver respuesta JSON para abrir el link en JS
    return JsonResponse({'url': url_whatsapp})