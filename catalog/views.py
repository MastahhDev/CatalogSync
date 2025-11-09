# catalog/views.py
from django.shortcuts import render, get_object_or_404
from django.http import Http404
from django.core.paginator import Paginator
from .models import Juego

def catalogo_general(request):
    """Vista del catálogo general con todos los juegos"""
    query = request.GET.get('q', '')
    
    if query:
        juegos = Juego.objects.filter(
            nombre__icontains=query,
            disponible=True
        ).order_by('nombre')
    else:
        juegos = Juego.objects.filter(disponible=True).order_by('nombre')
    
    # Paginación
    paginator = Paginator(juegos, 24)
    page_number = request.GET.get('page')
    juegos_paginados = paginator.get_page(page_number)
    
    context = {
        'juegos': juegos_paginados,
        'total_juegos': juegos.count(),
        'titulo': 'Catálogo General',
        'query': query,
    }
    
    return render(request, 'catalog/lista.html', context)

def catalogo_ps4(request):
    """Vista del catálogo de PS4"""
    query = request.GET.get('q', '')
    
    if query:
        juegos = Juego.objects.filter(
            nombre__icontains=query,
            consola='ps4',
            disponible=True
        ).order_by('nombre')
    else:
        juegos = Juego.objects.filter(consola='ps4', disponible=True).order_by('nombre')
    
    paginator = Paginator(juegos, 24)
    page_number = request.GET.get('page')
    juegos_paginados = paginator.get_page(page_number)
    
    context = {
        'juegos': juegos_paginados,
        'total_juegos': juegos.count(),
        'titulo': 'Catálogo PS4',
        'query': query,
    }
    
    return render(request, 'catalog/lista.html', context)

def catalogo_ps5(request):
    """Vista del catálogo de PS5"""
    query = request.GET.get('q', '')
    
    if query:
        juegos = Juego.objects.filter(
            nombre__icontains=query,
            consola='ps5',
            disponible=True
        ).order_by('nombre')
    else:
        juegos = Juego.objects.filter(consola='ps5', disponible=True).order_by('nombre')
    
    paginator = Paginator(juegos, 24)
    page_number = request.GET.get('page')
    juegos_paginados = paginator.get_page(page_number)
    
    context = {
        'juegos': juegos_paginados,
        'total_juegos': juegos.count(),
        'titulo': 'Catálogo PS5',
        'query': query,
    }
    
    return render(request, 'catalog/lista.html', context)

def destacados(request):
    """Vista de juegos destacados"""
    # Si tienes un campo 'destacado' en el modelo
    # juegos = Juego.objects.filter(destacado=True, disponible=True).order_by('nombre')
    
    # Por ahora, mostrar los más recientes
    juegos = Juego.objects.filter(disponible=True).order_by('-fecha_actualizacion')[:20]
    
    context = {
        'juegos': juegos,
        'total_juegos': juegos.count(),
        'titulo': 'Juegos Destacados',
    }
    
    return render(request, 'catalog/lista.html', context)

def detalle_juego(request, slug):
    """
    Vista de detalle del juego.
    El slug tiene formato: {id}-{nombre-slugificado}
    Ejemplo: 10-a-way-out o 10-a-way-out-ps4
    """
    try:
        # Extraer el ID del slug (todo lo que está antes del primer guion)
        partes = slug.split('-')
        juego_id = int(partes[0])
        
        # Buscar el juego por ID
        juego = get_object_or_404(Juego, id=juego_id)
        
        # Verificar que el juego esté disponible
        if not juego.disponible:
            raise Http404("Este juego no está disponible actualmente")
        
        # Debug: Imprimir info en consola
        print(f"✅ Juego encontrado: {juego.nombre} (ID: {juego.id})")
        print(f"   Slug recibido: {slug}")
        print(f"   Tiene secundario: {juego.tiene_secundario}")
        if juego.tiene_secundario:
            print(f"   Precio primario: ${juego.recargo}")
            print(f"   Precio secundario: ${juego.recargo_secundario}")
        
    except (ValueError, IndexError) as e:
        print(f"❌ Error parseando slug '{slug}': {e}")
        raise Http404("Formato de URL inválido")
    except Juego.DoesNotExist:
        print(f"❌ Juego con ID extraído de '{slug}' no encontrado")
        raise Http404("Juego no encontrado")
    
    context = {
        'juego': juego,
    }
    
    return render(request, 'catalog/detalle.html', context)