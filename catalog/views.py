from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from .models import Juego

def catalogo_general(request):
    """Muestra todos los juegos"""
    juegos = Juego.objects.all()
    paginator = Paginator(juegos, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    
    return render(request, 'catalog/lista.html', {
        'juegos': page_obj,
        'total_juegos': juegos.count(),
        'titulo': 'Catálogo Completo'
    })

def catalogo_ps4(request):
    """Muestra solo juegos de PS4"""
    juegos = Juego.objects.filter(consola='ps4')
    paginator = Paginator(juegos, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    
    return render(request, 'catalog/lista.html', {
        'juegos': page_obj,
        'total_juegos': juegos.count(),
        'titulo': 'PlayStation 4'
    })

def catalogo_ps5(request):
    """Muestra solo juegos de PS5"""
    juegos = Juego.objects.filter(consola='ps5')
    paginator = Paginator(juegos, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    
    return render(request, 'catalog/lista.html', {
        'juegos': page_obj,
        'total_juegos': juegos.count(),
        'titulo': 'PlayStation 5'
    })

def destacados(request):
    """Muestra solo juegos destacados"""
    juegos = Juego.objects.filter(destacado=True)
    paginator = Paginator(juegos, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    
    return render(request, 'catalog/lista.html', {
        'juegos': page_obj,
        'total_juegos': juegos.count(),
        'titulo': 'Juegos Destacados'
    })

def detalle_juego(request, slug):
    """Página de detalle de un juego"""
    # Buscar juego por nombre (convertir slug a nombre)
    nombre = slug.replace('-', ' ')
    juego = get_object_or_404(Juego, nombre__iexact=nombre)
    
    return render(request, 'catalog/detalle.html', {
        'juego': juego
    })