# catalog/views.py
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from .models import Juego
from django.utils.text import slugify
from django.db.models import Q

def catalogo_general(request):
    """Muestra todos los juegos DISPONIBLES"""
    query = request.GET.get('q')  # texto que escribe el usuario

    # Base: todos los juegos disponibles (sin filtrar por consola)
    juegos_list = Juego.objects.filter(disponible=True)

    # Si hay texto en el buscador, filtramos
    if query:
        juegos_list = juegos_list.filter(
            Q(nombre__icontains=query) | Q(descripcion__icontains=query)
        )

    # Orden y paginación
    juegos_list = juegos_list.order_by('nombre')
    paginator = Paginator(juegos_list, 20)
    page_number = request.GET.get('page')
    juegos = paginator.get_page(page_number)

    context = {
        'juegos': juegos,
        'titulo': 'Catálogo Completo',
        'total_juegos': juegos_list.count(),
        'query': query,  # para mantener el valor en el input
    }
    return render(request, 'catalog/lista.html', context)

def catalogo_ps4(request):
    query = request.GET.get('q')  # texto que escribe el usuario

    # Base: solo juegos de PS4 disponibles
    juegos_list = Juego.objects.filter(consola='ps4', disponible=True)

    # Si hay texto en el buscador, filtramos
    if query:
        juegos_list = juegos_list.filter(
            Q(nombre__icontains=query) | Q(descripcion__icontains=query)
        )

    # Orden y paginación
    juegos_list = juegos_list.order_by('nombre')
    paginator = Paginator(juegos_list, 20)
    page_number = request.GET.get('page')
    juegos = paginator.get_page(page_number)

    context = {
        'juegos': juegos,
        'titulo': 'Catálogo PS4',
        'total_juegos': juegos_list.count(),
        'query': query,  # para mantener el valor en el input
    }
    return render(request, 'catalog/lista.html', context)


def catalogo_ps5(request):
    query = request.GET.get('q')  # texto que escribe el usuario

    # Base: solo juegos de PS4 disponibles
    juegos_list = Juego.objects.filter(consola='ps5', disponible=True)

    # Si hay texto en el buscador, filtramos
    if query:
        juegos_list = juegos_list.filter(
            Q(nombre__icontains=query) | Q(descripcion__icontains=query)
        )

    # Orden y paginación
    juegos_list = juegos_list.order_by('nombre')
    paginator = Paginator(juegos_list, 20)
    page_number = request.GET.get('page')
    juegos = paginator.get_page(page_number)

    context = {
        'juegos': juegos,
        'titulo': 'Catálogo PS5',
        'total_juegos': juegos_list.count(),
        'query': query,  # para mantener el valor en el input
    }
    return render(request, 'catalog/lista.html', context)

def destacados(request):
    """Muestra solo juegos destacados DISPONIBLES"""
    juegos = Juego.objects.filter(destacado=True, disponible=True)  # ← CLAVE
    paginator = Paginator(juegos, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    
    return render(request, 'catalog/lista.html', {
        'juegos': page_obj,
        'total_juegos': juegos.count(),
        'titulo': 'Juegos Destacados'
    })

def detalle_juego(request, slug):
    """Página de detalle de un juego"""
    # Buscar por slug generado
    juegos = Juego.objects.all()
    
    for juego in juegos:
        if slugify(juego.nombre) == slug:
            return render(request, 'catalog/detalle.html', {'juego': juego})
    
    # Si no se encuentra, 404
    from django.http import Http404
    raise Http404("Juego no encontrado")