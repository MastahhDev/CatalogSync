from django.shortcuts import render
from django.core.paginator import Paginator
from catalog.models import Juego, ResenaCliente

# Create your views here.
def home(request):
    # Obtener solo los juegos destacados y disponibles
    juegos_destacados = Juego.objects.filter(
        destacado=True,
        disponible=True
    ).order_by('-fecha_actualizacion')[:10]
    
    # Obtener reseñas activas
    resenas = ResenaCliente.objects.filter(activo=True).order_by('-fecha')[:10]
    
    context = {
        'juegos': juegos_destacados,  # Para el carrusel de juegos
        'resenas': resenas,  # Para el carrusel de reseñas
    }
    return render(request, 'home.html', context)

def featured(request):
    return render(request, 'featured.html')

def ps4(request):
    return render(request, 'ps4.html')

def ps5(request):
    return render(request, 'ps5.html')

def questions(request):
    return render(request, 'questions.html')

def about(request):
    return render(request, 'about.html')

def lista_juegos(request):
    # Vista principal que muestra los juegos paginados
    print("Vista lista_juegos ejecutándose...")
    juegos = cargar_juegos_desde_csv()
    
    # Paginación - 20 juegos por página
    paginator = Paginator(juegos, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'juegos': page_obj,
        'total_juegos': len(juegos)
    }
    
    return render(request, 'ps4.html', context)